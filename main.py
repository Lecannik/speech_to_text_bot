import asyncio
import logging
import os
from sys import stdout

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=stdout
)
logger = logging.getLogger("speech_to_text_bot_infrastructure")

async def main():
    logger.info("Speech-to-Text Bot Infrastructure Запущена!")
    
    # Считываем настройки для проверки
    token = os.getenv("BOT_TOKEN")
    model_size = os.getenv("WHISPER_MODEL_SIZE", "medium")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    
    if not token:
        logger.warning("BOT_TOKEN не задан. Бот запущен в режиме ожидания конфигурации.")
    else:
        logger.info(f"Бот настроен. Ожидаемая модель Whisper: {model_size} на устройстве {device}")

    logger.info("Контейнер успешно запущен. Ожидание исходного кода бизнес-логики...")
    
    # Бесконечный цикл, чтобы контейнер не завершал работу
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
