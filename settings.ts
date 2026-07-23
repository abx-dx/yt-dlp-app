export interface CookiesConfig {
  enabled: boolean;
  browser: "firefox";
}

export interface ProfileConfig {
  format: string;
  output: string;
  playlist?: boolean;
  args: string[];
}

export interface Config {
  ytdlp: string;
  ffmpeg: string;
  cookies: CookiesConfig;
  profiles: Record<string, ProfileConfig>;
}

const config: Config = {
  ytdlp: "./bin/yt-dlp.exe",

  ffmpeg: "./bin/ffmpeg.exe",

  cookies: {
    enabled: true,
    browser: "firefox",
  },

  profiles: {
    video: {
      format: "bestvideo+bestaudio/best",
      output: "./downloads/%(title)s.%(ext)s",
      args: [
        "--merge-output-format",
        "mkv",
      ],
    },

    audio: {
      format: "bestaudio[acodec=opus]/bestaudio",
      output: "./downloads/%(artist)s - %(title)s.%(ext)s",
      args: [
        "--remux-video",
        "opus",
        "--embed-metadata",
        "--embed-thumbnail",
      ],
    },

    playlist: {
      format: "bestaudio[acodec=opus]/bestaudio",
      playlist: true,
      output:
        "./downloads/%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s",
      args: [
        "--yes-playlist",
        "--remux-video",
        "opus",
        "--embed-metadata",
        "--embed-thumbnail",
      ],
    },
  },
};

export default config;