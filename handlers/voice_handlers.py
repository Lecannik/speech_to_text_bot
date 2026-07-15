"""
Обработчики входящих аудио- и голосовых сообщений.
Принимает файлы, загружает их локально, распознает речь и делает краткое содержание.
"""

import os
import tempfile
import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message
from services.stt_service import STTService
from services.summary_service import SummaryService

logger = logging.getLogger(__name__)
router = Router()

# Инициализация сервисов
stt_service = STTService()
summary_service = SummaryService()

# Ограничиваем обработку аудио до 1 задачи одновременно для стабильности CPU и RAM
stt_semaphore = asyncio.Semaphore(1)

def split_message_text(text: str, limit: int = 4000) -> list[str]:
    """
    Разбивает длинный текст на части, не превышающие лимит Telegram на длину сообщения.
    
    Разбиение происходит по пробелам или границам слов для сохранения читаемости.
    """
    if len(text) <= limit:
        return [text]
        
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
            
        # Ищем последний пробел в пределах лимита
        split_pos = text.rfind(' ', 0, limit)
        if split_pos == -1:
            split_pos = limit
            
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()
        
    return parts

async def process_audio_message(message: Message, bot: Bot, file_id: str, file_name_hint: str):
    """
    Общая логика обработки аудиофайла (скачивание, STT, Summary, отправка ответов).
    Регулируется семафором для последовательной обработки.
    """
    # Проверяем, свободен ли "турникет" обработки
    is_queued = stt_semaphore.locked()
    if is_queued:
        status_message = await message.answer("⏳ Бот занят обработкой другого запроса. Ваша запись добавлена в очередь...")
    else:
        status_message = await message.answer("📥 Скачиваю аудиофайл...")
        
    # Создаем временный файл
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, f"{file_id}_{file_name_hint}")
    
    try:
        # Входим в очередь выполнения
        async with stt_semaphore:
            if is_queued:
                # Если стояли в очереди, информируем о начале работы
                await status_message.edit_text("📥 Очередь подошла! Скачиваю аудиофайл...")
                
            # Скачиваем файл из Telegram
            file_info = await bot.get_file(file_id)
            await bot.download_file(file_info.file_path, destination=temp_file_path)
            
            # Обновляем статус
            await status_message.edit_text("⚡️ Распознаю речь (это может занять некоторое время)...")
            
            # Запускаем STT (Whisper) в асинхронном пуле потоков
            loop = asyncio.get_running_loop()
            recognized_text = await loop.run_in_executor(None, stt_service.transcribe, temp_file_path)
            
            if not recognized_text:
                await status_message.edit_text("ℹ️ Аудиозапись пуста или в ней не обнаружена речь.")
                return

            # Удаляем сообщение со статусом и отправляем распознанный текст
            await status_message.delete()
            
            # Отправляем полный текст (разбиваем если он больше 4000 символов)
            text_parts = split_message_text(recognized_text)
            for i, part in enumerate(text_parts):
                prefix = ""
                if len(text_parts) > 1:
                    prefix = f"📝 **Часть {i+1} из {len(text_parts)}**:\n\n"
                await message.reply(f"{prefix}{part}", parse_mode="Markdown")

            # Отправляем новое сообщение со статусом для генерации Summary
            summary_status = await message.answer("✍️ Генерирую краткое содержание (summary)...")
            
            # Запускаем Summary (локальная Ollama)
            summary = await summary_service.generate_summary(recognized_text)
            
            await summary_status.delete()
            
            # Отправляем краткую выжимку
            await message.reply(
                f"📋 **Краткое содержание (Summary)**:\n\n{summary}",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Ошибка в процессе обработки аудио: {e}", exc_info=True)
        # На случай если мы упали до удаления status_message
        try:
            await status_message.edit_text(f"❌ Произошла ошибка при обработке аудио: {str(e)}")
        except Exception:
            await message.answer(f"❌ Произошла ошибка при обработке аудио: {str(e)}")
        
    finally:
        # Всегда удаляем временный файл
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Временный файл удален: {temp_file_path}")
            except Exception as ex:
                logger.error(f"Не удалось удалить временный файл {temp_file_path}: {ex}")

# Обработка голосовых сообщений (Voice)
@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot):
    """Обработчик голосовых сообщений."""
    logger.info(f"Получено голосовое сообщение от пользователя {message.from_user.id}")
    await process_audio_message(
        message=message,
        bot=bot,
        file_id=message.voice.file_id,
        file_name_hint="voice.ogg"
    )

# Обработка пересланных аудиофайлов (Audio)
@router.message(F.audio)
async def handle_audio(message: Message, bot: Bot):
    """Обработчик аудиофайлов (песни, файлы записей и т.д.)."""
    logger.info(f"Получен аудиофайл от пользователя {message.from_user.id}")
    # Вытаскиваем имя файла или ставим заглушку
    file_name = message.audio.file_name or "audio.mp3"
    await process_audio_message(
        message=message,
        bot=bot,
        file_id=message.audio.file_id,
        file_name_hint=file_name
    )
