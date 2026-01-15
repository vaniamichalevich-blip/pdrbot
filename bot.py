import json
import random
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InputFile,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8465937925:AAHsa7Ni6W9N6EHiviN3q4E45BZwNgTOWWY"

bot = Bot(TOKEN)
dp = Dispatcher()

# ------------------------------------
#   ЗАВАНТАЖЕННЯ БАЗИ
# ------------------------------------
with open("ready.json", "r", encoding="utf-8") as f:
    DB = json.load(f)

QUESTIONS = {q["id"]: q for q in DB}
MAX_Q_ID = max(QUESTIONS.keys())
TICKETS_COUNT = MAX_Q_ID // 20

USER_STATS = {}
EXAMS = {}

# ------------------------------------
#   ГОЛОВНЕ МЕНЮ
# ------------------------------------
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔀 Випадкове питання"),
            KeyboardButton(text="🧪 Іспит (20 питань)")
        ],
        [
            KeyboardButton(text="📊 Моя статистика"),
            KeyboardButton(text="🎫 Обрати білет")
        ]
    ],
    resize_keyboard=True
)

# ------------------------------------
#   СТАРТ
# ------------------------------------
@dp.message(F.text == "/start")
async def cmd_start(msg: Message):
    await msg.answer(
        "Привіт! Я бот для підготовки до ПДР 🚗\n\n"
        "Можеш:\n"
        "• Натиснути кнопки внизу\n"
        "• Ввести номер білета — отримаєш весь білет\n"
        "• Ввести ID питання — отримаєш одне питання\n"
        "• Написати будь-яке слово/фразу — пошук по питаннях\n",
        reply_markup=main_kb
    )

# ------------------------------------
#   ВИВЕДЕННЯ ПИТАННЯ БЕЗ ВАРІАНТІВ (ПОШУК)
# ------------------------------------
async def send_plain_question(msg: Message, qid: int):
    q = QUESTIONS[qid]

    text = f"❓ *{qid}. {q['question']}*\n\n"

    correct_id = q["correct"]
    correct_text = q["options"][correct_id - 1]

    text += f"✔ *Правильна відповідь:* {correct_text}\n"

    explanation = q.get("explanation") or q.get("explanation_text")
    if explanation:
        text += f"\nℹ *Пояснення:*\n{explanation}"

    img = q.get("image")
    if img:
        try:
            await msg.answer_photo(InputFile(img), caption=text, parse_mode="Markdown")
            return
        except:
            pass

    await msg.answer(text, parse_mode="Markdown")


# ------------------------------------
#   ВИВЕДЕННЯ ПИТАННЯ З ВАРІАНТАМИ (ІСПИТ)
# ------------------------------------
async def send_question_exam(msg: Message, qid: int):
    q = QUESTIONS[qid]

    kb = InlineKeyboardBuilder()
    for i, opt in enumerate(q["options"], start=1):
        kb.button(text=str(i), callback_data=f"ans:{qid}:{i}")
    kb.adjust(2)

    img = q.get("image")
    caption = f"❓ *{qid}. {q['question']}*"

    if img:
        try:
            await msg.answer_photo(InputFile(img), caption=caption, reply_markup=kb.as_markup(), parse_mode="Markdown")
            return
        except:
            pass

    await msg.answer(caption, reply_markup=kb.as_markup(), parse_mode="Markdown")

# ------------------------------------
#   ВИПАДКОВЕ ПИТАННЯ (НЕ ІСПИТ)
# ------------------------------------
@dp.message(F.text == "🔀 Випадкове питання")
async def btn_random(msg: Message):
    qid = random.choice(list(QUESTIONS.keys()))
    await send_plain_question(msg, qid)

# ------------------------------------
#   ІСПИТ
# ------------------------------------
@dp.message(F.text == "🧪 Іспит (20 питань)")
@dp.message(F.text == "/exam")
async def cmd_exam(msg: Message):
    user = msg.from_user.id

    selected = random.sample(list(QUESTIONS.keys()), 20)

    EXAMS[user] = {
        "questions": selected,
        "current": 0,
        "correct": 0,
        "wrong": 0,
        "wrong_list": [],
        "end_time": datetime.now() + timedelta(minutes=20)
    }

    await msg.answer("📝 Іспит розпочато!\nУ тебе є 20 хвилин.")
    await send_question_exam(msg, selected[0])

