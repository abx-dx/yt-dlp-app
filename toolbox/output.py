from __future__ import annotations

from .profiles import DOWNLOAD_DIR, Profile


def build_output(
    profile: Profile,
    output_dir: str | None,
) -> str:

    output = profile.output

    if output_dir:
        output = output.replace(
            DOWNLOAD_DIR,
            output_dir.replace("\\", "/"),
        )

    return output