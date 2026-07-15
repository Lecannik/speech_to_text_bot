"""
Сервис транскрибации аудиозаписей (Speech-to-Text).
Использует библиотеку faster-whisper для локального распознавания речи на CPU/GPU.
"""

import logging
from typing import Optional
from faster_whisper import WhisperModel
from config import Config

logger = logging.getLogger(__name__)

class STTService:
    """Сервис для преобразования речи в текст с использованием модели Whisper."""
    
    _instance: Optional['STTService'] = None
    _model: Optional[WhisperModel] = None

    def __new__(cls, *args, **kwargs):
        """Реализация паттерна Singleton для предотвращения повторной загрузки модели в память."""
        if not cls._instance:
            cls._instance = super(STTService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        """Инициализация сервиса. Модель Whisper загружается отложенно при первом вызове."""
        pass

    def _get_model(self) -> WhisperModel:
        """
        Инициализирует и возвращает экземпляр WhisperModel.
        
        Загрузка происходит один раз. Параметры берутся из конфигурации.
        """
        if self._model is None:
            logger.info(
                f"Инициализация WhisperModel: размер={Config.WHISPER_MODEL_SIZE}, "
                f"устройство={Config.WHISPER_DEVICE}, тип вычислений={Config.WHISPER_COMPUTE_TYPE}"
            )
            try:
                # Инициализация модели быстрее-виспера
                self._model = WhisperModel(
                    model_size_or_path=Config.WHISPER_MODEL_SIZE,
                    device=Config.WHISPER_DEVICE,
                    compute_type=Config.WHISPER_COMPUTE_TYPE,
                    download_root=None # использует путь по умолчанию или HF_HOME
                )
                logger.info("Модель Whisper успешно загружена в память.")
            except Exception as e:
                logger.error(f"Не удалось загрузить модель Whisper: {e}", exc_info=True)
                raise e
        return self._model

    def transcribe(self, file_path: str) -> str:
        """
        Транскрибирует аудиофайл в текст.
        
        Аргументы:
            file_path (str): Абсолютный путь к аудиофайлу (например, ogg, wav, mp3).
            
        Возвращает:
            str: Распознанный текст.
        """
        logger.info(f"Начало транскрибации файла: {file_path}")
        try:
            model = self._get_model()
            
            # Запуск распознавания
            # beam_size=5 - стандартный баланс скорости и качества
            segments, info = model.transcribe(
                file_path,
                beam_size=5,
                vad_filter=True, # Фильтрация тишины и шумов для улучшения качества
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            logger.info(
                f"Распознан язык: {info.language} с вероятностью {info.language_probability:.2f}"
            )
            
            # Собираем текст из сегментов
            text_segments = []
            for segment in segments:
                text_segments.append(segment.text)
                
            full_text = " ".join(text_segments).strip()
            logger.info("Транскрибация успешно завершена.")
            return full_text
            
        except Exception as e:
            logger.error(f"Ошибка при транскрибации файла {file_path}: {e}", exc_info=True)
            return f"[Ошибка распознавания речи]: {str(e)}"
