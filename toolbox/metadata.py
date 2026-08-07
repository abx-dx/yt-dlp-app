# toolbox/metadata.py

from __future__ import annotations

from pathlib import Path


def format_file_size(file_path: Path) -> str:
    if not file_path.exists():
        return "0.00"
    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    return f"{size_mb:.2f}"


def format_kbps(val: str) -> str:
    try:
        fval = float(val)
        return f"{fval:.2f}"
    except (ValueError, TypeError):
        return val
        
        
def normalize_resolution(resolution: str) -> str:
    resolution = resolution.strip()

    if "x" in resolution:
        resolution = resolution.rsplit("x", 1)[1]

    return resolution.replace("p", "")


def resolution_message(
    actual: str,
    target: str | None,
) -> str:

    if not target or target == "En İyi":
        return (
            f"  [Bilgi] Mevcut en yüksek çözünürlük "
            f"({actual}p) indirildi.\n"
        )

    target = (
        target
        .split("(")[-1]
        .replace("p)", "")
        .replace("p", "")
        .strip()
    )

    if actual.isdigit() and target.isdigit():

        act = int(actual)
        tgt = int(target)

        if act < tgt:
            return (
                f"  [Bilgi] İstenen çözünürlük "
                f"({tgt}p) bu videoda bulunamadı. "
                f"Mevcut en yüksek çözünürlük "
                f"({act}p) indirildi.\n"
            )

        if act == tgt:
            return (
                f"  [Bilgi] Hedeflenen çözünürlük "
                f"({act}p) indirildi.\n"
            )

        return (
            f"  [Bilgi] {act}p çözünürlük indirildi.\n"
        )

    return (
        f"  [Bilgi] {actual} çözünürlük indirildi.\n"
    )


def format_file_done_report(profile_name: str, line: str, target_res: str | None = None) -> str:
    parts = line.split("|")
    if len(parts) < 9:
        return line

    video_id = parts[1]
    format_id = parts[2]
    vcodec = parts[3]
    acodec = parts[4]
    resolution = parts[5]
    vbr = parts[6]
    abr = parts[7]
    file_path = Path(parts[8])

    size_mb = format_file_size(file_path)

    msg1 = f"[OK] {file_path.name}\n\n"

    if profile_name == "video":

        actual_height = normalize_resolution(resolution)

        info_note = resolution_message(
            actual_height,
            target_res,
        )

        video_format, *rest = format_id.split("+")
        audio_format = rest[0] if rest else ""

        msg3 = (
            f"  {video_id} | {resolution} | "
            f"{video_format} {vcodec} {format_kbps(vbr)} kbps | "
            f"{audio_format} {acodec} {format_kbps(abr)} kbps | "
            f"{size_mb} MB\n"
        )

        return msg1 + info_note + msg3

    msg3 = (
        f"  {video_id} | {format_id} | {acodec} | "
        f"{format_kbps(abr)} kbps | {size_mb} MB\n"
    )
    return msg1 + msg3