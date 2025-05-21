import os
import re
import aiohttp
import asyncio
import shutil
import img2pdf
import random
import threading
import requests

from PIL import Image
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

from keep_alive import keep_alive

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Kirim ID galeri nhentai (contoh: 177013) dan saya akan mengirimkan PDF-nya.\n\n"
        "Contoh: /download 177013"
    )

async def get_soup(session, url):
    async with session.get(url) as response:
        text = await response.text()
        return BeautifulSoup(text, 'html.parser')

async def download_page(session, url, page, temp_dir, gallery_id):
    try:
        await asyncio.sleep(random.uniform(0.1, 0.2))
        soup = await get_soup(session, url)
        img_tag = soup.select_one('#image-container img')
        img_url = img_tag.get('src') or img_tag.get('data-src')
        img_url = urljoin(url, img_url)

        filename = f"{gallery_id}_{page:03d}.jpg"
        img_path = os.path.join(temp_dir, filename)

        async with session.get(img_url) as r:
            r.raise_for_status()
            with open(img_path, 'wb') as f:
                async for chunk in r.content.iter_chunked(1024):
                    f.write(chunk)

        with Image.open(img_path) as img:
            if img.format != 'JPEG':
                img.convert('RGB').save(img_path, 'JPEG', quality=95)

        return img_path
    except Exception as e:
        print(f"Error halaman {page}: {str(e)}")
        return None

async def download_nhentai_gallery(gallery_id):
    temp_dir = f'nhentai_{gallery_id}'
    os.makedirs(temp_dir, exist_ok=True)
    try:
        test_url = f"https://nhentai.net/g/{gallery_id}/1/"
        async with aiohttp.ClientSession() as session:
            soup = await get_soup(session, test_url)
            end_page = int(soup.select_one('.num-pages').text)

            tasks = [
                download_page(session, f"https://nhentai.net/g/{gallery_id}/{page}/", page, temp_dir, gallery_id)
                for page in range(1, end_page + 1)
            ]
            downloaded_files = await asyncio.gather(*tasks)

        downloaded_files = sorted(f for f in downloaded_files if f is not None)
        pdf_path = f'nhentai_{gallery_id}.pdf'
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(downloaded_files))
        return pdf_path
    except Exception as e:
        print(f"Error utama: {str(e)}")
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Silakan masukkan ID galeri setelah perintah /download")
        return
    gallery_id = re.sub(r'\D', '', context.args[0])
    if not gallery_id:
        await update.message.reply_text("ID galeri tidak valid. Harap masukkan angka saja.")
        return

    await update.message.reply_text(f"⏳ Mendownload galeri {gallery_id}...")
    pdf_path = await download_nhentai_gallery(gallery_id)
    if pdf_path and os.path.exists(pdf_path):
        try:
            with open(pdf_path, 'rb') as f:
                await update.message.reply_document(
                    document=InputFile(f, filename=os.path.basename(pdf_path)),
                    caption=f"✅ Galeri {gallery_id} berhasil dikonversi!"
                )
        except Exception as e:
            await update.message.reply_text(f"Gagal mengirim file: {str(e)}")
        finally:
            os.remove(pdf_path)
    else:
        await update.message.reply_text("❌ Gagal membuat PDF. Pastikan ID galeri benar.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if re.match(r'^\d+$', text):
        context.args = [text]
        await handle_download(update, context)
    else:
        await update.message.reply_text("Kirim ID galeri (angka) atau gunakan /download <id>.")

async def main():
    keep_alive()  # Jalankan Flask server dan self-ping
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("download", handle_download))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    await app.run_polling()

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
