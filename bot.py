import asyncio
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from yt_dlp import YoutubeDL

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "5"))
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)
TELEGRAM_FILE_LIMIT_BYTES = 49 * 1024 * 1024


@dataclass
class TrackInfo:
    title: str
    page_url: str
    duration_seconds: int | None = None


RESULTS_CACHE: Dict[int, List[TrackInfo]] = {}


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "?"
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02}:{sec:02}"
    return f"{minutes}:{sec:02}"


def search_soundcloud(query: str, limit: int) -> List[TrackInfo]:
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
    }
    with YoutubeDL(ydl_opts) as ydl:
        data = ydl.extract_info(f"scsearch{limit}:{query}", download=False)

    tracks: List[TrackInfo] = []
    for entry in (data or {}).get("entries", []):
        if not entry:
            continue
        url = entry.get("url") or entry.get("webpage_url")
        if not url:
            continue
        if not str(url).startswith("http"):
            url = f"https://soundcloud.com/{url}"
        tracks.append(
            TrackInfo(
                title=entry.get("title") or "Без названия",
                page_url=url,
                duration_seconds=entry.get("duration"),
            )
        )
    return tracks


def safe_filename(text: str) -> str:
    return re.sub(r"[^\w\-. ]", "_", text)[:80].strip() or "track"


def download_track(url: str, title_hint: str) -> Path:
    base_name = safe_filename(title_hint)
    output_template = str(DOWNLOAD_DIR / f"{base_name}.%(ext)s")
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = Path(ydl.prepare_filename(info))

    if not file_path.exists():
        candidates = list(DOWNLOAD_DIR.glob(f"{base_name}.*"))
        if not candidates:
            raise FileNotFoundError("Не удалось найти скачанный файл")
        file_path = max(candidates, key=lambda p: p.stat().st_mtime)
    return file_path


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я помогу найти и скачать музыку из SoundCloud.\n\n"
        "Использование:\n"
        "1) /search название трека\n"
        "2) Нажми кнопку «Скачать» под нужным результатом"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Укажи запрос: /search название трека")
        return

    query = " ".join(context.args).strip()
    await update.message.reply_text(f"Ищу в SoundCloud: {query}")

    try:
        tracks = await asyncio.to_thread(search_soundcloud, query, MAX_RESULTS)
    except Exception as exc:
        logger.exception("Ошибка поиска: %s", exc)
        await update.message.reply_text("Ошибка поиска. Попробуй позже.")
        return

    if not tracks:
        await update.message.reply_text("Ничего не найдено.")
        return

    RESULTS_CACHE[update.effective_chat.id] = tracks

    lines = ["Найдено:"]
    keyboard = []
    for idx, tr in enumerate(tracks, start=1):
        lines.append(f"{idx}. {tr.title} ({_format_duration(tr.duration_seconds)})")
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"⬇️ Скачать #{idx}", callback_data=f"dl:{idx - 1}"
                )
            ]
        )

    await update.message.reply_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    tracks = RESULTS_CACHE.get(chat_id)
    if not tracks:
        await query.message.reply_text("Сначала выполни поиск через /search")
        return

    try:
        idx = int(query.data.split(":", 1)[1])
        track = tracks[idx]
    except Exception:
        await query.message.reply_text("Некорректный выбор. Выполни поиск заново.")
        return

    await query.message.reply_text(f"Скачиваю: {track.title}")
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_AUDIO)

    try:
        file_path = await asyncio.to_thread(download_track, track.page_url, track.title)
        file_size = file_path.stat().st_size
        if file_size > TELEGRAM_FILE_LIMIT_BYTES:
            await query.message.reply_text(
                "Файл слишком большой для отправки ботом в Telegram (>49MB)."
            )
            return

        with file_path.open("rb") as audio_f:
            await query.message.reply_audio(
                audio=audio_f,
                title=track.title,
                caption=f"Источник: {track.page_url}",
            )
    except Exception as exc:
        logger.exception("Ошибка загрузки: %s", exc)
        await query.message.reply_text("Не удалось скачать трек. Попробуй другой.")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Неизвестная команда. Используй /search <запрос>")


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN в переменных окружения")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CallbackQueryHandler(download_callback, pattern=r"^dl:\d+$"))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
