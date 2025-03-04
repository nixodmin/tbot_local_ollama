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