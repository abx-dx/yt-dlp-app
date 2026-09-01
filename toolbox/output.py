from __future__ import annotations

from .profiles import Profile


def build_output(
    profile: Profile,
    output_dir: str | None,
) -> str:

    if not output_dir:
        return profile.output

    output_dir = output_dir.replace("\\", "/")

    return f"{output_dir}/{profile.output}"