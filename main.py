import os
import asyncio
import tempfile
import shutil
import logging
import subprocess
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
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
    # Use cookies.txt if it exists (for YouTube)
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
    """Fallback for m3u8 that yt-dlp can't handle (403 errors)."""
    headers = "\r\n".join([f"{k}: {v}" for k, v in BROWSER_HEADERS.items()])
    
    cmd = [
        "ffmpeg",
        "-y",
        "-headers", headers,
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
    
    await status_msg.edit("Downloading via ffmpeg... (this may take a while)")
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        err = stderr.decode()[-500:] if stderr else "Unknown ffmpeg error"
        raise Exception(f"ffmpeg failed: {err}")
    
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise Exception("ffmpeg produced no output")
    
    return path

# ─── Handlers ───
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "Video Downloader Bot\n\n"
        "Send me any video link and I'll download & upload it here.\n\n"
        "Direct MP4 / Signed URLs\n"
        "m3u8 / HLS / Bunny.net\n"
        "YouTube (may need cookies.txt)\n\n"
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
            # Try yt-dlp first, fallback to ffmpeg with browser headers
            try:
                filepath = await download_ytdlp(url, base_path + ".%(ext)s")
            except Exception as e:
                logger.warning(f"yt-dlp failed for m3u8: {e}, trying ffmpeg...")
                filepath = base_path + ".mp4"
                await download_ffmpeg_m3u8(url, filepath, status)
        else:
            # YouTube and others
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
                "To fix this, you need to add a cookies.txt file:\n"
                "1. Install 'Get cookies.txt LOCALLY' extension in Chrome\n"
                "2. Go to youtube.com and sign in\n"
                "3. Export cookies as cookies.txt\n"
                "4. Add it to your GitHub repo root\n"
                "5. Redeploy",
                parse_mode="markdown"
            )
        elif "HTTP Error 403" in err_str:
            await status.edit(
                "Error: The video host is blocking the download (403 Forbidden).\n\n"
                "This usually means:\n"
                "- The link expired\n"
                "- The link needs a Referer header from the original website\n"
                "- The host requires login/cookies\n\n"
                "Try getting a fresh link from the source website.",
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
