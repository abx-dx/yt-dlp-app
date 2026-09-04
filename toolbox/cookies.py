from __future__ import annotations


def cookie_args(
    mode: str = "none",
    value: str | None = None,
) -> list[str]:
    if mode == "none":
        return []

    if mode == "browser":
        if not value:
            raise ValueError(
                "Tarayıcı belirtilmedi."
            )

        return [
            "--cookies-from-browser",
            value.lower(),
        ]

    if mode == "file":
        if not value:
            raise ValueError(
                "Cookie dosyası belirtilmedi."
            )

        return [
            "--cookies",
            value,
        ]

    raise ValueError(
        f"Bilinmeyen cookie modu: {mode}"
    )