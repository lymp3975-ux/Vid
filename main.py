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

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MAX_SIZE_GB = 2
MAX_SIZE_BYTES = MAX_SIZE_GB * 1024 * 1024 * 1024

client = TelegramClient("session", API_ID, API_HASH)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
}

async def download_with_retry(url, path, status_msg):
    """Download full file with resume support and real-time progress."""
    max_retries = 5
    chunk_size = 1024 * 1024
    downloaded = 0
    total = 0
    
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.head(url, timeout=30) as resp:
                    if resp.status == 200:
                        total = int(resp.headers.get("content-length", 0))
                        break
        except Exception as e:
            logger.warning(f"HEAD attempt {attempt+1} failed: {e}")
            await asyncio.sleep(1)
    
    if total > MAX_SIZE_BYTES:
        raise Exception(f"File too large ({total/1e9:.2f} GB > {MAX_SIZE_GB} GB)")
    
    last_percent = -1
    
    for attempt in range(max_retries):
        try:
            range_header = {}
            if downloaded > 0 and total > 0:
                range_header = {"Range": f"bytes={downloaded}-"}
                logger.info(f"Resuming from {downloaded}/{total}")
            
            async with aiohttp.ClientSession(headers={**HEADERS, **range_header}) as session:
                async with session.get(url, timeout=None) as resp:
                    if resp.status not in (200, 206):
                        raise Exception(f"HTTP {resp.status}")
                    
                    mode = "ab" if downloaded > 0 else "wb"
                    async with aiofiles.open(path, mode) as f:
                        async for chunk in resp.content.iter_chunked(chunk_size):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total:
                                percent = int(downloaded / total * 100)
                                if percent != last_percent and percent % 5 == 0:
                                    last_percent = percent
                                    try:
                                        await status_msg.edit(f"⬇️ Downloading... {percent}%")
                                    except:
                                        pass
            
            if total and os.path.getsize(path) < total:
                raise Exception("Incomplete, retrying...")
            return
            
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                raise Exception(f"Failed after {max_retries} retries: {e}")

async def download_trim(url, path, status_msg, start_time="0", duration="60"):
    """Use ffmpeg to download a specific clip."""
    header_lines = [f"{k}: {v}" for k, v in HEADERS.items()]
    headers_str = "\r\n".join(header_lines) + "\r\n"
    
    cmd = [
        "ffmpeg", "-y",
        "-headers", headers_str,
        "-ss", start_time,    # ← Start time (e.g., 10:00)
        "-i", url,
        "-t", duration,       # ← Duration (e.g., 60)
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        path
    ]
    
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    
    await status_msg.edit(f"⏱ Trimming {start_time} to {duration} with ffmpeg...")
    
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        err = stderr.decode()[-500:] if stderr else "Unknown error"
        raise Exception(f"ffmpeg trim failed: {err}")
    
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise Exception("Trim produced no output")

async def download_ytdlp(url, outtmpl):
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

@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🎬 Video Downloader Bot\n\n"
        "Commands:\n"
        "/start - Show help\n"
        "/trim START DURATION URL - Download a clip\n\n"
        "Examples:\n"
        "`/trim 0 1:00 url` → First 1 minute\n"
        "`/trim 10:00 1:00 url` → From 10:00 to 11:00\n"
        "`/trim 2:30:00 30 url` → From 2:30:00, 30 seconds\n\n"
        "Just send URL → Download full video\n\n"
        f"⚠️ Max file size: {MAX_SIZE_GB} GB",
        parse_mode="markdown"
    )

@client.on(events.NewMessage(pattern="/trim"))
async def trim_video(event):
    """Download a specific time range."""
    if event.out:
        return
    
    text = event.text.replace("/trim", "").strip()
    parts = text.split()
    
    if len(parts) < 1:
        await event.reply(
            "Usage: `/trim START DURATION URL`\n\n"
            "Examples:\n"
            "`/trim 0 1:00 https://link.mp4`\n"
            "`/trim 10:00 1:00 https://link.mp4` → 10 to 11 min\n"
            "`/trim 2:30 30 https://link.mp4` → 2:30 to 2:31",
            parse_mode="markdown"
        )
        return
    
    # Parse: can be "START DURATION URL" or just "URL" (defaults 0, 60)
    if len(parts) == 1:
        start_time = "0"
        duration = "60"
        url = parts[0]
    elif len(parts) == 2:
        start_time = "0"
        duration = parts[0]
        url = parts[1]
    else:
        start_time = parts[0]
        duration = parts[1]
        url = parts[2]
    
    status = await event.reply(f"⏱ Trimming {start_time} for {duration}...")
    tmpdir = tempfile.mkdtemp()
    
    try:
        filepath = os.path.join(tmpdir, "video_trimmed.mp4")
        await download_trim(url, filepath, status, start_time, duration)
        
        size = os.path.getsize(filepath)
        if size > MAX_SIZE_BYTES:
            raise Exception(f"File is {size/1e9:.2f} GB. Max: {MAX_SIZE_GB} GB.")
        
        await status.edit("📤 Uploading... 0%")
        last_percent = -1
        async def progress(current, total):
            nonlocal last_percent
            percent = int(current / total * 100)
            if percent != last_percent and percent % 5 == 0:
                last_percent = percent
                try:
                    await status.edit(f"📤 Uploading... {percent}%")
                except:
                    pass
        
        await client.send_file(
            event.chat_id, filepath,
            caption=f"✅ Done! Clip from {start_time} for {duration}.",
            supports_streaming=True,
            progress_callback=progress,
            attributes=[DocumentAttributeVideo(duration=0, w=0, h=0, supports_streaming=True)]
        )
        await status.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await status.edit(f"❌ Error: {str(e)[:400]}", parse_mode="markdown")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

@client.on(events.NewMessage)
async def handle_message(event):
    if event.out:
        return
    if not event.text or event.text.startswith("/"):
        return
    
    url = event.text.strip()
    status = await event.reply("🔍 Checking URL...")
    tmpdir = tempfile.mkdtemp()
    
    try:
        base_path = os.path.join(tmpdir, "video")
        is_direct_mp4 = url.endswith(".mp4") or "download.mp4" in url or "X-Amz" in url
        
        await status.edit("⬇️ Downloading... 0%")
        
        if is_direct_mp4:
            filepath = base_path + ".mp4"
            await download_with_retry(url, filepath, status)
        else:
            filepath = await download_ytdlp(url, base_path + ".%(ext)s")
        
        if not os.path.exists(filepath):
            raise Exception("Download failed — file not found.")
        
        size = os.path.getsize(filepath)
        if size > MAX_SIZE_BYTES:
            raise Exception(f"File is {size/1e9:.2f} GB. Max: {MAX_SIZE_GB} GB.")
        
        await status.edit("📤 Uploading... 0%")
        last_percent = -1
        async def progress(current, total):
            nonlocal last_percent
            percent = int(current / total * 100)
            if percent != last_percent and percent % 5 == 0:
                last_percent = percent
                try:
                    await status.edit(f"📤 Uploading... {percent}%")
                except:
                    pass
        
        await client.send_file(
            event.chat_id, filepath,
            caption="✅ Done! Here is your video.",
            supports_streaming=True,
            progress_callback=progress,
            attributes=[DocumentAttributeVideo(duration=0, w=0, h=0, supports_streaming=True)]
        )
        await status.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await status.edit(f"❌ Error: {str(e)[:400]}", parse_mode="markdown")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

async def main():
    logger.info("Starting bot...")
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    logger.info(f"Bot running as @{me.username}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
