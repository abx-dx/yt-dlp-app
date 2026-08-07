BROWSER = "firefox"


def cookie_args(enabled: bool) -> list[str]:

    if not enabled:
        return []

    return [
        "--cookies-from-browser",
        BROWSER,
    ]