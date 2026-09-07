import os
import asyncio
import tempfile
import shutil
import logging
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
import yt_dlp
import aiohttp
import aiofiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ─── Config ───
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MAX_SIZE_GB = 2
MAX_SIZE_BYTES = MAX_SIZE_GB * 1024 * 1024 * 1024

# ─── Init Client ───
client = TelegramClient("session", API_ID, API_HASH)

# ─── Download Helpers ───
async def download_direct(url: str, path: str, status_msg):
    """Download direct MP4/URLs with progress updates."""
    async with aiohttp.ClientSession() as session:
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
                                await status_msg.edit(f"⬇️ Downloading... {percent}%")
                            except:
                                pass

async def download_ytdlp(url: str, outtmpl: str):
    """Download via yt-dlp (handles m3u8, HLS, DASH, Bunny.net, etc.)."""
    loop = asyncio.get_event_loop()
    
    def _download():
        ydl_opts = {
            "outtmpl": outtmpl,
            "format": "best[filesize<2G]/best/bestvideo+bestaudio",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info.get("requested_downloads"):
                return info["requested_downloads"][0]["filepath"]
            return ydl.prepare_filename(info)
    
    return await loop.run_in_executor(None, _download)

# ─── Handlers ───
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🎬 **Video Downloader Bot**\n\n"
        "Send me any video link and I'll download & upload it here.\n\n"
        "✅ Direct MP4 / Signed URLs\n"
        "✅ m3u8 / HLS / Bunny.net\n"
        "✅ YouTube, Facebook, TikTok, etc.\n\n"
        f"⚠️ Max file size: **{MAX_SIZE_GB} GB**",
        parse_mode="markdown"
    )

@client.on(events.NewMessage)
async def handle_message(event):
    if not event.text or event.text.startswith("/"):
        return
    
    url = event.text.strip()
    status = await event.reply("🔍 Checking URL...")
    tmpdir = tempfile.mkdtemp()
    
    try:
        base_path = os.path.join(tmpdir, "video")
        is_m3u8 = ".m3u8" in url
        is_direct_mp4 = url.endswith(".mp4") or "download.mp4" in url or "X-Amz" in url
        
        await status.edit("⬇️ Downloading... Please wait.")
        
        if is_m3u8 or not is_direct_mp4:
            filepath = await download_ytdlp(url, base_path + ".%(ext)s")
        else:
            filepath = base_path + ".mp4"
            await download_direct(url, filepath, status)
        
        if not os.path.exists(filepath):
            raise Exception("Download failed — file not found.")
        
        size = os.path.getsize(filepath)
        if size > MAX_SIZE_BYTES:
            raise Exception(f"File is {size/1e9:.2f} GB. Max: {MAX_SIZE_GB} GB.")
        
        await status.edit("📤 Uploading to Telegram...")
        
        last_percent = -1
        async def progress(current, total):
            nonlocal last_percent
            percent = int(current / total * 100)
            if percent != last_percent and percent % 10 == 0:
                last_percent = percent
                try:
                    await status.edit(f"📤 Uploading... {percent}%")
                except:
                    pass
        
        await client.send_file(
            event.chat_id,
            filepath,
            caption="✅ Done! Here is your video.",
            supports_streaming=True,
            progress_callback=progress,
            attributes=[DocumentAttributeVideo(supports_streaming=True)]
        )
        
        await status.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await status.edit(f"❌ Error: `{str(e)}`", parse_mode="markdown")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# ─── Main ───
async def main():
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    logger.info(f"Bot running as @{me.username}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
