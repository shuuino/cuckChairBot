import asyncio
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
import yt_dlp

from bot_instance import bot, server_lock_interaction

# -------------------------------------------
# x command config

SUPPORTED_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".gif",
}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
_X_MEDIA_EXTS = SUPPORTED_EXTS | {".mp4", ".webm"}

# Required for sensitive/age-restricted posts. Set None to disable.
# trying out this to bypass the "verify your age to view" but i'm in europe so i doubt it'll work
TWITTER_COOKIES_FILE: Optional[str] = "cookies.txt"
_COOKIE_FILE: Optional[str] = (
    TWITTER_COOKIES_FILE
    if TWITTER_COOKIES_FILE and os.path.isfile(TWITTER_COOKIES_FILE)
    else None
)

# GIF quality — target size raised to Discord's 25 MB attachment cap
_GIF_TARGET_BYTES = 25 * 1024 * 1024
_GIF_MAX_DURATION = 30  # seconds

_GIF_QUALITY_LADDER: list[tuple[int, int, int]] = [
    (15, 480, 256),
    (12, 420, 256),
    (10, 360, 192),
    (8,  320, 128),
    (6,  240, 96),
    (5,  180, 64),
]

# -------------------------------------------
# tool detection

_FFMPEG_SEARCH_PATHS = [
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\ffmpeg\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    r"C:\tools\ffmpeg\bin\ffmpeg.exe",
]

def _find_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    for p in _FFMPEG_SEARCH_PATHS:
        if os.path.isfile(p):
            return p
    raise RuntimeError(
        "ffmpeg not found. "
        "Windows: https://ffmpeg.org/download.html  "
        "Linux: sudo apt install ffmpeg"
    )

def _find_gallerydl() -> Optional[str]:
    found = shutil.which("gallery-dl")
    if found:
        return found
    for c in [r"C:\gallery-dl\gallery-dl.exe", r"C:\tools\gallery-dl.exe"]:
        if os.path.isfile(c):
            return c
    return None

FFMPEG    = _find_ffmpeg()
GALLERYDL = _find_gallerydl()

# -------------------------------------------
# ffmpeg helpers

def _run_ffmpeg(args: list[str]) -> None:
    cmd = [FFMPEG, "-threads", "0"] + args
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, cmd, stderr=r.stderr)

# -------------------------------------------
# gif conversion

def _convert_video_to_gif(input_path: str, output_path: str, fps: int, scale: int, colors: int) -> None:
    palette  = output_path + ".pal.png"
    vf_scale = f"fps={fps},scale={scale}:-2:flags=bicubic"
    try:
        _run_ffmpeg(["-y", "-i", input_path, "-t", str(_GIF_MAX_DURATION),
                     "-vf", f"{vf_scale},palettegen=max_colors={colors}:stats_mode=full", palette])
        _run_ffmpeg(["-y", "-i", input_path, "-t", str(_GIF_MAX_DURATION), "-i", palette,
                     "-filter_complex", f"{vf_scale}[x];[x][1:v]paletteuse=dither=floyd_steinberg",
                     output_path])
    finally:
        if os.path.exists(palette):
            os.remove(palette)

def convert_to_gif(input_path: str, output_path: str) -> bool:
    """Returns True if output is a native image passthrough, False if a real GIF."""
    ext = Path(input_path).suffix.lower()

    if ext in IMAGE_EXTS:
        shutil.copy2(input_path, output_path)
        return True

    if ext == ".gif" and os.path.getsize(input_path) <= _GIF_TARGET_BYTES:
        shutil.copy2(input_path, output_path)
        return False

    n = len(_GIF_QUALITY_LADDER)
    lo, hi = 0, n - 1
    last_attempt = n - 1

    while lo <= hi:
        mid = (lo + hi) // 2
        fps, scale, colors = _GIF_QUALITY_LADDER[mid]
        _convert_video_to_gif(input_path, output_path, fps, scale, colors)
        size = os.path.getsize(output_path)
        if size <= _GIF_TARGET_BYTES:
            last_attempt = mid
            hi = mid - 1
        else:
            lo = mid + 1

    if last_attempt != (lo - 1 if lo > 0 else 0):
        fps, scale, colors = _GIF_QUALITY_LADDER[last_attempt]
        if os.path.getsize(output_path) > _GIF_TARGET_BYTES:
            _convert_video_to_gif(input_path, output_path, fps, scale, colors)

    return False

