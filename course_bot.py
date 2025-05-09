# -*- coding: utf-8 -*-
import logging
import os
import json
from server import keep_alive
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler

import os

# Try to import dotenv, but continue if not available
try:
    from dotenv import load_dotenv
    load_dotenv()  # Move this line INSIDE the try block
except ImportError:
    # If dotenv is not installed, just continue
    pass

TOKEN = os.getenv('7951312973:AAG-y-gAzZ4DteNhTeZxKIukvcpIx5xOKrU')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = '7951312973:AAG-y-gAzZ4DteNhTeZxKIukvcpIx5xOKrU'  # Replace with your actual token from BotFather

# Database simulation - in production, use a real database
USER_DATA_FILE = 'user_data.json'

# Flag to control testing mode - set to False for normal operation
TEST_MODE = False

# Video lessons - properly encoding Cyrillic strings with proper formatting
LESSONS = {
    1: {
        'intro_message': "Вітаю вас на першому дні інтенсиву! 🎊,\n\n"
        "Сьогодні ви отримали перший урок — *подкаст із\n"
        "психологом* про маніпуляції в бʼюті-сфері."
        "Ми поговоримо чесно:\n"
        "– Чому маніпуляції — це не \"дрібниці\", а серйозне порушення кордонів\n"
        "– Як їх розпізнати в роботі з керівництвом, колегами та клієнтами\n"
        "– Та найголовніше — як навчитись себе захищати\n",
        'videos': [
            {'file_id': 'BAACAgIAAyEFAASaGaDWAAMWaB4BuTq41XAp90PnvmCB4hMTGL4AAhZsAAJ_NfBI39cIf7_aME02BA', 
             'caption': 'Подкаст із психологом (маніпуляції в б\'юті-сфері)'}
        ],
        'completion_message': 'Завтра на вас чекатиме другий урок — подкаст з адвокаткою про ФОПи, права майстра та орендні договори.✔️'
    },
    2: {
        'intro_message': "Вітаю!🙌\n\n"
        "Сьогодні ви отримали другий урок — подкаст із адвокаткою, де ми говоримо про те, що мусить знати кожен майстер:\n"
        "– Як правильно оформити ФОП та яку групу обрати\n"
        "– Як захистити свої права, працюючи в салоні або на себе\n"
        "– На що звертати увагу в орендних договорах: суборенда, частина приміщення, поділ комуналки\n\n"
        "Ми розклали юридичні нюанси простою мовою — без \"страшних\" термінів, тільки реальні ситуації з практики.",
        'videos': [
            {'file_id': 'BAACAgIAAyEFAASaGaDWAAMaaB4EscQSmB4_JHtsqGc4gMcDXAoAAiRsAAJ_NfBIZVlHygKFZXE2BA', 
             'caption': 'Подкаст із адвокаткою (ФОП, оренда, права майстра)'}
        ],
        'post_videos_message': '🎁🎁🎁 🎁🎁🎁🎁🎁🎁🎁🎁🎁\nЦі документи допоможуть вам не "попасти" на словах і зафіксувати всі умови співпраці офіційно.📜\n**Завантажуйте, адаптуйте під себе і працюйте впевнено!**',
        'documents': [
            {'file_id': 'BQACAgIAAyEFAASaGaDWAAMXaB4DMIL06ORGZhLDAdG8iirzJIYAAqNvAAJ2AAHwSDEtYlx3aq2pNgQ', 
             'caption': 'Документ 1'},
            {'file_id': 'BQACAgIAAyEFAASaGaDWAAMYaB4DUx0MvIeVKKJxghbli2zQVCYAAqVvAAJ2AAHwSDX-cXcbud4QNgQ', 
             'caption': 'Документ 2'}
        ],
        'completion_message': 'Завтра ви отримаєте завершальний третій урок — щиру історію успіху від нейлблогерки, яка колись починала з нуля.🫶'
    },
    3: {
        'intro_message': "Привіт! Ви на третьому дні інтенсиву — і сьогоднішній подкаст про те, що надихає.\n\n"
        "Гостя — нейлблогерка, яка пройшла шлях від локального майстра до людини, що працює з брендами, веде блог і має вплив.\n\n"
        "Ми поговорили відверто:\n"
        "– Як не зупинитись, коли не вірять\n"
        "– Як знайти свою унікальність\n"
        "– І як перетворити манікюр не просто на роботу, а на спосіб життя 🫶🫂",
        'videos': [
            {'file_id': 'BAACAgIAAyEFAASaGaDWAAMdaB4FIrjeF6bjWloGXew86vL6HVoAAjxsAAJ_NfBI0bpuSf4EmW82BA', 
             'caption': 'Подкаст із нейл-блогеркою (справжня історія успіху)'}
        ],
        'completion_message': 'Вітаємо! Ви завершили основну частину курсу!'
    },
    # Bonus content (day 4)
    4: {
        'bonus_text': "Це відео — бонус, подарунок 🎁 для тебе, як для майстра, який хоче працювати не \"як-небудь\", а **системно, швидко, красиво**.\n\nЗбережи, передивись кілька разів, і впровадь вже сьогодні!\nБо одна фішка — вже економія часу.\nА час — це твоя ціна.\n\nЗ любов'ю,\n**твоя Стелла**",
        'videos': [
            {'file_id': 'BAACAgIAAyEFAASaGaDWAAMVaB4AAX6edqYeZgtKTooOZCUaku2xAAJtbwACdgAB8EiOu4OkQVusSTYE', 
             'caption': 'Бонусний урок - Секрети професійного успіху'}
        ],
        'post_bonus_text': "**ЗНИЖКА – 10 % ДЛЯ МОЇХ!** 🎁🎁🎁\nВ магазині https://www.instagram.com/lianail_official_ukraine?igsh=MTR2ZTZvNHNxaWxreA==\n\n**За моїм промокодом** **STELLA09**\n\n**Як скористатися знижкою** 🤔:\n1. Заходиш на сайт магазину, додаєш усе потрібне в кошик.\n2. Після оформлення з тобою зв'яжеться менеджер — просто скажи:\n\"**У мене є промокод STELLA09**\" — і знижку буде застосовано. ✅\n\nАбо:\n3. Пиши одразу в Instagram-магазин у дірект —\n**вкажи мій промокод STELLA09**, і менеджер оформить тобі знижку вручну. ✅\n\n**Роби красу — вигідно.**\n**Працюй з любов'ю.**"
    }
}

