import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ==== НАСТРОЙКИ ====
API_TOKEN = "8089562672:AAF4U5MjqcqXCG1nZPHPRGeITI4jLNSkQdc"
OWNER_ID = 8306180778  # твой ID
TARGET_CHAT_IDS = [
    "@veref_chat13",
    "@vhatsuper23",
    "@chats12uapiar2"
]

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# ==== СОСТОЯНИЯ ====
class PostStates(StatesGroup):
    choosing_type = State()
    waiting_for_media_or_text = State()
    waiting_for_buttons = State()
    waiting_for_forward = State()
    waiting_for_interval = State()

# ==== ПЕРЕМЕННЫЕ ====
tasks = []
job_task = None

# ==== КНОПКИ ====
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить пост")],
        [KeyboardButton(text="📋 Список постов")],
        [KeyboardButton(text="⛔️ Остановить рассылку")]
    ],
    resize_keyboard=True
)

posting_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ ГОТОВО")],
        [KeyboardButton(text="⏪ Отмена")]
    ],
    resize_keyboard=True
)

choose_type_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📝 Пост", callback_data="type_post")],
        [InlineKeyboardButton(text="🔁 Пересылка", callback_data="type_forward")],
        [InlineKeyboardButton(text="⏪ Отмена", callback_data="cancel_add")]
    ]
)

# ==== ПРОВЕРКА ВЛАДЕЛЬЦА ====
def is_owner(message: Message) -> bool:
    return message.from_user.id == OWNER_ID

def is_owner_id(user_id: int) -> bool:
    return user_id == OWNER_ID

# ==== START ====
@dp.message(CommandStart())
async def start(message: Message):
    if not is_owner(message):
        return await message.answer("⛔️ У вас нет доступа. Напишите админу.")
    await message.answer("Привет 👑 Выберите действие ⬇️", reply_markup=main_menu)

# ==== ДОБАВИТЬ ПОСТ ====
@dp.message(F.text == "➕ Добавить пост")
async def add_post(message: Message, state: FSMContext):
    if not is_owner(message):
        return
    await state.set_state(PostStates.choosing_type)
    await message.answer(
        "Выберите, что хотите добавить:",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        "Тип рассылки:",
        reply_markup=choose_type_kb
    )

# ==== ВЫБОР ТИПА ЧЕРЕЗ КНОПКИ ====
@dp.callback_query(F.data.in_({"type_post", "type_forward", "cancel_add"}))
async def choose_type_cb(callback: CallbackQuery, state: FSMContext):
    if not is_owner_id(callback.from_user.id):
        return await callback.answer("⛔️ Нет доступа", show_alert=True)

    if callback.data == "cancel_add":
        await state.clear()
        await callback.message.edit_text("❌ Отменено.")
        await callback.message.answer("Возврат в меню.", reply_markup=main_menu)
        return

    if callback.data == "type_post":
        await state.set_state(PostStates.waiting_for_media_or_text)
        try:
            await callback.message.edit_text("Отправь пост (текст, фото, видео, документ).")
        except Exception:
            # если сообщение нельзя отредактировать, просто отправим новое
            await callback.message.answer("Отправь пост (текст, фото, видео, документ).")
        await callback.message.answer("Когда закончишь — жми «ГОТОВО».", reply_markup=posting_menu)
        await callback.answer()
        return

    if callback.data == "type_forward":
        await state.set_state(PostStates.waiting_for_forward)
        try:
            await callback.message.edit_text("Перешли сообщение для рассылки.")
        except Exception:
            await callback.message.answer("Перешли сообщение для рассылки.")
        await callback.message.answer("Когда закончишь — жми «ГОТОВО».", reply_markup=posting_menu)
        await callback.answer()
        return

# ==== ПОЛУЧЕНИЕ ПОСТА ====
@dp.message(PostStates.waiting_for_media_or_text)
async def receive_post(message: Message, state: FSMContext):
    if message.text == "⏪ Отмена":
        await message.answer("❌ Отменено.", reply_markup=main_menu)
        return await state.clear()

    if message.text == "✅ ГОТОВО":
        return await message.answer("❗️ Сначала отправь сообщение.")

    if message.photo:
        content = {"type": "photo", "file_id": message.photo[-1].file_id, "caption": message.caption, "buttons": []}
    elif message.video:
        content = {"type": "video", "file_id": message.video.file_id, "caption": message.caption, "buttons": []}
    elif message.document:
        content = {"type": "document", "file_id": message.document.file_id, "caption": message.caption, "buttons": []}
    elif message.text:
        content = {"type": "text", "text": message.text, "buttons": []}
    else:
        return await message.answer("❗️ Неподдерживаемый тип.")

    await state.update_data(current_post=content)
    await message.answer(
        "Хотите добавить кнопки?\nФормат: <b>Название - ссылка</b>\nИли нажмите «ГОТОВО».",
        reply_markup=posting_menu
    )
    await state.set_state(PostStates.waiting_for_buttons)

