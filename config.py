"""
Модуль конфигурации приложения.
Загружает переменные окружения из файла .env и предоставляет интерфейс доступа к ним.
"""

import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

class Config:
    """Класс для хранения и доступа к параметрам конфигурации бота."""
    
    # Токен Telegram бота для общения с пользователями
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Настройки локальной модели Whisper (STT)
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "medium")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    
    # Настройки локальной модели LLM (Ollama / Summary)
    # По умолчанию для Docker-окружения используем http://ollama:11434,
    # для локального тестирования вне Docker подставляется http://localhost:11434.
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://ollama:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    
    # Промпт для генерации краткого содержания
    SUMMARY_PROMPT: str = os.getenv(
        "SUMMARY_PROMPT",
        "Сделай подробную выжимку (summary) следующего текста на русском языке. "
        "Выдели ключевые мысли, задачи, договоренности и важные детали в виде списков."
    )

# Валидация критических настроек
if not Config.BOT_TOKEN:
    raise ValueError("Критическая ошибка: Переменная BOT_TOKEN должна быть задана в окружении или файле .env")
