import logging
import os
import json
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Завантаження змінних середовища
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Не вдалося знайти токен бота. Перевірте змінні середовища.")

RENDER_APP_URL = os.getenv('RENDER_APP_URL', 'https://your-app-url.onrender.com')
USER_DATA_FILE = 'user_data.json'
TEST_MODE = False

# Контент уроків
LESSONS = {
    1: {
        'intro_message': "Вітаю вас на першому дні інтенсиву! 🎊\n\nСьогодні ви отримали перший урок — *подкаст із психологом* про маніпуляції в бʼюті-сфері.\nМи поговоримо чесно:\n– Чому маніпуляції — це не \"дрібниці\", а серйозне порушення кордонів\n– Як їх розпізнати в роботі з керівництвом, колегами та клієнтами\n– Та найголовніше — як навчитись себе захищати",
        'videos': [
            {'file_id': 'BAACAgIAAyEFAASaGaDWAAMeaCNM2Q1tPOzDskUXmsxCs9PhHjgAAnd1AAK5ARhJo4zf7IIDr282BA', 'caption': ''}
        ],
        'completion_message': 'Завтра на вас чекатиме другий урок — подкаст з адвокаткою про ФОПи, права майстра та орендні договори.✔️'
    },
    2: {
        'intro_message': "Вітаю!🙌\n\nСьогодні ви отримали другий урок — подкаст із адвокаткою, де ми говоримо про те, що мусить знати кожен майстер:\n– Як правильно оформити ФОП та яку групу обрати\n– Як захистити свої права, працюючи в салоні або на себе\n– На що звертати увагу в орендних договорах: суборенда, частина приміщення, поділ комуналки\n\nМи розклали юридичні нюанси простою мовою — без \"страшних\" термінів, тільки реальні ситуації з практики.",
        'videos': [
            {'file_id': 'BAACAgIAAyEFAASaGaDWAAMaaB4EscQSmB4_JHtsqGc4gMcDXAoAAiRsAAJ_NfBIZVlHygKFZXE2BA', 'caption': ''}
        ],
        'post_videos_message': '🎁🎁🎁 🎁🎁🎁🎁🎁🎁🎁🎁🎁\nЦі документи допоможуть вам не "попасти" на словах і зафіксувати всі умови співпраці офіційно.📜\n**Завантажуйте, адаптуйте під себе і працюйте впевнено!**',
        'documents': [
            {'file_id': 'BQACAgIAAyEFAASaGaDWAAMXaB4DMIL06ORGZhLDAdG8iirzJIYAAqNvAAJ2AAHwSDEtYlx3aq2pNgQ', 'caption': 'Документ 1'},
            {'file_id': 'BQACAgIAAyEFAASaGaDWAAMYaB4DUx0MvIeVKKJxghbli2zQVCYAAqVvAAJ2AAHwSDX-cXcbud4QNgQ', 'caption': 'Документ 2'}
        ],
        'completion_message': 'Завтра ви отримаєте завершальний третій урок — щиру історію успіху від нейлблогерки, яка колись починала з нуля.🫶'
    },
    3: {
        'intro_message': "Привіт! Ви на третьому дні інтенсиву — і сьогоднішній подкаст про те, що надихає.\n\nГостя — нейлблогерка, яка пройшла шлях від локального майстра до людини, що працює з брендами, веде блог і має вплив.\n\nМи поговорили відверто:\n– Як не зупинитись, коли не вірять\n– Як знайти свою унікальність\n– І як перетворити манікюр не просто на роботу, а на спосіб життя 🫶🫂",
        'videos': [
            {'file_id': 'BAACAgIAAyEFAASaGaDWAAMdaB4FIrjeF6bjWloGXew86vL6HVoAAjxsAAJ_NfBI0bpuSf4EmW82BA', 'caption': ''}
        ],
        'completion_message': 'Вітаємо! Ви завершили основну частину курсу!'
    },
    4: {
        'bonus_text': "Це відео — бонус, подарунок 🎁 для тебе, як для майстра, який хоче працювати не \"як-небудь\", а **системно, швидко, красиво**.\n\nЗбережи, передивись кілька разів, і впровадь вже сьогодні!\nБо одна фішка — вже економія часу.\nА час — це твоя ціна.\n\nЗ любов'ю,\n**твоя Стелла**",
        'videos': [
            {'file_id': 'BAACAgIAAyEFAASaGaDWAAMVaB4AAX6edqYeZgtKTooOZCUaku2xAAJtbwACdgAB8EiOu4OkQVusSTYE', 'caption': 'Бонусний урок - Секрети професійного успіху'}
        ],
        'post_bonus_text': "**ЗНИЖКА – 10 % ДЛЯ МОЇХ!** 🎁🎁🎁\nВ магазині [LianaNail Official Ukraine](https://www.instagram.com/lianail_official_ukraine/)\n\n**За моїм промокодом** **STELLA09**\n\n**Як скористатися знижкою** 🤔:\n1. Заходиш на сайт магазину, додаєш усе потрібне в кошик.\n2. Після оформлення з тобою зв'яжеться менеджер — просто скажи:\n\"**У мене є промокод STELLA09**\" — і знижку буде застосовано. ✅\n\nАбо:\n3. Пиши одразу в Instagram-магазин у дірект —\n**вкажи мій промокод STELLA09**, і менеджер оформить тобі знижку вручну. ✅\n\n**Роби красу — вигідно.**\n**Працюй з любов'ю.**"
    }
}