# ==== ДОБАВЛЕНИЕ КНОПОК ====
@dp.message(PostStates.waiting_for_buttons)
async def add_buttons(message: Message, state: FSMContext):
    data = await state.get_data()
    current_post = data.get("current_post")

    if message.text == "✅ ГОТОВО":
        await message.answer("Укажи интервал (в секундах).", reply_markup=ReplyKeyboardRemove())
        await state.set_state(PostStates.waiting_for_interval)
        return

    if message.text == "⏪ Отмена":
        await message.answer("❌ Отменено.", reply_markup=main_menu)
        return await state.clear()

    try:
        name, url = message.text.split(" - ", 1)
        if url.startswith("@"):
            url = f"https://t.me/{url[1:]}"
        current_post["buttons"].append({"text": name.strip(), "url": url.strip()})
        await state.update_data(current_post=current_post)
        await message.answer(f"✅ Кнопка <b>{name.strip()}</b> добавлена.")
    except ValueError:
        await message.answer("❗️ Формат: Название - ссылка")

# ==== ПОЛУЧЕНИЕ ПЕРЕСЫЛКИ ====
@dp.message(PostStates.waiting_for_forward)
async def receive_forward(message: Message, state: FSMContext):
    if message.text == "⏪ Отмена":
        await message.answer("❌ Отменено.", reply_markup=main_menu)
        return await state.clear()

    if not message.forward_from_chat and not message.forward_from:
        return await message.answer("❗️ Перешлите настоящее сообщение.")

    content = {
        "type": "forward",
        "chat_id": message.chat.id,
        "message_id": message.message_id,
        "buttons": []  # чтобы не было ошибок
    }
    await state.update_data(current_post=content)
    await message.answer("Укажи интервал (в секундах).", reply_markup=ReplyKeyboardRemove())
    await state.set_state(PostStates.waiting_for_interval)

# ==== ИНТЕРВАЛ ====
@dp.message(PostStates.waiting_for_interval)
async def set_interval(message: Message, state: FSMContext):
    global job_task
    try:
        interval = int(message.text)
        if interval < 5:
            return await message.answer("❗️ Минимум 5 секунд.")
    except ValueError:
        return await message.answer("❗️ Нужно число.")

    data = await state.get_data()
    current_post = data.get("current_post")

    tasks.append({
        "contents": [current_post],
        "interval": interval,
        "last_sent": 0
    })

    await message.answer("✅ Пост добавлен в список!", reply_markup=main_menu)
    await state.clear()

    if not job_task:
        job_task = asyncio.create_task(post_loop())

# ==== СПИСОК ПОСТОВ ====
@dp.message(F.text == "📋 Список постов")
async def list_posts(message: Message):
    if not tasks:
        return await message.answer("📭 Список пуст.")

    text = "📋 <b>Список постов:</b>\n\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for i, task in enumerate(tasks, start=1):
        c = task["contents"][0]
        t = c["type"]
        interval = task["interval"]
        text += f"{i}. Тип: {t}, интервал: {interval} сек\n"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ Удалить {i}", callback_data=f"del_{i-1}")])

    await message.answer(text, reply_markup=kb)

# ==== УДАЛЕНИЕ ПОСТА ====
@dp.callback_query(F.data.startswith("del_"))
async def delete_post(callback: CallbackQuery):
    index = int(callback.data.split("_")[1])
    if 0 <= index < len(tasks):
        tasks.pop(index)
        await callback.answer("✅ Пост удалён")
        await callback.message.delete()
    else:
        await callback.answer("❗️ Ошибка индекса", show_alert=True)

# ==== СТОП ====
@dp.message(F.text == "⛔️ Остановить рассылку")
async def stop_all(message: Message):
    global job_task, tasks
    if job_task:
        job_task.cancel()
        job_task = None
        tasks.clear()
        await message.answer("⛔️ Все рассылки остановлены.", reply_markup=main_menu)
    else:
        await message.answer("❗️ Рассылка не запущена.")

# ==== ЦИКЛ РАССЫЛКИ ====
async def post_loop():
    global tasks
    while True:
        now = asyncio.get_event_loop().time()
        for task in tasks:
            if now - task["last_sent"] >= task["interval"]:
                for content in task["contents"]:
                    kb = None
                    if content.get("buttons"):
                        # каждая кнопка на своей строке
                        kb = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [InlineKeyboardButton(text=btn["text"], url=btn["url"])]
                                for btn in content["buttons"]
                            ]
                        )

                    for chat_id in TARGET_CHAT_IDS:
                        try:
                            if content["type"] == "text":
                                await bot.send_message(chat_id, content["text"], reply_markup=kb)
                            elif content["type"] == "photo":
                                await bot.send_photo(chat_id, content["file_id"], caption=content.get("caption"), reply_markup=kb)
                            elif content["type"] == "video":
                                await bot.send_video(chat_id, content["file_id"], caption=content.get("caption"), reply_markup=kb)
                            elif content["type"] == "document":
                                await bot.send_document(chat_id, content["file_id"], caption=content.get("caption"), reply_markup=kb)
                            elif content["type"] == "forward":
                                await bot.forward_message(chat_id, content["chat_id"], content["message_id"])
                        except Exception as e:
                            print(f"[Ошибка отправки] {e}")
                task["last_sent"] = now
        await asyncio.sleep(1)

# ==== ЗАПУСК ====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dp.run_polling(bot)
