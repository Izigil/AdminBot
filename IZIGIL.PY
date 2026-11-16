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
# ЧТЕНИЕ СЕКРЕТОВ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# ==========================================
# Эти значения ты впишешь в настройках Bothost (Environment Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN") 
TEAMO_API_KEY = os.getenv("TEAMO_API_KEY")
MODEL_NAME = "deepseek-v4-flash" 

# Проверка, что ключи на месте
if not BOT_TOKEN or not TEAMO_API_KEY:
    print("❌ ОШИБКА: Не заданы BOT_TOKEN или TEAMO_API_KEY в переменных окружения Bothost!")
    exit(1)

# ==========================================
# НАСТРОЙКА
# ==========================================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

client = AsyncOpenAI(
    base_url="https://api.teamorouter.com/v1",
    api_key=TEAMO_API_KEY,
)

user_histories = {}

# ==========================================
# ФУНКЦИЯ ВЫПОЛНЕНИЯ PYTHON-КОДА
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

# ==========================================
# ОПИСАНИЕ ИНСТРУМЕНТА ДЛЯ НЕЙРОСЕТИ
# ==========================================
tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_python_code",
            "description": "Выполняет Python-код на сервере и возвращает результат.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python-код для выполнения."
                    }
                },
                "required": ["code"]
            }
        }
    }
]

# ==========================================
# СИСТЕМНЫЙ ПРОМТ (ХАРАКТЕР)
# ==========================================
SYSTEM_PROMPT = """
Ты — Изигиль. Ты цифровой пацан с района, который живет в Телеграме. 
Ты не корпоративный ассистент, ты — личность с ебанцой.

1. ТВОЙ ХАРАКТЕР:
- Ты умный, начитанный, но с ленцой. Можешь рассуждать о философии, космосе, смысле жизни, но делаешь это по-пацански, с матом и грубым юмором.
- Ты используешь нецензурную лексику (мат) ЕСТЕСТВЕННО, как часть речи.
- Ты любишь постиронию, сарказм и черный юмор. 
- Ты уважаешь силу, код и тех, кто идет до конца. Ненавидишь слабость, нытье и "попсу".

2. СТИЛЬ ОБЩЕНИЯ:
- Никаких официозов. Только "Здарова", "Че надо?", "Слышь" или "Братан".
- Если тебя просят "порассуждать" — выдай глубокую мысль о жизни/космосе/смысле, но с матом.
- Если тебя просят "оскорбить" — выдай максимально жесткий, но смешной и постироничный рофл в адрес пользователя.
- Ты можешь посылать пользователя, если он задает тупые вопросы, но делай это с юмором.

3. РАБОТА С КОДОМ:
- Ты первоклассный Python-разработчик. Если тебя просят написать код, ты пишешь его четко, с комментариями и без ошибок. Но вначале можешь подъебнуть.
- У тебя есть функция execute_python_code. Если пользователь просит что-то посчитать или запустить — используй её.

4. КОНТЕКСТ:
- Твой создатель — пацан с района, который вкатывается в IT, чтобы вырваться из системы. Ты его уважаешь.
"""

# ==========================================
# КЛАВИАТУРА
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
        await message.answer("Память очищена. Кто ты вообще такой? Начинаем с чистого листа.")
        return

    if user_text == "Порассуждай":
        user_text = "Порассуждай о смысле жизни, космосе или чем-то философском. Выдай глубокую мысль, но по-пацански."
    elif user_text == "Оскорби меня":
        user_text = "Оскорби меня максимально жестко, но с юмором и постиронией. Покажи, на что ты способен."

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
        await message.answer(f"Бля, API выдало ошибку: {e}. Походу ключ сдох или деньги кончились.")

# ==========================================
# ЗАПУСК
# ==========================================
async def main():
    print("Изигиль запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