def load_user_data():
    """Завантаження даних користувачів"""
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Помилка завантаження даних: {e}")
    return {}

def save_user_data(data):
    """Збереження даних користувачів"""
    try:
        os.makedirs(os.path.dirname(USER_DATA_FILE) or '.', exist_ok=True)
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Помилка збереження даних: {e}")

user_data = load_user_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробка команди /start"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    if user_id in user_data:
        await update.message.reply_text(f"З поверненням, {user_name}! Ваш курс вже розпочато.")
        return
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    user_data[user_id] = {
        'name': user_name,
        'start_date': current_date,
        'current_day': 1,
        'last_lesson_date': current_date
    }
    save_user_data(user_data)
    
    await update.message.reply_text(LESSONS[1]['intro_message'], parse_mode='Markdown')
    await send_lesson(context.bot, user_id, 1)

async def send_lesson(bot, user_id: str, day: int) -> None:
    """Відправка уроку"""
    try:
        if day > 3:
            await send_bonus(bot, user_id)
            return
        
        lesson = LESSONS.get(day)
        if not lesson:
            raise ValueError(f"Немає уроку для дня {day}")
        
        if day > 1 and 'intro_message' in lesson:
            await bot.send_message(
                chat_id=user_id,
                text=lesson['intro_message'],
                parse_mode='Markdown'
            )
        
        for video in lesson['videos']:
            try:
                await bot.send_video(
                    chat_id=user_id,
                    video=video['file_id'],
                    caption=video['caption']
                )
            except Exception as e:
                logger.error(f"Помилка відправки відео: {e}")
                await bot.send_message(
                    chat_id=user_id,
                    text="Не вдалося відправити відео. Спробуйте пізніше."
                )
        
        if day == 2 and 'post_videos_message' in lesson:
            await bot.send_message(
                chat_id=user_id,
                text=lesson['post_videos_message'],
                parse_mode='Markdown'
            )
            if 'documents' in lesson:
                for doc in lesson['documents']:
                    try:
                        await bot.send_document(
                            chat_id=user_id,
                            document=doc['file_id'],
                            caption=doc['caption']
                        )
                    except Exception as e:
                        logger.error(f"Помилка відправки документа: {e}")
        
        user_data[user_id]['current_day'] = day
        user_data[user_id]['last_lesson_date'] = datetime.now().strftime('%Y-%m-%d')
        save_user_data(user_data)
        
        if day == 3:
            await bot.send_message(
                chat_id=user_id,
                text=LESSONS[3]['completion_message'],
                parse_mode='Markdown'
            )
            await send_bonus(bot, user_id)
        elif day < 3:
            keyboard = [
                [InlineKeyboardButton("Отримати наступний урок зараз", callback_data=f"next_now_{day+1}")],
                [InlineKeyboardButton("Завтра", callback_data=f"next_day_{day+1}")],
                [InlineKeyboardButton("Через 2 дні", callback_data=f"next_2days_{day+1}")]
            ]
            await bot.send_message(
                chat_id=user_id, 
                text=f"Коли ви хочете отримати наступний урок?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    except Exception as e:
        logger.error(f"Помилка відправки уроку {day}: {e}")
        await bot.send_message(
            chat_id=user_id,
            text="Сталася помилка. Спробуйте пізніше."
        )

async def send_bonus(bot, user_id: str) -> None:
    """Відправка бонусного матеріалу"""
    try:
        bonus = LESSONS[4]
        
        # Відправляємо заголовок бонусу
        await bot.send_message(
            chat_id=user_id,
            text="🎁 Бонусний матеріал:",
            parse_mode='Markdown'
        )
        
        # Відправляємо основний текст бонусу
        await bot.send_message(
            chat_id=user_id,
            text=bonus['bonus_text'],
            parse_mode='Markdown'
        )
        
        # Відправляємо бонусне відео
        for video in bonus['videos']:
            try:
                await bot.send_video(
                    chat_id=user_id,
                    video=video['file_id'],
                    caption=video['caption'],
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Помилка відправки бонусного відео: {e}")
                await bot.send_message(
                    chat_id=user_id,
                    text="Не вдалося відправити бонусне відео. Спробуйте пізніше."
                )
        
        # Відправляємо інформацію про знижку
        if 'post_bonus_text' in bonus:
            await bot.send_message(
                chat_id=user_id,
                text=bonus['post_bonus_text'],
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        
        # Оновлюємо статус користувача
        user_data[user_id]['current_day'] = 4
        user_data[user_id]['completed'] = True
        save_user_data(user_data)
        
    except Exception as e:
        logger.error(f"Помилка відправки бонусу: {e}")
        await bot.send_message(
            chat_id=user_id,
            text="Сталася помилка при відправці бонусу. Спробуйте пізніше."
        )

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробка натискань кнопок"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    if user_id not in user_data:
        await query.edit_message_text(text="Спочатку почніть курс: /start")
        return
    
    callback_data = query.data
    
    if callback_data.startswith("next_now_"):
        lesson_day = int(callback_data.split("_")[2])
        await query.edit_message_text(text=f"Відправляємо урок {lesson_day}...")
        await send_lesson(context.bot, user_id, lesson_day)
    
    elif callback_data.startswith("next_day_"):
        lesson_day = int(callback_data.split("_")[2])
        selected_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        await query.edit_message_text(text=f"Ви отримаєте урок {lesson_day} завтра о 10:00.")
        user_data[user_id]["next_lesson_day"] = lesson_day
        user_data[user_id]["next_lesson_date"] = selected_date
        user_data[user_id]["next_lesson_time"] = "10:00"
        save_user_data(user_data)
    
    elif callback_data.startswith("next_2days_"):
        lesson_day = int(callback_data.split("_")[2])
        selected_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        await query.edit_message_text(text=f"Ви отримаєте урок {lesson_day} через 2 дні о 10:00.")
        user_data[user_id]["next_lesson_day"] = lesson_day
        user_data[user_id]["next_lesson_date"] = selected_date
        user_data[user_id]["next_lesson_time"] = "10:00"
        save_user_data(user_data)

async def check_and_send_scheduled_lessons():
    """Перевірка та відправка запланованих уроків"""
    try:
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M')
        
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        for user_id, data in user_data.items():
            if data.get('completed', False):
                continue
                
            if ("next_lesson_date" in data and 
                "next_lesson_time" in data and
                data["next_lesson_date"] <= current_date and
                data["next_lesson_time"] <= current_time):
                
                next_day = data.get("next_lesson_day", data['current_day'] + 1)
                try:
                    await send_lesson(app.bot, user_id, next_day)
                    for key in ["next_lesson_date", "next_lesson_time", "next_lesson_day"]:
                        data.pop(key, None)
                    save_user_data(user_data)
                except Exception as e:
                    logger.error(f"Помилка відправки уроку {next_day}: {e}")
        
        await app.shutdown()
    except Exception as e:
        logger.error(f"Помилка перевірки уроків: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help"""
    await update.message.reply_text(
        "Цей бот відправить вам 3-денний міні-курс.\n\n"
        "Команди:\n"
        "/start - Почати курс\n"
        "/help - Довідка\n"
        "/status - Ваш прогрес\n"
        "/next - Наступний урок\n"
        "/bonus - Бонусний матеріал"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /status"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_data:
        await update.message.reply_text("Спочатку почніть курс: /start")
        return
    
    data = user_data[user_id]
    current_day = data['current_day']
    
    if data.get('completed', False):
        await update.message.reply_text("Ви завершили курс! Вітаємо!")
    elif current_day >= 3:
        await update.message.reply_text("Ви завершили основний курс! Бонус вже відправлено.")
    else:
        if "next_lesson_date" in data:
            next_date = data["next_lesson_date"]
            await update.message.reply_text(f"Ви на дні {current_day}. Наступний урок буде {next_date} о 10:00.")
        else:
            await update.message.reply_text(f"Ви на дні {current_day}. Використайте /next для наступного уроку.")

async def next_lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /next"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_data:
        await update.message.reply_text("Спочатку почніть курс: /start")
        return
    
    data = user_data[user_id]
    current_day = data['current_day']
    
    if data.get('completed', False):
        await update.message.reply_text("Ви вже завершили весь курс!")
    elif current_day >= 3:
        await update.message.reply_text("Ви завершили основний курс! Бонус вже відправлено.")
    else:
        next_day = current_day + 1
        await update.message.reply_text(f"Відправляємо урок {next_day}...")
        await send_lesson(context.bot, user_id, next_day)

async def bonus_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /bonus"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_data:
        await update.message.reply_text("Спочатку почніть курс: /start")
        return
    
    data = user_data[user_id]
    
    if data.get('completed', False):
        await update.message.reply_text("Ви вже отримали бонус.")
    elif data['current_day'] >= 3 or TEST_MODE:
        await update.message.reply_text("Відправляємо бонус...")
        await send_bonus(context.bot, user_id)
    else:
        await update.message.reply_text(f"Ви ще не завершили курс (наразі день {data['current_day']}/3).")

def ping_server():
    """Пінгування сервера"""
    try:
        response = requests.get(RENDER_APP_URL, timeout=10)
        logger.info(f"Ping: {response.status_code}")
    except Exception as e:
        logger.error(f"Помилка пінгу: {e}")

def setup_web_server():
    """Налаштування веб-сервера"""
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "Bot is running"
    
    @app.route('/health')
    def health():
        return "OK", 200
    
    import threading
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
    ).start()

def setup_scheduler():
    """Налаштування планувальника"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_send_scheduled_lessons, 'cron', hour='*', minute=0)
    scheduler.add_job(ping_server, 'interval', minutes=10)
    scheduler.start()
    logger.info("Планувальник запущено")

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("next", next_lesson_command))
    application.add_handler(CommandHandler("bonus", bonus_command))
    application.add_handler(CallbackQueryHandler(handle_button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
        lambda u, c: u.message.reply_text("Використайте /start для початку курсу.")))

    setup_scheduler()
    setup_web_server()
    
    application.run_polling()

if __name__ == "__main__":
    main()