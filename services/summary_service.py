"""
Сервис генерации краткого содержания (Summary) текста.
Отправляет запросы к локально запущенному серверу LLM (Ollama) с помощью httpx.
Поддерживает автоматический пулл (скачивание) модели, если она отсутствует на сервере.
"""

import logging
import httpx
from config import Config

logger = logging.getLogger(__name__)

class SummaryService:
    """Сервис для интеграции с локальным Ollama API для суммаризации текстов."""

    _model_verified: bool = False  # Флаг, чтобы не проверять наличие модели при каждом запросе

    def __init__(self) -> None:
        """Инициализация сервиса."""
        pass

    async def _ensure_model_loaded(self, client: httpx.AsyncClient) -> None:
        """
        Проверяет, скачана ли требуемая модель в Ollama.
        Если модель отсутствует, инициирует её автоматическое скачивание.
        """
        if self._model_verified:
            return

        tags_url = f"{Config.OLLAMA_HOST}/api/tags"
        pull_url = f"{Config.OLLAMA_HOST}/api/pull"
        target_model = Config.OLLAMA_MODEL

        try:
            # 1. Проверяем список установленных моделей
            logger.info(f"Проверка наличия модели '{target_model}' в Ollama через {tags_url}...")
            response = await client.get(tags_url)
            response.raise_for_status()
            data = response.json()

            local_models = [m['name'] for m in data.get('models', [])]
            # Ollama может хранить модель как "qwen2.5:3b" или "qwen2.5:3b-instruct" (или с хэшем/тегом :latest)
            # Делаем нестрогое сопоставление
            model_exists = any(target_model in name for name in local_models)

            if model_exists:
                logger.info(f"Модель '{target_model}' уже установлена в Ollama.")
                self._model_verified = True
                return

            # 2. Если модели нет, скачиваем ее
            logger.info(f"Модель '{target_model}' не найдена локально. Инициируем скачивание (pull)...")
            pull_payload = {
                "name": target_model,
                "stream": False
            }
            
            # Запрос может выполняться долго (скачивание 1.6-3 ГБ), ставим большой таймаут
            pull_response = await client.post(pull_url, json=pull_payload, timeout=600.0)
            pull_response.raise_for_status()
            
            logger.info(f"Модель '{target_model}' успешно скачана и готова к работе.")
            self._model_verified = True

        except Exception as e:
            logger.error(
                f"Ошибка при проверке/загрузке модели {target_model} в Ollama: {e}", 
                exc_info=True
            )
            # Не блокируем выполнение, пробуем продолжить (вдруг Ollama доступна, но /api/tags упал)

    async def generate_summary(self, text: str) -> str:
        """
        Генерирует краткое содержание (summary) для переданного текста с помощью локальной Ollama.
        
        Аргументы:
            text (str): Исходный текст для суммаризации.
            
        Возвращает:
            str: Сгенерированное краткое содержание или текст ошибки.
        """
        if not text.strip():
            return "Текст пуст. Нечего суммаризировать."
            
        logger.info(f"Запуск локальной суммаризации текста через Ollama (модель: {Config.OLLAMA_MODEL})")
        
        chat_url = f"{Config.OLLAMA_HOST}/api/chat"
        prompt = f"{Config.SUMMARY_PROMPT}\n\nТекст для обработки:\n{text}"
        
        payload = {
            "model": Config.OLLAMA_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.3  # Более консервативные/структурированные ответы
            }
        }
        
        try:
            # Используем увеличенный таймаут на выполнение генерации (на CPU-only LLM может отвечать медленно)
            async with httpx.AsyncClient(timeout=180.0) as client:
                # Проверяем и скачиваем модель при необходимости
                await self._ensure_model_loaded(client)
                
                logger.info("Отправка запроса на генерацию в Ollama...")
                response = await client.post(chat_url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                # Извлекаем ответ
                summary = data['message']['content']
                logger.info("Summary успешно сгенерировано локально.")
                return summary.strip()
                
        except Exception as e:
            logger.error(f"Ошибка при запросе к локальному API Ollama: {e}", exc_info=True)
            return (
                f"[Ошибка локальной генерации выжимки]: {str(e)}\n"
                f"Убедитесь, что сервис Ollama запущен и модель '{Config.OLLAMA_MODEL}' доступна."
            )