@dp.callback_query(F.data.startswith("ans:"))
async def cb_answer(cb: CallbackQuery):
    _, qid_s, selected_s = cb.data.split(":")
    qid = int(qid_s)
    chosen = int(selected_s)
    user = cb.from_user.id

    exam = EXAMS[user]
    correct = QUESTIONS[qid]["correct"]

    if chosen == correct:
        exam["correct"] += 1
        await cb.message.answer("✅ Правильно!")
    else:
        exam["wrong"] += 1
        exam["wrong_list"].append(qid)
        await cb.message.answer(f"❌ Неправильно! Правильна: {correct}")

    exam["current"] += 1

    if exam["current"] >= 20 or datetime.now() >= exam["end_time"]:
        result = (
            f"🏁 *Іспит завершено!*\n\n"
            f"✔ Правильних: {exam['correct']}\n"
            f"❌ Помилок: {exam['wrong']}\n\n"
        )

        if exam["wrong_list"]:
            result += "🔻 *Питання з помилками:*\n"
            for qid in exam["wrong_list"]:
                result += f"• {qid}. {QUESTIONS[qid]['question']}\n"

        del EXAMS[user]

        await cb.message.answer(result, parse_mode="Markdown")
        await cb.answer()
        return

    next_qid = exam["questions"][exam["current"]]
    await send_question_exam(cb.message, next_qid)
    await cb.answer()

# ------------------------------------
#   СТАТИСТИКА
# ------------------------------------
@dp.message(F.text == "📊 Моя статистика")
async def btn_stats(msg: Message):
    user = msg.from_user.id
    s = USER_STATS.get(user)

    if not s:
        return await msg.answer("Ти ще не відповів на жодне питання.")

    await msg.answer(
        f"📊 *Твоя статистика:*\n"
        f"✔ Правильних: {s['correct']}\n"
        f"❌ Неправильних: {s['wrong']}",
        parse_mode="Markdown"
    )

# ------------------------------------
#   БІЛЕТИ
# ------------------------------------
@dp.message(F.text == "🎫 Обрати білет")
async def btn_ticket(msg: Message):
    await msg.answer(f"Введи номер білета від 1 до {TICKETS_COUNT}.")

@dp.message(F.text.regexp(r"^\d+$"))
async def handle_number(msg: Message):
    n = int(msg.text)

    if 1 <= n <= TICKETS_COUNT:
        await send_ticket(msg, n)
        return

    if n in QUESTIONS:
        await send_plain_question(msg, n)
        return

    await msg.answer("❌ Невірний номер.")

async def send_ticket(msg: Message, ticket_num: int):
    start = (ticket_num - 1) * 20 + 1
    end = start + 19

    await msg.answer(f"📘 *Білет {ticket_num}*\n", parse_mode="Markdown")

    for qid in range(start, end + 1):
        if qid not in QUESTIONS:
            continue
        await send_plain_question(msg, qid)

# ------------------------------------
#   ПОШУК
# ------------------------------------
@dp.message(~F.text.startswith("/") & ~F.text.regexp(r"^\d+$"))
async def search(msg: Message):
    text = msg.text.lower().strip()
    words = [w for w in text.split() if len(w) > 2]

    results = []
    for qid, q in QUESTIONS.items():
        if all(w in q["question"].lower() for w in words):
            results.append(qid)
        if len(results) >= 40:
            break

    if not results:
        return await msg.answer("Нічого не знайдено 😢")

    kb = InlineKeyboardBuilder()
    for qid in results:
        txt = QUESTIONS[qid]["question"]
        short = txt[:60] + "…" if len(txt) > 60 else txt
        kb.button(text=f"{qid}: {short}", callback_data=f"openq:{qid}")
    kb.adjust(1)

    await msg.answer(f"🔍 Знайдено {len(results)} питань:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("openq:"))
async def cb_openq(cb: CallbackQuery):
    qid = int(cb.data.split(":")[1])
    await send_plain_question(cb.message, qid)
    await cb.answer()

# ------------------------------------
#   RUN
# ------------------------------------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