# -------------------------------------------
# shared helpers

def _sanitise_filename(name: str) -> str:
    clean = re.sub(r'[\/:*?"<>|]', "", name)
    clean = re.sub(r"\s+", "_", clean).strip("._")
    return clean or "output"

# URL normalisation: replace any domain with x.com, validate result
_URL_RE = re.compile(r"^(https?://)(?:www\.)?[^/\s]+(/\S+)$", re.IGNORECASE)
_X_STATUS_RE = re.compile(r"^https?://x\.com/\S+/status/\d+", re.IGNORECASE)

def _normalise_to_x(raw_link: str) -> Optional[str]:
    """Swap the link's domain for x.com. Returns the rebuilt URL only if it
    matches a valid x.com status link shape; otherwise None (invalid)."""
    m = _URL_RE.match(raw_link.strip())
    if not m:
        return None
    candidate = f"{m.group(1)}x.com{m.group(2)}"
    if _X_STATUS_RE.match(candidate):
        return candidate
    return None

# -------------------------------------------
# yt-dlp / gallery-dl

def _cookie_args() -> list[str]:
    return ["--cookies", _COOKIE_FILE] if _COOKIE_FILE else []

def _cookie_opts() -> dict:
    return {"cookiefile": _COOKIE_FILE} if _COOKIE_FILE else {}

class _YTDLPError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.user_msg = msg

def _check_fatal(msg: str) -> Optional[str]:
    ml = msg.lower()
    if "login" in ml or "private" in ml:
        return "❌ Private account or login required."
    if "sensitive" in ml or "age" in ml or "age-restricted" in ml:
        return (
            "❌ This post is marked as sensitive/age-restricted.\n"
            "To fetch it, log in to X in your browser, export a **cookies.txt** file, "
            "place it next to the bot as `cookies.txt`, and restart."
        )
    if "404" in ml or "not found" in ml:
        return "❌ Tweet not found (deleted or invalid URL)."
    return None

def _ytdlp_download_sync(link: str, dl_template: str, extractor_api: Optional[str] = None) -> None:
    opts: dict = {
        "noplaylist":          True,
        "merge_output_format": "mp4",
        "quiet":               True,
        "no_warnings":         True,
        **_cookie_opts(),
    }
    if extractor_api:
        opts["extractor_args"] = {"twitter": {"api": [extractor_api]}}
    opts["outtmpl"] = dl_template
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([link])
    except yt_dlp.utils.DownloadError as e:
        fatal = _check_fatal(str(e))
        if fatal:
            raise _YTDLPError(fatal) from e
        raise

async def _ytdlp_with_fallback(link: str, dl_template: str) -> tuple[bool, Optional[str]]:
    try:
        await asyncio.to_thread(_ytdlp_download_sync, link, dl_template)
        return True, None
    except _YTDLPError as e:
        return False, e.user_msg
    except yt_dlp.utils.DownloadError:
        pass

    try:
        await asyncio.to_thread(_ytdlp_download_sync, link, dl_template, "syndication")
        return True, None
    except _YTDLPError as e:
        return False, e.user_msg
    except yt_dlp.utils.DownloadError as e:
        return False, _check_fatal(str(e))

async def _run_gallerydl(link: str, tmpdir: str, filename_tmpl: str, cookies: list[str]) -> tuple[int, str]:
    args = [GALLERYDL, "--dest", tmpdir, "--filename", filename_tmpl] + cookies + [link]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    gerr = stderr_b.decode("utf-8", errors="replace").strip()
    return proc.returncode, gerr

def _is_sensitive_error(stderr: str) -> bool:
    gl = stderr.lower()
    return "sensitive" in gl or "age" in gl or "login" in gl or "private" in gl

