"""
mpv player launcher.

Handles:
  - Launching mpv with a stream URL
  - Passing HTTP headers (Referer, User-Agent) via --http-header-fields
  - Passing HLS-specific options
  - Skip times for openings/endings (Anilibria)
"""
from __future__ import annotations
import subprocess
import sys
import os
from typing import Optional

from .models import Quality, Episode

MPV_BINARY = os.environ.get("MPV_BIN", "mpv")


def _check_mpv():
    if subprocess.run(["which", MPV_BINARY], capture_output=True).returncode != 0:
        print(
            f"[ERROR] mpv не знайдено.\n"
            "  Встановіть: sudo pacman -S mpv",
            file=sys.stderr,
        )
        sys.exit(1)


def play(
    quality: Quality,
    episode: Optional[Episode] = None,
    title: str = "",
):
    """
    Launch mpv with the given stream quality.
    Blocks until mpv exits.
    """
    _check_mpv()

    args = [MPV_BINARY]

    # Window title
    ep_label = f" — Серія {episode.number}" if episode else ""
    args += [f"--title={title}{ep_label}"]

    # HTTP headers
    header_fields = []
    if quality.headers.get("Referer"):
        header_fields.append(f"Referer: {quality.headers['Referer']}")
    if quality.headers.get("User-Agent"):
        header_fields.append(f"User-Agent: {quality.headers['User-Agent']}")

    if header_fields:
        args += [f"--http-header-fields={','.join(header_fields)}"]

    # HLS options for smoother streaming
    if ".m3u8" in quality.url:
        args += [
            "--demuxer-max-bytes=150MiB",
            "--cache=yes",
            "--stream-lavf-o=reconnect=1",
            "--stream-lavf-o=reconnect_streamed=1",
            "--stream-lavf-o=reconnect_delay_max=5",
        ]

    # Skip times (Anilibria openings/endings)
    if episode:
        skips = episode._meta.get("skips", {})
        opening = skips.get("opening", [])
        ending = skips.get("ending", [])
        if opening and len(opening) >= 2:
            # Add chapter marks for opening skip
            args += [f"--start={opening[0]}"]
        if ending and len(ending) >= 2:
            # Set end time to skip ending
            args += [f"--end={ending[0]}"]

    # OSD display of quality
    args += [f"--osd-msg1=Якість: {quality.label}"]

    # The stream URL
    args.append(quality.url)

    try:
        subprocess.run(args)
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        print(f"[ERROR] mpv не знайдено: {MPV_BINARY}", file=sys.stderr)
        sys.exit(1)
