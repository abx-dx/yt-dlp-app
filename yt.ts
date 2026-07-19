const configFile = new URL("./config.json", import.meta.url);

const config = JSON.parse(
  await Deno.readTextFile(configFile)
);


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


const [command, originalUrl] = Deno.args;


if (!command || !originalUrl) {

  console.log(
    "Kullanım:\nyt video URL\nyt audio URL\nyt playlist URL\nyt info URL"
  );

  Deno.exit(1);

}


let url = originalUrl;


if (url.startsWith("https://music.youtube.com/playlist")) {

  url = url.replace(
    "music.youtube.com",
    "www.youtube.com"
  );

}


const profileConfig =
  config.profiles[command];


let output =
  profileConfig?.output ||
  config.output;


const ytdlpArgs: string[] = [];


if (config.cookies?.enabled) {

  ytdlpArgs.push(
    "--cookies-from-browser",
    config.cookies.browser
  );

}


ytdlpArgs.push(
  "--continue",
  "--no-overwrites",
  "--windows-filenames",
  "--newline",
  "--progress",
  "--retries",
  "infinite",
  "--fragment-retries",
  "infinite",
  "--embed-thumbnail",
  "--convert-thumbnails",
  "jpg",
  "--embed-metadata",
  "--encoding",
  "utf-8"
);


// Playlist hazırlığı

if (command === "playlist") {

  try {

    const infoArgs: string[] = [];


    if (config.cookies?.enabled) {

      infoArgs.push(
        "--cookies-from-browser",
        config.cookies.browser
      );

    }


    infoArgs.push(
      "-J",
      "--flat-playlist",
      url
    );


    const infoCmd =
      new Deno.Command(
        config.ytdlp,
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


    output =
      `./downloads/${folder}/%(playlist_index)0${padding}d - %(artist,uploader)s - %(title)s.%(ext)s`;


  } catch {

    output =
      "./downloads/%(playlist_index)s - %(artist,uploader)s - %(title)s.%(ext)s";

  }

}


// FILE_DONE

ytdlpArgs.push(
  "--print",
  "after_move:FILE_DONE|%(id)s|%(format_id)s|%(vcodec)s|%(acodec)s|%(resolution)s|%(vbr)s|%(abr)s|%(filepath)s"
);


// aria2

if (config.aria2) {

  try {

    await Deno.stat(config.aria2);


    ytdlpArgs.push(
      "--downloader",
      config.aria2,
      "--downloader-args",
      "aria2c:-x 16 -s 16 -j 16 -k 1M"
    );


  } catch {}

}


// info

if (command === "info") {

  ytdlpArgs.push(
    "--dump-json",
    url
  );

}

else {


  const profile =
    config.profiles[command];


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

const process =
  new Deno.Command(
    config.ytdlp,
    {
      args: ytdlpArgs,
      stdout: "piped",
      stderr: "inherit"
    }
  );


const child =
  process.spawn();


const decoder =
  new TextDecoder("utf-8");


let buffer = "";


if (child.stdout) {

  for await (const chunk of child.stdout) {


    buffer += decoder.decode(chunk);


    const lines =
      buffer.split("\n");


    buffer =
      lines.pop() || "";


    for (const line of lines) {


      if (!line.startsWith("FILE_DONE|")) {
        continue;
      }


      const p =
        line.split("|");


      if (p.length >= 9) {


        const filePath =
          p.slice(8).join("|");


        const fileName =
          filePath.split("\\").pop();


        let sizeMB =
          "0.00";


        try {

          const stat =
            await Deno.stat(filePath);


          sizeMB =
            (
              stat.size /
              1024 /
              1024
            ).toFixed(2);


        } catch {}


        console.log("");

        console.log(
          `[OK] ${fileName}`
        );


        if (command === "video") {


          const formats =
            p[2].split("+");


          const videoFormat =
            formats[0] || "";


          const audioFormat =
            formats[1] || "";


          console.log(
            `  ${p[1]} | ${p[5]} | ${videoFormat} ${p[3]} ${formatKbps(p[6])} kbps | ${audioFormat} ${p[4]} ${formatKbps(p[7])} kbps | ${sizeMB} MB`
          );


        }

        else {


          console.log(
            `  ${p[1]} | ${p[2]} | ${p[4]} | ${formatKbps(p[7])} kbps | ${sizeMB} MB`
          );


        }

      }

    }

  }

}


const status =
  await child.status;


if (!status.success) {

  Deno.exit(
    status.code
  );

}