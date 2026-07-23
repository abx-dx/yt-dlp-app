import settings from "./settings.ts";

function sanitizeFilename(name: string): string {

  return name
    .replace(/[\\/:*?"<>|]/g, "")
    .replace(/[\r\n\t]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

}


function formatKbps(
  value: string | number | undefined
): string {

  const num = Number(value);

  if (!Number.isFinite(num)) {
    return "0.00";
  }

  return num.toFixed(2);

}


const args = [...Deno.args];

const command = args.shift();
const originalUrl = args.shift();

let outputDir: string | undefined;
let useCookies = false;

while (args.length > 0) {
  const arg = args.shift();

  switch (arg) {
    case "--output":
      outputDir = args.shift();
      break;

    case "--cookies":
      useCookies = true;
      break;
  }
}

if (!command || !originalUrl) {
  Deno.exit(1);
}


let url = originalUrl;


if (url.startsWith("https://music.youtube.com/playlist")) {

  url = url.replace(
    "music.youtube.com",
    "www.youtube.com"
  );

}

const profileSettings = settings.profiles[command];

if (!profileSettings) {
  console.error(`Geçersiz profil: ${command}`);
  Deno.exit(1);
}

const cookies = structuredClone(settings.cookies);
cookies.enabled = useCookies;

let output = profileSettings.output;

if (outputDir) {
  const normalized = outputDir.replaceAll("\\", "/");

  output = output.replace(
    "./downloads",
    normalized,
  );
}

const ytdlpArgs: string[] = [];



if (cookies.enabled) {
  ytdlpArgs.push(
    "--cookies-from-browser",
    cookies.browser
  );
}


ytdlpArgs.push(
  "--continue",
  "--no-overwrites",
  "--windows-filenames",
  "--newline",
  "--progress",
  "--no-quiet",
  "--retries",
  "infinite",
  "--fragment-retries",
  "infinite",
  "--embed-thumbnail",
  "--convert-thumbnails",
  "jpg",
  "--embed-metadata",
  "--encoding",
  "utf-8",
  "--concurrent-fragments", // <-- EKLENDİ: 16 parçayı eşzamanlı indirir
  "16"
);


// Playlist hazırlığı

if (command === "playlist") {

  try {

    const infoArgs: string[] = [];


    if (cookies.enabled) {

      infoArgs.push(
        "--cookies-from-browser",
        cookies.browser
      );

    }


    infoArgs.push(
      "-J",
      "--flat-playlist",
      url
    );


    const infoCmd =
      new Deno.Command(
        settings.ytdlp,
        {
          args: infoArgs,
          stdout: "piped",
          stderr: "piped"
        }
      );


    const infoResult =
      await infoCmd.output();


    const infoText =
      new TextDecoder("utf-8")
      .decode(infoResult.stdout);
	  
	const info =
	  JSON.parse(infoText); 


    const count =
      info.entries?.length ||
      info.playlist_count ||
      1;


    const padding =
      String(count).length;


    const folder =
      sanitizeFilename(
        info.title || "Playlist"
      );


	const baseDir = outputDir
	  ? outputDir.replaceAll("\\", "/")
	  : "./downloads";

	output =
      `${baseDir}/${folder}/%(playlist_index)0${padding}d - %(title)s.%(ext)s`;

  } catch {

	const baseDir = outputDir
      ? outputDir.replaceAll("\\", "/")
      : "./downloads";

	output =
	   `${baseDir}/%(playlist_index)s - %(title)s.%(ext)s`;

  }

}


// FILE_DONE

ytdlpArgs.push(
  "--print",
  "after_move:FILE_DONE|%(id)s|%(format_id)s|%(vcodec)s|%(acodec)s|%(resolution)s|%(vbr)s|%(abr)s|%(filepath)s"
);

// info

if (command === "info") {

  ytdlpArgs.push(
    "--dump-json",
    url
  );

}

else {


  const profile =
    settings.profiles[command];


  if (!profile) {

    console.error(
      `Bilinmeyen komut: ${command}`
    );

    Deno.exit(1);

  }


  if (profile.playlist) {

    ytdlpArgs.push(
      "--yes-playlist"
    );

  }


  ytdlpArgs.push(
    "-f",
    profile.format
  );


  if (profile.args) {

    ytdlpArgs.push(
      ...profile.args
    );

  }


  ytdlpArgs.push(
    "-o",
    output,
    url
  );

}


// çalıştır
const process = new Deno.Command(settings.ytdlp, {
  args: ytdlpArgs,
  stdout: "piped",
  stderr: "piped", // stderr de dinlemeye alındı
});

const child = process.spawn();

// Hem stdout hem stderr akışını eşzamanlı canlı okuyan fonksiyon
// Hem stdout hem stderr akışını eşzamanlı VE TAMPONSUZ (FLUSH) okuyan fonksiyon
async function streamOutput(stream: ReadableStream<Uint8Array>) {
  const reader = stream.getReader();
  const decoder = new TextDecoder("utf-8");
  const encoder = new TextEncoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const cleanLine = line.trim();
      if (!cleanLine) continue;

      if (cleanLine.startsWith("FILE_DONE|")) {
        const p = cleanLine.split("|");
        if (p.length >= 9) {
          const filePath = p.slice(8).join("|");
          const fileName = filePath.split("\\").pop() || filePath.split("/").pop();
          let sizeMB = "0.00";

          try {
            const stat = await Deno.stat(filePath);
            sizeMB = (stat.size / 1024 / 1024).toFixed(2);
          } catch {}

          const msg1 = "\n";
          const msg2 = `[OK] ${fileName}\n`;
          let msg3 = "";

          if (command === "video") {
            const formats = p[2].split("+");
            const videoFormat = formats[0] || "";
            const audioFormat = formats[1] || "";
            msg3 = `  ${p[1]} | ${p[5]} | ${videoFormat} ${p[3]} ${formatKbps(p[6])} kbps | ${audioFormat} ${p[4]} ${formatKbps(p[7])} kbps | ${sizeMB} MB\n`;
          } else {
            msg3 = `  ${p[1]} | ${p[2]} | ${p[4]} | ${formatKbps(p[7])} kbps | ${sizeMB} MB\n`;
          }

          // Çıktıları tamponlamadan anında Python'a basar:
          Deno.stdout.writeSync(encoder.encode(msg1 + msg2 + msg3));
        }
      } else {
        // CANLI FLUSH: console.log yerine doğrudan stdout'a anında yazdırıyoruz
        Deno.stdout.writeSync(encoder.encode(cleanLine + "\n"));
      }
    }
  }
}

// İki akışı paralel başlat
await Promise.all([
  streamOutput(child.stdout),
  streamOutput(child.stderr)
]);

const status = await child.status;

if (!status.success) {
  Deno.exit(status.code);
}