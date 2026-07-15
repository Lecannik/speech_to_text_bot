# Speech to Text Telegram Bot (STT Bot)

Telegram-бот для автоматического преобразования голосовых сообщений в текст с использованием локальной модели Whisper (OpenAI) и генерацией краткого содержания (summary) вторым сообщением.

Проект спроектирован с учетом запуска в изолированной инфраструктуре (Proxmox QEMU VM в серой локальной сети `192.168.20.0/24`) и автоматического развертывания через CI/CD пайплайн.

---

## 🛠 Архитектура деплоя

Проект использует паттерн автоматического развертывания без хранения исходного кода на целевом сервере:

1. **Сборка образа** происходит в облачной среде GitHub Actions (`ubuntu-latest`).
2. Готовый образ пушится в **DockerHub** в публичный/приватный репозиторий `lecannik/speech-to-text-bot`.
3. Локальный **Self-Hosted GitHub Runner** (запущенный на выделенной инфраструктурной VM) слушает события репозитория.
4. При успешной сборке раннер копирует конфигурационные файлы (`docker-compose.prod.yml`) на целевую VM `192.168.20.29` по протоколу SSH.
5. Раннер инициирует команду обновления контейнеров (`docker compose pull && docker compose up -d`) внутри целевой VM.
6. Выполняется проверка статуса контейнера (healthcheck).
7. Отправляется уведомление в Telegram-чат о статусе деплоя.

---

## 🖥 Подготовка окружения на целевой VM (`192.168.20.29`)

Для развертывания бота необходимо выделить виртуальную машину (VM QEMU) в Proxmox:

### Системные требования
* **ОС**: Ubuntu 24.04 LTS Server (или аналогичная)
* **CPU**: 4 ядра (тип процессора в Proxmox выставить как `host`, чтобы пробросить инструкции AVX2, критичные для Whisper)
* **RAM**: 8 ГБ (модели `medium` требуется около 5 ГБ в пике вычислений)
* **Диск**: 40 ГБ SSD/NVMe (под ОС, образы Docker и кэшируемые Whisper-модели)

### Настройка VM
1. Установите **Docker Engine** и **Docker Compose** plugin:
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-buildx-plugin docker-compose-plugin
   sudo systemctl enable --now docker
   ```
2. Создайте системного пользователя `nik` и добавьте его в группу `docker`:
   ```bash
   sudo usermod -aG docker nik
   ```
3. Создайте рабочую директорию:
   ```bash
   sudo mkdir -p /opt/speech-to-text-bot
   sudo chown -R nik:nik /opt/speech-to-text-bot
   ```
4. Настройте файл переменных окружения `/opt/speech-to-text-bot/.env`. За основу возьмите шаблон из репозитория `.env.example`:
   ```bash
   cp .env.example /opt/speech-to-text-bot/.env
   nano /opt/speech-to-text-bot/.env
   ```
    *Обязательно укажите ваш `BOT_TOKEN` (токен основного рабочего бота).*

---

## 🏃 Настройка Self-Hosted Runner

Для доставки обновлений на VM раннеру требуется доступ по SSH. Раннер устанавливается на существующей VM, управляющей деплоем в вашей сети.

1. Зарегистрируйте новый раннер в репозитории на GitHub (**Settings -> Actions -> Runners -> New self-hosted runner**).
2. Выберите ОС Linux и следуйте инструкциям для загрузки пакета раннера в отдельную директорию на вашей инфраструктурной VM (например, `/home/nik/actions-runner-stt/`).
3. При конфигурации укажите:
   * URL репозитория: `https://github.com/Lecannik/speech-to-text-bot`
   * Имя раннера: `speech-to-text-bot-runner`
   * Метки (labels): `self-hosted,speech-to-text-bot`
4. Установите и запустите раннер как службу:
   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```
5. Убедитесь, что SSH-ключ пользователя, от лица которого запущен раннер, скопирован на целевую VM `192.168.20.29`:
   ```bash
   ssh-copy-id nik@192.168.20.29
   ```

---

## 🔐 GitHub Secrets

Для работы пайплайна добавьте следующие секреты в GitHub (рекомендуется настроить на уровне организации/аккаунта или непосредственно в репозитории):

* `DOCKERHUB_USERNAME` — ваш логин на DockerHub.
* `DOCKERHUB_TOKEN` — ваш Access Token (PAT) от DockerHub для авторизации при push/pull.
* `TELEGRAM_BOT_TOKEN` — токен **второго** служебного бота, который используется только для отслеживания деплоя и отправки логов сборки.
* `TELEGRAM_CHAT_ID` — ID чата, куда служебный бот будет слать отчеты деплоя.

---

## 🚀 Управление контейнерами (вручную на целевом сервере)

Если вам потребуется проверить логи или перезапустить контейнер вручную, подключитесь по SSH на `192.168.20.29`:

```bash
cd /opt/speech-to-text-bot

# Посмотреть статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Просмотр логов бота в реальном времени
docker compose -f docker-compose.prod.yml logs -f bot

# Ручной перезапуск
docker compose -f docker-compose.prod.yml restart bot
```

Модели Whisper сохраняются в именованном Docker Volume `models_data` и кэшируются между обновлениями образов контейнера.