def load_user_data():
    """Load user data from file or environment"""
    if 'USER_DATA' in os.environ:
        return json.loads(os.environ.get('USER_DATA', '{}'))
    elif os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    """Save user data to file and environment if possible"""
    # Always save to file for local development
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    
    # If running on Render, also update environment variable
    if 'RENDER' in os.environ:
        # Note: This is a workaround and has limitations
        # For production, use a proper database
        os.environ['USER_DATA'] = json.dumps(data)

# Initialize user data storage
user_data = load_user_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message and first lesson when the command /start is issued"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    # Check if user already started the course
    if user_id in user_data:
        await update.message.reply_text(f"З поверненням, {user_name}! Ваш курс вже розпочато.")
        return
    
    # Register new user
    current_date = datetime.now().strftime('%Y-%m-%d')
    user_data[user_id] = {
        'name': user_name,
        'start_date': current_date,
        'current_day': 1,
        'last_lesson_date': current_date
    }
    save_user_data(user_data)
    
    # Send welcome message from lesson 1
    await update.message.reply_text(
        LESSONS[1]['intro_message'],
        parse_mode='Markdown'
    )
    
    # Send first lesson
    await send_lesson(context.bot, user_id, 1)

async def send_lesson(bot, user_id: str, day: int) -> None:
    """Send a specific lesson to a user"""
    if day > 3:
        # Send bonus content
        await send_bonus(bot, user_id)
        return
    
    lesson = LESSONS[day]
    
    # Send intro message if it's not the first day (first day intro is sent in start command)
    if day > 1 and 'intro_message' in lesson:
        await bot.send_message(
            chat_id=user_id,
            text=lesson['intro_message'],
            parse_mode='Markdown'
        )
    
    # Send each video in the lesson
    for video in lesson['videos']:
        await bot.send_video(
            chat_id=user_id,
            video=video['file_id'],
            caption=video['caption']
        )
    
    # For day 2, send the special documents message and documents
    if day == 2 and 'post_videos_message' in lesson:
        await bot.send_message(
            chat_id=user_id,
            text=lesson['post_videos_message'],
            parse_mode='Markdown'
        )
        
        # Send documents
        if 'documents' in lesson:
            for doc in lesson['documents']:
                await bot.send_document(
                    chat_id=user_id,
                    document=doc['file_id'],
                    caption=doc['caption']
                )
    
    # Update user data
    user_data[user_id]['current_day'] = day
    user_data[user_id]['last_lesson_date'] = datetime.now().strftime('%Y-%m-%d')
    save_user_data(user_data)
    
    if day < 3:
        await bot.send_message(
            chat_id=user_id, 
            text=lesson['completion_message'],
            parse_mode='Markdown'
        )
    else:
        # After day 3, send notification about bonus
        await bot.send_message(
            chat_id=user_id,
            text="Вітаємо! Ви завершили міні-курс! Завтра ви отримаєте спеціальний бонус.",
            parse_mode='Markdown'
        )
        
        # If in test mode, immediately send the bonus content
        if TEST_MODE:
            await send_bonus(bot, user_id)