_SENSITIVE_MSG = (
    "❌ This post is marked as sensitive/age-restricted.\n"
    "Export a **cookies.txt** from your browser while logged into X "
    "and place it next to the bot, then try again."
)

# -------------------------------------------
# /x command core logic

async def _fetch_x_media(interaction: discord.Interaction, link: str, tmpdir: str) -> Optional[list[Path]]:
    cookies = _cookie_args()
    dl_tmpl = os.path.join(tmpdir, "media_%(autonumber)s.%(ext)s")

    ok, fatal = await _ytdlp_with_fallback(link, dl_tmpl)
    if not ok and fatal:
        await interaction.followup.send(fatal); return None

    downloaded = sorted(
        f for f in Path(tmpdir).glob("media_*.*")
        if f.suffix.lower() in _X_MEDIA_EXTS
    )

    if not downloaded and GALLERYDL:
        rc, gerr = await _run_gallerydl(link, tmpdir, "galimg_{num}.{extension}", cookies)
        if rc != 0 and _is_sensitive_error(gerr):
            await interaction.followup.send(_SENSITIVE_MSG); return None
        downloaded = sorted(
            f for f in Path(tmpdir).rglob("galimg_*.*")
            if f.suffix.lower() in SUPPORTED_EXTS
        )

    return downloaded

@bot.tree.command(name="x", description="Download media from a Twitter/X post and return as GIF(s).")
@app_commands.describe(
    link="Twitter/X status URL (any known embed domain also works).",
    filename="Optional name for the output file (without extension). Ignored when multiple media items are found.",
)
async def x_command(interaction: discord.Interaction, link: str, filename: Optional[str] = None):
    if not server_lock_interaction(interaction):
        return

    normalised = _normalise_to_x(link)
    if normalised is None:
        await interaction.response.send_message(
            "❌ Invalid Twitter/X URL. Expected: `https://x.com/username/status/123…`", ephemeral=True); return

    await interaction.response.defer(thinking=True)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            downloaded = await _fetch_x_media(interaction, normalised, tmpdir)
            if downloaded is None:
                return

            if not downloaded:
                await interaction.followup.send(
                    "❌ No media found. May be text-only, deleted, sensitive, or require login."
                ); return

            gif_paths: list[Optional[str]] = [None] * len(downloaded)

            async def _convert_one(idx: int, media_path: Path) -> None:
                ext = media_path.suffix.lower()
                if ext in IMAGE_EXTS:
                    out = os.path.join(tmpdir, f"tweet_{idx}{ext}")
                    shutil.copy2(str(media_path), out)
                    gif_paths[idx] = out
                    return
                out = os.path.join(tmpdir, f"tweet_{idx}.gif")
                try:
                    await asyncio.to_thread(convert_to_gif, str(media_path), out)
                    gif_paths[idx] = out
                except Exception:
                    pass

            await asyncio.gather(*[_convert_one(i, p) for i, p in enumerate(downloaded)])

            sent = 0
            for idx, gif_path in enumerate(gif_paths, start=1):
                if gif_path is None:
                    await interaction.followup.send(f"⚠️ Item {idx} failed to convert — skipping."); continue
                size = os.path.getsize(gif_path)
                if size > 25 * 1024 * 1024:
                    await interaction.followup.send(f"⚠️ Item {idx}: {size/1024/1024:.1f} MB — too large, skipping."); continue
                if len(downloaded) > 1:
                    label = f"tweet_{idx}"
                elif filename:
                    label = _sanitise_filename(filename)
                else:
                    label = "tweet"
                prefix = f"✅ Here's your GIF, {interaction.user.mention}!" if sent == 0 else f"📎 Media {idx}:"
                try:
                    await interaction.followup.send(prefix, file=discord.File(gif_path, filename=f"{label}.gif"))
                    sent += 1
                except discord.HTTPException as e:
                    await interaction.followup.send(f"⚠️ Item {idx} upload failed (Discord {e.status}) — skipping.")

            if sent == 0:
                await interaction.followup.send("❌ All media items failed or were too large.")
    except Exception:
        try: await interaction.followup.send("❌ Something went wrong. Please try again.")
        except Exception: pass
