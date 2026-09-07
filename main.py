import os
import asyncio
import tempfile
import shutil
import logging
import re
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
import yt_dlp
import aiohttp
import aiofiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ─── Config ───
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAX_SIZE_GB = 2
MAX_SIZE_BYTES = MAX_SIZE_GB * 1024 * 1024 * 1024

# ─── VALIDATE ENV VARS ───
missing = []
if not API_ID:
    missing.append("API_ID")
if not API_HASH:
    missing.append("API_HASH")
if not BOT_TOKEN:
    missing.append("BOT_TOKEN")

if missing:
    raise RuntimeError(f"MISSING ENV VARIABLES: {', '.join(missing)}. Set them in Railway Variables tab.")

API_ID = int(API_ID)

logger.info(f"API_ID loaded: {API_ID}")
logger.info(f"API_HASH loaded: {'YES' if API_HASH else 'NO'}")
logger.info(f"BOT_TOKEN loaded: {'YES' if BOT_TOKEN else 'NO'}")

# ─── Browser Headers ───
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://bunny.net",
    "Referer": "https://bunny.net/",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
}

# ─── Init Client ───
client = TelegramClient("session", API_ID, API_HASH)

# ─── yt-dlp Base Options ───
def get_ydl_opts(outtmpl: str):
    opts = {
        "outtmpl": outtmpl,
        "format": "best[filesize<2G]/best/bestvideo+bestaudio",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "http_headers": BROWSER_HEADERS,
        "extractor_args": {
            "youtube": {
                "player_client": ["web"],
                "player_skip": ["webpage", "configs", "js"],
            }
        },
    }
    if os.path.exists("/app/cookies.txt"):
        opts["cookiefile"] = "/app/cookies.txt"
        logger.info("Using cookies.txt for yt-dlp")
    return opts

# ─── Download Helpers ───
async def download_direct(url: str, path: str, status_msg):
    async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=None)) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            
            total = int(resp.headers.get("content-length", 0))
            if total > MAX_SIZE_BYTES:
                raise Exception(f"File too large ({total/1e9:.2f} GB > {MAX_SIZE_GB} GB)")
            
            downloaded = 0
            last_percent = -1
            async with aiofiles.open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    await f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = int(downloaded / total * 100)
                        if percent != last_percent and percent % 10 == 0:
                            last_percent = percent
                            try:
                                await status_msg.edit(f"Downloading... {percent}%")
                            except:
                                pass

async def download_ytdlp(url: str, outtmpl: str):
    loop = asyncio.get_event_loop()
    
    def _download():
        ydl_opts = get_ydl_opts(outtmpl)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info.get("requested_downloads"):
                return info["requested_downloads"][0]["filepath"]
            return ydl.prepare_filename(info)
    
    return await loop.run_in_executor(None, _download)

async def download_ffmpeg_m3u8(url: str, path: str, status_msg):
    """ffmpeg fallback with proper CRLF headers."""
    header_lines = [f"{k}: {v}" for k, v in BROWSER_HEADERS.items()]
    headers_str = "\r\n".join(header_lines) + "\r\n"
    
    cmd = [
        "ffmpeg", "-y",
        "-headers", headers_str,
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        path
    ]
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    await status_msg.edit("Downloading via ffmpeg...")
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        err = stderr.decode()[-800:] if stderr else "Unknown error"
        raise Exception(f"ffmpeg failed: {err}")
    
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise Exception("ffmpeg produced no output")
    
    return path