async def send_bonus(bot, user_id: str) -> None:
    """Send bonus content to user"""
    bonus = LESSONS[4]
    
    # Send bonus text message first
    await bot.send_message(
        chat_id=user_id,
        text=bonus['bonus_text'],
        parse_mode='Markdown'
    )
    
    # Then send bonus video(s)
    for video in bonus['videos']:
        await bot.send_video(
            chat_id=user_id,
            video=video['file_id'],
            caption=video['caption']
        )
    
    # Send discount information
    if 'post_bonus_text' in bonus:
        await bot.send_message(
            chat_id=user_id,
            text=bonus['post_bonus_text'],
            parse_mode='Markdown'
        )
    
    # Update user status
    user_data[user_id]['current_day'] = 4
    user_data[user_id]['completed'] = True
    save_user_data(user_data)

async def check_and_send_daily_lessons():
    """Check if users should receive their next lesson"""
    # Skip if in test mode
    if TEST_MODE:
        return
        
    today = datetime.now().strftime('%Y-%m-%d')
    application = Application.builder().token(TOKEN).build()
    
    for user_id, data in user_data.items():
        # Skip users who have completed the full course (including bonus)
        if data.get('completed', False):
            continue
            
        last_lesson_date = datetime.strptime(data['last_lesson_date'], '%Y-%m-%d')
        next_lesson_date = last_lesson_date + timedelta(days=1)
        
        # If it's time for the next lesson
        if next_lesson_date.strftime('%Y-%m-%d') <= today and data['current_day'] <= 3:
            next_day = data['current_day'] + 1
            # Don't need a separate message here as the intro message is now part of send_lesson
            await send_lesson(application.bot, user_id, next_day)
    
    await application.shutdown()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued"""
    await update.message.reply_text(
        "Цей бот відправить вам 3-денний міні-курс.\n\n"
        "Команди:\n"
        "/start - Почати курс\n"
        "/help - Показати це повідомлення\n"
        "/status - Перевірити ваш прогрес\n"
        "/bonus - Отримати бонусний матеріал (якщо доступний)\n"
        "/test_on - Включити тестовий режим (всі повідомлення відразу)\n"
        "/test_off - Виключити тестовий режим (стандартний режим)"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check status of the course for this user"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_data:
        await update.message.reply_text("Ви ще не почали курс. Використайте /start щоб почати.")
        return
    
    data = user_data[user_id]
    current_day = data['current_day']
    
    if data.get('completed', False):
        await update.message.reply_text("Ви повністю завершили курс, включаючи бонусний матеріал! Вітаємо!")
    elif current_day >= 3:
        next_lesson_date = datetime.strptime(data['last_lesson_date'], '%Y-%m-%d') + timedelta(days=1)
        today = datetime.now()
        
        if next_lesson_date.date() <= today.date():
            await update.message.reply_text(
                "Ви завершили основну частину курсу! Бонусний матеріал готовий для вас. Використайте /bonus щоб отримати його зараз."
            )
        else:
            await update.message.reply_text(
                "Ви завершили основну частину курсу!\n"
                f"Ваш бонусний матеріал буде надіслано {next_lesson_date.strftime('%Y-%m-%d')}."
            )
    else:
        next_lesson_date = datetime.strptime(data['last_lesson_date'], '%Y-%m-%d') + timedelta(days=1)
        await update.message.reply_text(
            f"Ви на дні {current_day} курсу.\n"
            f"Ваш наступний урок (День {current_day+1}) буде надіслано {next_lesson_date.strftime('%Y-%m-%d')}."
        )

async def bonus_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send bonus content immediately if user has completed main course"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_data:
        await update.message.reply_text("Ви ще не почали курс. Використайте /start щоб почати.")
        return
    
    data = user_data[user_id]
    
    if data.get('completed', False):
        await update.message.reply_text("Ви вже отримали бонусний матеріал.")
    elif data['current_day'] >= 3 or TEST_MODE:
        await send_bonus(context.bot, user_id)
        await update.message.reply_text("Бонусний матеріал відправлено!")
    else:
        await update.message.reply_text(
            "Ви маєте завершити основну частину курсу (3 дні), щоб отримати бонус.\n"
            f"Наразі ви на дні {data['current_day']}."
        )

async def test_all_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test command to send all lessons at once"""
    user_id = str(update.effective_user.id)
    
    # Register user if not exists
    if user_id not in user_data:
        current_date = datetime.now().strftime('%Y-%m-%d')
        user_data[user_id] = {
            'name': update.effective_user.first_name,
            'start_date': current_date,
            'current_day': 0,
            'last_lesson_date': current_date
        }
        save_user_data(user_data)
    
    await update.message.reply_text("🧪 Тестовий режим: відправляємо всі уроки та бонуси...")
    
    # Send all lessons with short delays
    await update.message.reply_text("📚 Урок 1:")
    # Send intro for lesson 1
    await update.message.reply_text(
        LESSONS[1]['intro_message'],
        parse_mode='Markdown'
    )
    await send_lesson(context.bot, user_id, 1)
    
    await update.message.reply_text("📚 Урок 2:")
    # Send intro for lesson 2
    await update.message.reply_text(
        LESSONS[2]['intro_message'],
        parse_mode='Markdown'
    )
    await send_lesson(context.bot, user_id, 2)
    
    await update.message.reply_text("📚 Урок 3:")
    # Send intro for lesson 3
    await update.message.reply_text(
        LESSONS[3]['intro_message'],
        parse_mode='Markdown'
    )
    await send_lesson(context.bot, user_id, 3)
    
    # Bonus is sent automatically after lesson 3 in test mode
    
    await update.message.reply_text("✅ Тестування завершено! Всі повідомлення відправлено.")

