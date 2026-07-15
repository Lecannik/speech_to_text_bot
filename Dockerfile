# Базовый образ с Python 3.11
FROM python:3.11-slim AS builder

WORKDIR /app

# Установка системных утилит, необходимых для сборки зависимостей (если понадобятся)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения для изоляции зависимостей
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Финальный легковесный образ
FROM python:3.11-slim AS runner

WORKDIR /app

# Установка ffmpeg (критически важен для Whisper для декодирования аудио)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Копирование виртуального окружения из builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Установка переменных окружения для Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Копирование исходного кода приложения
COPY . .

# Команда запуска бота по умолчанию
CMD ["python", "main.py"]
