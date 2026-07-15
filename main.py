"""
Главный модуль запуска Telegram-бота.
Инициализирует бота, подключает обработчики и запускает асинхронный polling.
"""

import asyncio
import logging
from sys import stdout
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from config import Config
from handlers.voice_handlers import router as voice_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=stdout
)
logger = logging.getLogger("speech_to_text_bot")

# Создаем глобальный роутер для базовых команд
base_router = Router()

@base_router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start."""
    user_name = message.from_user.full_name or "пользователь"
    welcome_text = (
        f"👋 Привет, {user_name}!\n\n"
        f"Я бот для распознавания речи и создания кратких выжимок (Summary).\n\n"
        f"🎤 **Как это работает?**\n"
        f"1. Отправь мне голосовое сообщение или перешли аудиозапись.\n"
        f"2. Я расшифрую речь в текст локальной моделью Whisper.\n"
        f"3. Я пришлю тебе полный текст, а вторым сообщением — краткую выжимку (Summary) ключевых моментов.\n\n"
        f"Настройки Whisper: модель `{Config.WHISPER_MODEL_SIZE}` на `{Config.WHISPER_DEVICE}`.\n"
        f"Провайдер суммаризации: `{Config.API_PROVIDER}`."
    )
    await message.reply(welcome_text, parse_mode=ParseMode.MARKDOWN)

@base_router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help."""
    help_text = (
        "🤖 **Справка по использованию бота**\n\n"
        "Просто отправьте мне аудиофайл или запишите голосовое сообщение:\n"
        "- Поддерживаются форматы голосовых сообщений Telegram (OGG/Opus).\n"
        "- Поддерживаются обычные музыкальные файлы или записи диктофона (MP3, WAV, AAC, M4A и т.д.).\n\n"
        "Бот автоматически пришлет вам:\n"
        "1. Полную расшифровку аудио в виде текста.\n"
        "2. Краткий конспект с ключевыми мыслями (summary) от LLM."
    )
    await message.reply(help_text, parse_mode=ParseMode.MARKDOWN)

async def main():
    """Точка входа запуска бота."""
    logger.info("Запуск Telegram STT бота...")
    
    # Инициализация бота. Настройка parse_mode по умолчанию
    bot = Bot(token=Config.BOT_TOKEN)
    
    # Инициализация диспетчера
    dp = Dispatcher()
    
    # Подключаем роутеры (сначала базовые команды, затем обработка аудио)
    dp.include_router(base_router)
    dp.include_router(voice_router)
    
    # Запускаем polling, пропуская накопившиеся сообщения (drop_pending_updates)
    # для предотвращения лавины ответов на старые сообщения при перезапуске бота
    logger.info("Бот успешно запущен и слушает новые сообщения!")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Программа завершена.")
