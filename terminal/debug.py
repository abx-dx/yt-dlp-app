from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path


DEBUG_PORT_ENV = "YTDLP_DEBUG_PORT"
CLI_CHILD_ENV = "YTDLP_CLI_CHILD"

CURRENT_DIR = Path(__file__).resolve().parent.parent


class DebugSocketWriter:
    """
    stdout için socket tabanlı, doğrudan yazan text stream.

    Her write() çağrısında veri doğrudan socket'e gönderilir.
    Böylece makefile()/TextIOWrapper buffering'i kullanılmaz.
    """

    def __init__(self, sock: socket.socket):
        self._socket = sock

    def write(self, text: str) -> int:
        if not text:
            return 0

        data = text.encode(
            "utf-8",
            errors="replace",
        )

        self._socket.sendall(data)

        return len(text)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        return None

    def writable(self) -> bool:
        return True

    def isatty(self) -> bool:
        return False

    @property
    def encoding(self) -> str:
        return "utf-8"


class DebugChannel:
    """
    Küçük terminale runner debug çıktısı aktarır.

    Child PowerShell tarafında kullanılır.
    """

    def __init__(self, port: int):
        self._socket = socket.create_connection(
            ("127.0.0.1", port)
        )

        self._stream = DebugSocketWriter(
            self._socket
        )

    @contextmanager
    def redirect_stdout(self):
        original_stdout = sys.stdout
        sys.stdout = self._stream

        try:
            yield

        finally:
            sys.stdout = original_stdout

    def close(self) -> None:
        try:
            self._stream.flush()

        finally:
            self._socket.close()


def debug_listener(
    listener: socket.socket,
) -> None:
    try:
        while True:
            try:
                conn, _ = listener.accept()
            except OSError:
                break

            try:
                with conn:
                    buffer = b""

                    while True:
                        try:
                            data = conn.recv(4096)
                        except OSError:
                            break

                        if not data:
                            break

                        buffer += data

                        while b"\n" in buffer:
                            line, buffer = buffer.split(
                                b"\n",
                                1,
                            )

                            print(
                                line.decode(
                                    "utf-8",
                                    errors="replace",
                                ),
                                flush=True,
                            )

                    if buffer:
                        print(
                            buffer.decode(
                                "utf-8",
                                errors="replace",
                            ),
                            flush=True,
                        )

            except OSError:
                pass

    finally:
        try:
            listener.close()
        except OSError:
            pass


def launch_application_console() -> None:
    listener = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    listener.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )

    listener.bind(("127.0.0.1", 0))
    listener.listen(1)

    port = listener.getsockname()[1]

    env = os.environ.copy()
    env[CLI_CHILD_ENV] = "1"
    env[DEBUG_PORT_ENV] = str(port)

    listener_thread = threading.Thread(
        target=debug_listener,
        args=(listener,),
        daemon=True,
    )

    listener_thread.start()

    process = subprocess.Popen(
        [
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            "-Command",
            (
                f'& "{sys.executable}" '
                f'"{CURRENT_DIR / "cli.py"}"; '
                f"Start-Sleep -Seconds 1"
            ),
        ],
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    process.wait()

    try:
        listener.close()
    except OSError:
        pass

    listener_thread.join(timeout=1.0)


def get_debug_channel() -> DebugChannel | None:
    port = os.environ.get(DEBUG_PORT_ENV)

    if not port:
        return None

    try:
        return DebugChannel(int(port))

    except (
        ConnectionRefusedError,
        OSError,
    ):
        return None