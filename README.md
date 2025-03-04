Пример кода на Python для подключения к Телеграм боту нейросетевой модели подключенной через фреймворк для запуска и управления большими языковыми моделями (LLM) - ollama (https://ollama.com)

В качестве хоста использован мини-ПК с характеристиками:

AMD Ryzen 7 2700U (4с/8t)

RAM DDR4 16 ГБ (8x2) из которых доступно 14 (2 под видеопамять)

SSD NVME 256 ГБ

Операционная система Ubuntu Server 20.04

1. Создайте в Telegram бота через BotFather и получите Токен вашего бота.

2. Установите фреймворк ollama

```
sudo curl -fsSL https://ollama.com/install.sh | sh
```
и запустите фреймворк

```
sudo systemctl daemon-reload

sudo systemctl enable ollama

sudo systemctl start ollama
```
Теперь фреймворк ollama работает по адресу: http://127.0.0.1:11434

3. Зайдите на другом ПК на сайт https://ollama.com/library и выберите модель подходящую под ваше "железо"

Я выбрал https://ollama.com/library/deepseek-r1:14b

Чтобы загрузить модель на сервер, я использовал команду

```
ollama run deepseek-r1:14b
```
Начнётся загрузка модели на сервер (в моём случае это было 9Гб)
После окончания загрузки будет запущена строка диалога с нейросетевой моделью, можете задать вопрос, можете сразу выйти.
Команда для выхода:
```
>>> /bye
```

4. Готовим окружение python для скрипта связывающего Telegram бота и ollama.

Для примера в качестве пользователя испольую user, обязательно замените на свой вариант

В каталоге /home/user должен лежать файл tbot_local_ollama.py (содержимое скрипта в самом конце инструкции и файлах данного гита)

Создаём из-под вашего пользователя виртуальное окружение для питона:

```
sudo apt install python3.12-venv

python3 -m venv my-venv
```

Устанавливаем требуемые библиотеки в виртуальное окружение
```
my-venv/bin/pip install python-telegram-bot
 
my-venv/bin/pip install requests
```

Прежде чем сделать из скрипта сервис и добавить в автозагрузку проверьте, что всё работает без ошибок, запустите скрипт в консоли и обменяйтесь сообщениями с вашим ботом в Telegram.

Ключевые слова (в скрипте можно заменить KEYWORDS = ["нейронка", "нейросеть"] ) - это слова на которые будет реагировать нейросеть, чтобы вам ответить.

```
my-venv/bin/python3 tbot_local_ollama.py
```
Если всё работает (учтите, что скорость ответа нейросети напрямую зависит от вашего "железа", на мини-ПК, указанной в начале этого текста конфигурации, ответ нейросети занимает примерно секунд 10), то сделайте из скрипта сервис:
```
sudo nano /etc/systemd/system/tbot_local_ollama.service
```
Содержимое файла tbot_local_ollama.service (не забудьте заменить user на вашего пользователя):
```
[Unit]
Description=Tbot Python Script Service
After=network.target

[Service]
ExecStart=/home/user/my-venv/bin/python3 /home/user/tbot_local_ollama.py
WorkingDirectory=/home/user
Restart=always
User=user
Group=user

[Install]
WantedBy=multi-user.target
```
После создания файла tbot_local_ollama.service нужно обновить systemd
```
sudo systemctl daemon-reload
```
Запускаем сервис с помощью команды
```
sudo systemctl start tbot_local_ollama.service
```
Смотрим, что он запустился и работает
```
sudo systemctl status tbot_local_ollama.service
```
Чтобы включить его в автоматический запуск после перезагрузки системы
```
sudo systemctl enable tbot_local_ollama.service
```
Перезапуск сервиса
```
sudo systemctl restart tbot_local_ollama.service
```
Остановка сервиса
```
sudo systemctl stop tbot_local_ollama.service
```

Сам скрипт tbot_local_ollama.py

```
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import json
import logging
import re

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Токен Telegram-бота
TOKEN = 'ТОКЕН_ВАШЕГО_БОТА'

# URL для работы с Ollama (локальный сервер)
OLLAMA_URL = "http://127.0.0.1:11434"

# Модель Ollama, которую вы хотите использовать
MODEL = "deepseek-r1:14b"

# Ключевые слова для активации нейросети
KEYWORDS = ["нейронка", "нейросеть"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Скрипт чат-бота активен.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    user_input = update.message.text.lower()

    # Проверяем, содержит ли сообщение ключевые слова
    if not any(keyword in user_input for keyword in KEYWORDS):
        return  # Если ключевых слов нет, выходим из функции без отправки запроса к Ollama


    # System prompt
    system_prompt = "Use russian language, be friendly, be short."

    # Объединяем system prompt и пользовательский ввод
    full_prompt = f"{system_prompt}\n\n{user_input}"

    # Подготовка данных для запроса к Ollama
    api_data = {
        "model": MODEL,
        "keep_alive": -1,
        "prompt": full_prompt,
        "max_tokens": 500,
        "temperature": 0.7
    }

    try:
        # Отправляем запрос к Ollama с поддержкой стриминга
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=api_data, stream=True, timeout=20)

        response.raise_for_status()  # Проверяем статус ответа

        full_response = ""
        for line in response.iter_lines(decode_unicode=True):
            if line:  # Проверяем, что строка не пустая
                try:
                    # Каждая строка — это JSON
                    json_line = json.loads(line.strip())
                    if "response" in json_line:
                        full_response += json_line["response"]
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка при декодировании JSON: {e}")

        clean_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL)
        clean_response = clean_response.strip()
        full_response = clean_response

        if full_response.strip():
            logger.info(f"Assistant Response: {full_response}")
            await update.message.reply_text(full_response)
        else:
            logger.warning("Модель вернула пустой ответ.")
            await update.message.reply_text("Модель не смогла сформировать ответ.")

    except requests.exceptions.Timeout:
        logger.error("Ollama не отвечает более 20 секунд.")
        await update.message.reply_text("Извините, модель временно недоступна. Попробуйте позже.")

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при обращении к Ollama: {e}")
        await update.message.reply_text("Произошла ошибка при работе с моделью. Пожалуйста, попробуйте позже.")

def main() -> None:
    # Создаем экземпляр ApplicationBuilder и передаем ему токен вашего бота
    application = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("status", start))

    # Регистрируем обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
```
