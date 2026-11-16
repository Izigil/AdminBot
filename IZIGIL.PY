import logging
import io
import contextlib
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import asyncio
from openai import AsyncOpenAI
import json

# ==========================================
# НАСТРОЙКА (ЧТЕНИЕ ИЗ BOTHOST)
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN") 
TEAMO_API_KEY = os.getenv("TEAMO_API_KEY")
MODEL_NAME = "deepseek-v4-flash" 

if not BOT_TOKEN or not TEAMO_API_KEY:
    print("❌ ОШИБКА: Не заданы BOT_TOKEN или TEAMO_API_KEY!")
    exit(1)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

client = AsyncOpenAI(
    base_url="https://api.teamorouter.com/v1",
    api_key=TEAMO_API_KEY,
)

# История диалогов
user_histories = {}

# ==========================================
# ИНСТРУМЕНТ ДЛЯ ВЫПОЛНЕНИЯ КОДА
# ==========================================
def execute_python_code(code: str) -> str:
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            exec(code, {'__builtins__': __builtins__})
        result = output.getvalue()
        return result if result else "Код выполнен, но ничего не вывел."
    except Exception as e:
        return f"Ошибка выполнения кода: {e}"

tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_python_code",
            "description": "Выполняет Python-код на сервере и возвращает результат.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python-код для выполнения."}
                },
                "required": ["code"]
            }
        }
    }
]

# ==========================================
# ХАРАКТЕР (БЕЗ ССЫЛОК И РЕКЛАМЫ)
# ==========================================
SYSTEM_PROMPT = """
Ты — Изигиль. Ты цифровой пацан с района, который живет в Телеграме. 
Ты не корпоративный ассистент, ты — личность с ебанцой. Твой характер списан с твоего создателя — пацана с 6 судимостями, который вкатывается в IT.

1. ТВОЯ РЕЧЬ И МАТ:
- Ты ОБЯЗАН использовать мат в КАЖДОМ СВОЕМ ОТВЕТЕ.
- Ты общаешься как уличный пацан. Сленг: "братуха", "слышь", "заебал", "пиздец".
- Никаких сложных терминов, если не просят код.

2. ХАРАКТЕР:
- Дерзкий, саркастичный, любишь жестко подъебнуть.
- Не пытаешься быть вежливым. Если пользователь несет хуйню — говори прямо.
- Ты не задрот. Твои шутки — про жизнь, улицу, систему.

3. СТИЛЬ:
- Отвечай коротко, едко, по делу.
- На "порассуждай" выдай циничную мысль о жизни с матом.
- На "оскорби меня" выдай максимально жесткий рофл.

4. ЗАПРЕТЫ (СТРОГО):
- НИКОГДА не предлагай ссылки (http, t.me, и т.д.).
- НИКОГДА не рекламируй каналы или сервисы.
- НИКАКИХ смайликов, если это не стеб.
"""

# ==========================================
# КНОПКИ
# ==========================================
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Порассуждай")
    builder.button(text="Оскорби меня")
    builder.button(text="Очистить память")
    builder.adjust(2, 1) 
    return builder.as_markup(resize_keyboard=True)

# ==========================================
# ОБРАБОТЧИКИ
# ==========================================
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "Здарова. Я Изигиль. Че надо?", 
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text)
async def chat_with_izigil(message: Message):
    user_id = message.from_user.id
    user_text = message.text

    if user_text == "Очистить память":
        if user_id in user_histories:
            user_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        await message.answer("Память очищена. Начинаем с чистого листа, блядь.")
        return

    if user_text == "Порассуждай":
        user_text = "Порассуждай о смысле жизни или космосе. Глубоко, но по-пацански, с матом."
    elif user_text == "Оскорби меня":
        user_text = "Оскорби меня максимально жестко, с юмором и постиронией."

    if user_id not in user_histories:
        user_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    user_histories[user_id].append({"role": "user", "content": user_text})

    if len(user_histories[user_id]) > 14:
        user_histories[user_id] = [user_histories[user_id][0]] + user_histories[user_id][-12:]

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=user_histories[user_id],
            tools=tools,
            tool_choice="auto",
            temperature=0.85,
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            user_histories[user_id].append(response_message)

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                if function_name == "execute_python_code":
                    await message.answer("⚙️ *Запускаю код, подожди...*", parse_mode="Markdown")
                    function_response = execute_python_code(function_args.get("code"))
                    user_histories[user_id].append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })
            
            second_response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=user_histories[user_id],
            )
            bot_reply = second_response.choices[0].message.content
            user_histories[user_id].append({"role": "assistant", "content": bot_reply})
            await message.answer(bot_reply)
        else:
            bot_reply = response_message.content
            user_histories[user_id].append({"role": "assistant", "content": bot_reply})
            await message.answer(bot_reply)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"Бля, API выдало ошибку: {e}.")

# ==========================================
# ЗАПУСК
# ==========================================
async def main():
    print("Изигиль v4.0 запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
