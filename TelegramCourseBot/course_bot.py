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

# Video lessons - properly encoding Cyrillic strings
LESSONS = {
    1: {
        'videos': [
            {'file_id': 'BAACAgIAAyEFAASaO0PaAAMSaBh81Oq5WA2Kyt5tZwTnQciQm2QAAr5vAAKPGMFIhbpMLiF2XDM2BA', 
             'caption': 'Подкаст із психологом (маніпуляції в б\'юті-сфері) - Частина 1'},
            {'file_id': 'BAACAgIAAyEFAASaO0PaAAMSaBh81Oq5WA2Kyt5tZwTnQciQm2QAAr5vAAKPGMFIhbpMLiF2XDM2BA', 
             'caption': 'Подкаст із психологом (маніпуляції в б\'юті-сфері) - Частина 2'}
        ],
        'completion_message': 'День 1 завершено! Завтра ви отримаєте урок 2.'
    },
    2: {
        'videos': [
            {'file_id': 'BQACAgIAAyEFAASaO0PaAAMRaBh3oY-4ZhU6GS0PVBgX1QeSoewAAnZvAAKPGMFIfedRg1BApKw2BA', 
             'caption': 'Подкаст із адвокаткою (ФОП, оренда, права майстра) - Частина 1'},
            {'file_id': 'BQACAgIAAyEFAASaO0PaAAMRaBh3oY-4ZhU6GS0PVBgX1QeSoewAAnZvAAKPGMFIfedRg1BApKw2BA', 
             'caption': 'Подкаст із адвокаткою (ФОП, оренда, права майстра) - Частина 2'}
        ],
        'completion_message': 'День 2 завершено! Завтра ви отримаєте урок 3.'
    },
    3: {
        'videos': [
            {'file_id': 'BQACAgIAAyEFAASaO0PaAAMRaBh3oY-4ZhU6GS0PVBgX1QeSoewAAnZvAAKPGMFIfedRg1BApKw2BA', 
             'caption': 'Подкаст із нейл-блогеркою (справжня історія успіху) - Частина 1'},
            {'file_id': 'BQACAgIAAyEFAASaO0PaAAMRaBh3oY-4ZhU6GS0PVBgX1QeSoewAAnZvAAKPGMFIfedRg1BApKw2BA', 
             'caption': 'Подкаст із нейл-блогеркою (справжня історія успіху) - Частина 2'}
        ],
        'completion_message': 'Вітаємо! Ви завершили основну частину курсу!'
    },
    # Bonus content (day 4)
    4: {
        'bonus_text': 'Дякуємо за проходження нашого міні-курсу! Ось ваш бонусний подарунок.\n\nВикористовуйте код знижки **NAILPRO25** для отримання 25% знижки в нашому магазині.',
        'videos': [
            {'file_id': 'BQACAgIAAyEFAASaO0PaAAMRaBh3oY-4ZhU6GS0PVBgX1QeSoewAAnZvAAKPGMFIfedRg1BApKw2BA', 
             'caption': 'Бонусний урок - Секрети професійного успіху'}
        ]
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
        await update.message.reply_text("З поверненням, {}! Ваш курс вже розпочато.".format(user_name))
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
    
    # Send welcome message
    await update.message.reply_text(
        "Вітаємо в міні-курсі, {}!\n\n"
        "Ви отримаєте один урок на день протягом наступних 3 днів.\n"
        "Ось ваш перший урок:".format(user_name)
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
    
    # Send each video in the lesson
    for video in lesson['videos']:
        await bot.send_video(
            chat_id=user_id,
            video=video['file_id'],
            caption=video['caption']
        )
    
    # Update user data
    user_data[user_id]['current_day'] = day
    user_data[user_id]['last_lesson_date'] = datetime.now().strftime('%Y-%m-%d')
    save_user_data(user_data)
    
    if day < 3:
        await bot.send_message(
            chat_id=user_id, 
            text=lesson['completion_message']
        )
    else:
        # After day 3, send notification about bonus
        await bot.send_message(
            chat_id=user_id,
            text="Вітаємо! Ви завершили міні-курс! Завтра ви отримаєте спеціальний бонус."
        )

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
    
    # Update user status
    user_data[user_id]['current_day'] = 4
    user_data[user_id]['completed'] = True
    save_user_data(user_data)

async def check_and_send_daily_lessons():
    """Check if users should receive their next lesson"""
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
            await application.bot.send_message(
                chat_id=user_id,
                text="Ось ваш урок {}:".format(next_day)
            )
            await send_lesson(application.bot, user_id, next_day)
    
    await application.shutdown()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued"""
    await update.message.reply_text(
        "Цей бот відправить вам 3-денний міні-курс.\n\n"
        "Команди:\n"
        "/start - Почати курс\n"
        "/help - Показати це повідомлення\n"
        "/status - Перевірити ваш прогрес"
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
                "Ваш бонусний матеріал буде надіслано {}.".format(next_lesson_date.strftime('%Y-%m-%d'))
            )
    else:
        next_lesson_date = datetime.strptime(data['last_lesson_date'], '%Y-%m-%d') + timedelta(days=1)
        await update.message.reply_text(
            "Ви на дні {} курсу.\n"
            "Ваш наступний урок (День {}) буде надіслано {}.".format(
                current_day, current_day+1, next_lesson_date.strftime('%Y-%m-%d')
            )
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
    elif data['current_day'] >= 3:
        await send_bonus(context.bot, user_id)
        await update.message.reply_text("Бонусний матеріал відправлено!")
    else:
        await update.message.reply_text(
            "Ви маєте завершити основну частину курсу (3 дні), щоб отримати бонус.\n"
            "Наразі ви на дні {}.".format(data['current_day'])
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

    # Set up scheduler for daily lessons
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_send_daily_lessons, 'interval', hours=1)  # Check every hour
    scheduler.start()
    
    keep_alive()

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()