async def download_m3u8_manual(url: str, path: str, status_msg):
    """Manually download m3u8 playlist + segments, then concat with ffmpeg."""
    tmpdir = tempfile.mkdtemp()
    
    try:
        # Step 1: Download m3u8 playlist
        async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    raise Exception(f"m3u8 playlist HTTP {resp.status}")
                m3u8_text = await resp.text()
        
        # Step 2: Parse segments
        base_url = url.rsplit("/", 1)[0] + "/"
        segments = []
        for line in m3u8_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("http"):
                segments.append(line)
            else:
                # Relative path
                segments.append(base_url + line)
        
        if not segments:
            raise Exception("No video segments found in m3u8")
        
        logger.info(f"Found {len(segments)} segments")
        
        # Step 3: Download all segments
        seg_dir = os.path.join(tmpdir, "segs")
        os.makedirs(seg_dir, exist_ok=True)
        seg_files = []
        
        async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
            for i, seg_url in enumerate(segments):
                seg_path = os.path.join(seg_dir, f"{i:05d}.ts")
                async with session.get(seg_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status != 200:
                        raise Exception(f"Segment {i+1}/{len(segments)} failed: HTTP {resp.status}")
                    async with aiofiles.open(seg_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024 * 1024):
                            await f.write(chunk)
                
                seg_files.append(seg_path)
                
                if i % 5 == 0 or i == len(segments) - 1:
                    try:
                        await status_msg.edit(f"Downloading segments... {i+1}/{len(segments)}")
                    except:
                        pass
        
        # Step 4: Concat with ffmpeg
        concat_file = os.path.join(tmpdir, "concat.txt")
        async with aiofiles.open(concat_file, "w") as f:
            for seg in seg_files:
                await f.write(f"file '{seg}'\n")
        
        await status_msg.edit("Merging segments...")
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            path
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            err = stderr.decode()[-500:] if stderr else "concat failed"
            raise Exception(f"ffmpeg merge failed: {err}")
        
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise Exception("Merge produced no output")
        
        return path
        
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# ─── Handlers ───
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "Video Downloader Bot\n\n"
        "Send me any video link and I'll download & upload it here.\n\n"
        "Direct MP4 / Signed URLs\n"
        "m3u8 / HLS / Bunny.net\n"
        "YouTube (needs cookies.txt)\n\n"
        f"Max file size: {MAX_SIZE_GB} GB",
        parse_mode="markdown"
    )

@client.on(events.NewMessage)
async def handle_message(event):
    if not event.text or event.text.startswith("/"):
        return
    
    url = event.text.strip()
    status = await event.reply("Checking URL...")
    tmpdir = tempfile.mkdtemp()
    
    try:
        base_path = os.path.join(tmpdir, "video")
        is_m3u8 = ".m3u8" in url
        is_direct_mp4 = url.endswith(".mp4") or "download.mp4" in url or "X-Amz" in url
        
        await status.edit("Downloading... Please wait.")
        
        if is_direct_mp4:
            filepath = base_path + ".mp4"
            await download_direct(url, filepath, status)
        elif is_m3u8:
            # Try 3 methods: yt-dlp -> ffmpeg -> manual
            last_error = None
            for method_name, method in [
                ("yt-dlp", lambda: download_ytdlp(url, base_path + ".%(ext)s")),
                ("ffmpeg", lambda: download_ffmpeg_m3u8(url, base_path + ".mp4", status)),
                ("manual segments", lambda: download_m3u8_manual(url, base_path + ".mp4", status)),
            ]:
                try:
                    filepath = await method()
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        break
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"{method_name} failed: {e}")
                    continue
            else:
                raise Exception(f"All download methods failed. Last error: {last_error}")
        else:
            # YouTube, etc.
            filepath = await download_ytdlp(url, base_path + ".%(ext)s")
        
        if not os.path.exists(filepath):
            raise Exception("Download failed — file not found.")
        
        size = os.path.getsize(filepath)
        if size > MAX_SIZE_BYTES:
            raise Exception(f"File is {size/1e9:.2f} GB. Max: {MAX_SIZE_GB} GB.")
        
        await status.edit("Uploading to Telegram...")
        
        last_percent = -1
        async def progress(current, total):
            nonlocal last_percent
            percent = int(current / total * 100)
            if percent != last_percent and percent % 10 == 0:
                last_percent = percent
                try:
                    await status.edit(f"Uploading... {percent}%")
                except:
                    pass
        
        await client.send_file(
            event.chat_id,
            filepath,
            caption="Done! Here is your video.",
            supports_streaming=True,
            progress_callback=progress,
            attributes=[DocumentAttributeVideo(supports_streaming=True)]
        )
        
        await status.delete()
        
    except Exception as e:
        err_str = str(e)
        logger.error(f"Error: {err_str}", exc_info=True)
        
        if "Sign in to confirm" in err_str:
            await status.edit(
                "Error: YouTube is blocking downloads.\n\n"
                "Fix: Add cookies.txt to your repo (export from Chrome while signed into YouTube).",
                parse_mode="markdown"
            )
        elif "HTTP Error 403" in err_str or "403 Forbidden" in err_str:
            await status.edit(
                "Error: 403 Forbidden — the video host is blocking this server.\n\n"
                "Possible reasons:\n"
                "1. The link expired (get a fresh one)\n"
                "2. The link needs a Referer from the original website\n"
                "3. The CDN blocks datacenter IPs (Railway)\n\n"
                "Try: Get a fresh link from the source website and send it immediately.",
                parse_mode="markdown"
            )
        else:
            await status.edit(f"Error: {err_str[:400]}", parse_mode="markdown")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# ─── Main ───
async def main():
    logger.info("Starting bot...")
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    logger.info(f"Bot running as @{me.username}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