async def test_mode_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable test mode"""
    global TEST_MODE
    TEST_MODE = True
    await update.message.reply_text(
        "🔧 Тестовий режим УВІМКНЕНО!\n"
        "Тепер ви можете отримати всі уроки одразу командою /test_all\n"
        "Вимкнути тестовий режим: /test_off"
    )

async def test_mode_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disable test mode"""
    global TEST_MODE
    TEST_MODE = False
    await update.message.reply_text(
        "🔧 Тестовий режим ВИМКНЕНО!\n"
        "Бот працює в звичайному режимі - один урок на день."
    )

def main() -> None:
    """Start the bot"""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("bonus", bonus_command))
    
    # Test commands
    application.add_handler(CommandHandler("test_all", test_all_lessons))
    application.add_handler(CommandHandler("test_on", test_mode_on))
    application.add_handler(CommandHandler("test_off", test_mode_off))

    # Set up scheduler for daily lessons
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_send_daily_lessons, 'interval', hours=1)  # Check every hour
    scheduler.start()
    
    # Налаштування порту та вебхука для Render
    PORT = int(os.environ.get('PORT', 8443))
    
    # Перевіряємо, чи запущено на Render
    if 'RENDER' in os.environ:
        # Отримуємо URL сервісу з змінної середовища
        WEBHOOK_URL = os.environ.get('https://render.com/docs/troubleshooting-deploys')
        
        # Запускаємо webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
        )
    else:
        # Локальний режим або інший хостинг
        keep_alive()
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()