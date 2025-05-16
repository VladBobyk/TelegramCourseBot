import logging
import os
import json
import requests
import asyncio  # Add this with your other imports
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

RENDER_APP_URL = os.getenv('RENDER_APP_URL', 'https://telegramcoursebot-18ir.onrender.com')
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
            # Після 3-го уроку пропонуємо вибір часу для бонусу
            keyboard = [
                [InlineKeyboardButton("Отримати бонус зараз", callback_data="bonus_now")],
                [InlineKeyboardButton("Завтра", callback_data="bonus_tomorrow")],
                [InlineKeyboardButton("Через 2 дні", callback_data="bonus_2days")]
            ]
            await bot.send_message(
                chat_id=user_id,
                text="Вітаємо! Ви завершили основний курс! Коли ви хочете отримати бонусний матеріал?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif day < 3:
            # Для уроків 1-2 пропонуємо вибір часу для наступного уроку
            keyboard = [
                [InlineKeyboardButton("Отримати наступний урок зараз", callback_data=f"next_now_{day+1}")],
                [InlineKeyboardButton("Завтра", callback_data=f"next_tomorrow_{day+1}")],
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

async def ask_time_selection(bot, user_id: str, days_to_add: int, lesson_day: int = None):
    """Запит вибору часу для уроку/бонусу"""
    selected_date = (datetime.now() + timedelta(days=days_to_add)).strftime('%Y-%m-%d')
    
    keyboard = [
        [
            InlineKeyboardButton("Ранок (08:00)", callback_data=f"time_08:00_{days_to_add}_{lesson_day}"),
            InlineKeyboardButton("День (12:00)", callback_data=f"time_12:00_{days_to_add}_{lesson_day}"),
        ],
        [
            InlineKeyboardButton("Вечір (18:00)", callback_data=f"time_18:00_{days_to_add}_{lesson_day}"),
            InlineKeyboardButton("Ніч (22:00)", callback_data=f"time_22:00_{days_to_add}_{lesson_day}"),
        ]
    ]
    
    text = f"Оберіть бажаний час отримання "
    if lesson_day is None:
        text += f"бонусного матеріалу ({selected_date}):"
    else:
        text += f"уроку {lesson_day} ({selected_date}):"
    
    await bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
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
    
    # Debug log to see what's happening
    logger.info(f"Button clicked: {callback_data} by user {user_id}")
    
    if callback_data.startswith("next_now_"):
        lesson_day = int(callback_data.split("_")[2])
        await query.edit_message_text(text=f"Відправляємо урок {lesson_day}...")
        await send_lesson(context.bot, user_id, lesson_day)
    
    elif callback_data.startswith("next_tomorrow_"):
        lesson_day = int(callback_data.split("_")[2])
        await query.edit_message_text(text="Оберіть час отримання уроку:")
        await ask_time_selection(context.bot, user_id, 1, lesson_day)  # 1 день = завтра
    
    elif callback_data.startswith("next_2days_"):
        lesson_day = int(callback_data.split("_")[2])
        await query.edit_message_text(text="Оберіть час отримання уроку:")
        await ask_time_selection(context.bot, user_id, 2, lesson_day)  # 2 дні = післязавтра
    
    elif callback_data == "bonus_now":
        await query.edit_message_text(text="Відправляємо бонусний матеріал...")
        await send_bonus(context.bot, user_id)
    
    elif callback_data == "bonus_tomorrow":
        await query.edit_message_text(text="Оберіть час отримання бонусу:")
        await ask_time_selection(context.bot, user_id, 1)  # 1 день = завтра
    
    elif callback_data == "bonus_2days":
        await query.edit_message_text(text="Оберіть час отримання бонусу:")
        await ask_time_selection(context.bot, user_id, 2)  # 2 дні = післязавтра
    
    elif callback_data.startswith("time_"):
        parts = callback_data.split("_")
        selected_time = parts[1]  # Now gets the full time with format HH:MM
        days_to_add = int(parts[2])
        lesson_day_str = parts[3] if len(parts) > 3 else None
        
        selected_date = (datetime.now() + timedelta(days=days_to_add)).strftime('%Y-%m-%d')
        
        if lesson_day_str is None or lesson_day_str == "None":
            # Бонусний матеріал
            user_data[user_id]["next_bonus_date"] = selected_date
            user_data[user_id]["next_bonus_time"] = selected_time
            await query.edit_message_text(
                text=f"Ви отримаєте бонусний матеріал {selected_date} о {selected_time}."
            )
            logger.info(f"Scheduled bonus for user {user_id} at {selected_date} {selected_time}")
        else:
            # Звичайний урок
            lesson_day = int(lesson_day_str)
            user_data[user_id]["next_lesson_day"] = lesson_day
            user_data[user_id]["next_lesson_date"] = selected_date
            user_data[user_id]["next_lesson_time"] = selected_time
            await query.edit_message_text(
                text=f"Ви отримаєте урок {lesson_day} {selected_date} о {selected_time}."
            )
            logger.info(f"Scheduled lesson {lesson_day} for user {user_id} at {selected_date} {selected_time}")
        
        # Important: Save data immediately after updating
        save_user_data(user_data)

async def check_and_send_scheduled_lessons(bot=None):
    """Перевірка та відправка запланованих уроків"""
    try:
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M')
        
        logger.info(f"Running scheduled check at {current_date} {current_time}")
        
        if bot is None:
            # For standalone testing, create a bot instance
            bot = Application.builder().token(TELEGRAM_BOT_TOKEN).build().bot
            logger.info("Created new bot instance for check_and_send_scheduled_lessons")
        else:
            logger.info("Using provided bot instance for check_and_send_scheduled_lessons")
        
        for user_id, data in user_data.items():
            if data.get('completed', False):
                continue
                
            # Check for scheduled lessons - improved time comparison
            if "next_lesson_date" in data and "next_lesson_time" in data:
                scheduled_date = data["next_lesson_date"]
                scheduled_time = data["next_lesson_time"]
                
                # Parse the scheduled time
                try:
                    scheduled_datetime = datetime.strptime(f"{scheduled_date} {scheduled_time}", '%Y-%m-%d %H:%M')
                    logger.info(f"User {user_id} has lesson scheduled for {scheduled_datetime}, current time is {now}")
                    
                    # Check if scheduled time has passed
                    if now >= scheduled_datetime:
                        next_day = data.get("next_lesson_day", data.get('current_day', 1) + 1)
                        logger.info(f"Time to send lesson {next_day} to user {user_id}")
                        
                        try:
                            await send_lesson(bot, user_id, next_day)
                            # Remove scheduling data after sending
                            for key in ["next_lesson_date", "next_lesson_time", "next_lesson_day"]:
                                data.pop(key, None)
                            save_user_data(user_data)
                            logger.info(f"Successfully sent lesson {next_day} to user {user_id}")
                        except Exception as e:
                            logger.error(f"Error sending lesson {next_day} to user {user_id}: {e}")
                except Exception as e:
                    logger.error(f"Error parsing scheduled datetime for user {user_id}: {e}")
            
            # Check for scheduled bonuses - improved time comparison
            if "next_bonus_date" in data and "next_bonus_time" in data:
                scheduled_date = data["next_bonus_date"]
                scheduled_time = data["next_bonus_time"]
                
                # Parse the scheduled time
                try:
                    scheduled_datetime = datetime.strptime(f"{scheduled_date} {scheduled_time}", '%Y-%m-%d %H:%M')
                    logger.info(f"User {user_id} has bonus scheduled for {scheduled_datetime}, current time is {now}")
                    
                    # Check if scheduled time has passed
                    if now >= scheduled_datetime:
                        logger.info(f"Time to send bonus to user {user_id}")
                        
                        try:
                            await send_bonus(bot, user_id)
                            # Remove scheduling data after sending
                            for key in ["next_bonus_date", "next_bonus_time"]:
                                data.pop(key, None)
                            save_user_data(user_data)
                            logger.info(f"Successfully sent bonus to user {user_id}")
                        except Exception as e:
                            logger.error(f"Error sending bonus to user {user_id}: {e}")
                except Exception as e:
                    logger.error(f"Error parsing scheduled datetime for user {user_id}: {e}")
                    
    except Exception as e:
        logger.error(f"Error in check_and_send_scheduled_lessons: {e}")
        # Print full exception for debugging
        import traceback
        logger.error(traceback.format_exc())



def setup_scheduler(application=None):
    """Налаштування планувальника"""
    scheduler = BackgroundScheduler(daemon=True)
    
    # Use a more robust approach for the async function in scheduler
    def run_async_check():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if application:
            # If application is provided, use its bot
            loop.run_until_complete(check_and_send_scheduled_lessons(application.bot))
        else:
            # Fallback for backward compatibility
            loop.run_until_complete(check_and_send_scheduled_lessons())
        loop.close()
        
    # Add job to run every 1 minute (more frequent checks)
    scheduler.add_job(run_async_check, 'interval', minutes=1)
    scheduler.add_job(ping_server, 'interval', minutes=10)
    
    try:
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        
    return scheduler

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
        if "next_bonus_date" in data:
            await update.message.reply_text(
                f"Ви завершили основний курс! Бонус буде надіслано {data['next_bonus_date']} о {data['next_bonus_time']}.\n"
                "Ви можете отримати його зараз командою /bonus."
            )
        else:
            await update.message.reply_text(
                "Ви завершили основний курс! Бонусний матеріал готовий для вас.\n"
                "Використайте /bonus щоб отримати його зараз."
            )
    else:
        if "next_lesson_date" in data:
            await update.message.reply_text(
                f"Ви на дні {current_day}. Наступний урок буде {data['next_lesson_date']} о {data['next_lesson_time']}.\n"
                "Ви можете отримати його зараз командою /next."
            )
        else:
            await update.message.reply_text(
                f"Ви на дні {current_day}. Використайте /next для наступного уроку."
            )

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
        await update.message.reply_text(
            "Ви завершили основний курс! Для отримання бонусного матеріалу використайте команду /bonus."
        )
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
        await update.message.reply_text("Ви вже отримали бонусний матеріал.")
    elif data['current_day'] >= 3 or TEST_MODE:
        await update.message.reply_text("Відправляємо бонусний матеріал...")
        await send_bonus(context.bot, user_id)
    else:
        await update.message.reply_text(
            f"Ви ще не завершили основний курс (наразі день {data['current_day']}/3)."
        )

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

async def test_scheduler_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /test_scheduler для тестування розкладу"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_data:
        await update.message.reply_text("Спочатку почніть курс: /start")
        return
    
    await update.message.reply_text("Тестуємо розклад уроків. Симулюємо заплановану відправку...")
    
    # Create a copy of user data for testing purposes
    test_data = {user_id: user_data[user_id].copy()}
    
    # If user has a scheduled lesson, simulate it's time to send
    if "next_lesson_date" in test_data[user_id] and "next_lesson_time" in test_data[user_id]:
        next_day = test_data[user_id].get("next_lesson_day", test_data[user_id]['current_day'] + 1)
        await update.message.reply_text(f"Знайдено запланований урок {next_day} на {test_data[user_id]['next_lesson_date']} о {test_data[user_id]['next_lesson_time']}. Відправляємо...")
        await send_lesson(context.bot, user_id, next_day)
        # Remove scheduling data after sending
        for key in ["next_lesson_date", "next_lesson_time", "next_lesson_day"]:
            if key in user_data[user_id]:
                user_data[user_id].pop(key)
        save_user_data(user_data)
        return
        
    # If user has a scheduled bonus, simulate it's time to send
    if "next_bonus_date" in test_data[user_id] and "next_bonus_time" in test_data[user_id]:
        await update.message.reply_text(f"Знайдено запланований бонус на {test_data[user_id]['next_bonus_date']} о {test_data[user_id]['next_bonus_time']}. Відправляємо...")
        await send_bonus(context.bot, user_id)
        # Remove scheduling data after sending
        for key in ["next_bonus_date", "next_bonus_time"]:
            if key in user_data[user_id]:
                user_data[user_id].pop(key)
        save_user_data(user_data)
        return
    
    await update.message.reply_text("Немає запланованих уроків або бонусів для тестування.")

async def debug_schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /debug_schedule для перегляду розкладу"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_data:
        await update.message.reply_text("Спочатку почніть курс: /start")
        return
    
    data = user_data[user_id]
    debug_info = f"Debug інформація для користувача {user_id}:\n\n"
    debug_info += f"Поточний день: {data.get('current_day', 'Не встановлено')}\n"
    debug_info += f"Завершено курс: {data.get('completed', False)}\n"
    debug_info += f"Дата початку: {data.get('start_date', 'Не встановлено')}\n"
    debug_info += f"Остання дата уроку: {data.get('last_lesson_date', 'Не встановлено')}\n"
    debug_info += f"\nВсі дані користувача: {json.dumps(data, ensure_ascii=False, indent=2)}\n"
    
    if "next_lesson_date" in data:
        debug_info += f"\nЗапланований урок {data.get('next_lesson_day')}:\n"
        debug_info += f"Дата: {data.get('next_lesson_date')}\n"
        debug_info += f"Час: {data.get('next_lesson_time')}\n"
        
        # Calculate time until send
        try:
            scheduled_time = datetime.strptime(f"{data['next_lesson_date']} {data['next_lesson_time']}", '%Y-%m-%d %H:%M')
            now = datetime.now()
            time_diff = scheduled_time - now
            if time_diff.total_seconds() > 0:
                hours, remainder = divmod(time_diff.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                debug_info += f"Залишилось часу: {int(hours)} год {int(minutes)} хв\n"
            else:
                debug_info += "Час відправки минув! Перевірте роботу планувальника.\n"
        except Exception as e:
            debug_info += f"Помилка обчислення часу: {str(e)}\n"
    
    if "next_bonus_date" in data:
        debug_info += f"\nЗапланований бонус:\n"
        debug_info += f"Дата: {data.get('next_bonus_date')}\n"
        debug_info += f"Час: {data.get('next_bonus_time')}\n"
        
        # Calculate time until send
        try:
            scheduled_time = datetime.strptime(f"{data['next_bonus_date']} {data['next_bonus_time']}", '%Y-%m-%d %H:%M')
            now = datetime.now()
            time_diff = scheduled_time - now
            if time_diff.total_seconds() > 0:
                hours, remainder = divmod(time_diff.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                debug_info += f"Залишилось часу: {int(hours)} год {int(minutes)} хв\n"
            else:
                debug_info += "Час відправки минув! Перевірте роботу планувальника.\n"
        except Exception as e:
            debug_info += f"Помилка обчислення часу: {str(e)}\n"
            
    # Check for scheduling information in the user message
    msg = update.effective_message.reply_to_message
    if msg:
        debug_info += f"\nПов'язане повідомлення: {msg.text[:100]}...\n"
    
    await update.message.reply_text(debug_info)


async def set_test_time_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /set_test_time для встановлення тестового часу"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_data:
        await update.message.reply_text("Спочатку почніть курс: /start")
        return
    
    if not context.args or len(context.args) != 2:
        await update.message.reply_text(
            "Використання: /set_test_time YYYY-MM-DD HH:MM\n"
            "Наприклад: /set_test_time 2025-05-16 08:00"
        )
        return
    
    try:
        test_date = context.args[0]
        test_time = context.args[1]
        # Validate format
        datetime.strptime(f"{test_date} {test_time}", '%Y-%m-%d %H:%M')
        
        # Check the user's current scheduling status
        current_data = user_data[user_id]
        logger.info(f"Current user data for {user_id}: {current_data}")
        
        has_next_lesson = "next_lesson_date" in current_data and "next_lesson_time" in current_data
        has_next_bonus = "next_bonus_date" in current_data and "next_bonus_time" in current_data
        
        if has_next_lesson:
            current_data["next_lesson_date"] = test_date
            current_data["next_lesson_time"] = test_time
            save_user_data(user_data)
            await update.message.reply_text(
                f"Тестовий час для уроку {current_data.get('next_lesson_day', '?')} встановлено на {test_date} {test_time}.\n"
                "Використайте /test_scheduler для перевірки відправки."
            )
        elif has_next_bonus:
            current_data["next_bonus_date"] = test_date
            current_data["next_bonus_time"] = test_time
            save_user_data(user_data)
            await update.message.reply_text(
                f"Тестовий час для бонусу встановлено на {test_date} {test_time}.\n"
                "Використайте /test_scheduler для перевірки відправки."
            )
        else:
            # Special case: Let's check if the message about scheduling exists
            msg = update.effective_message.reply_to_message
            if msg and "Ви отримаєте бонусний матеріал" in msg.text:
                # Extract date and time from the message if possible
                current_data["next_bonus_date"] = test_date  # We'll use the user-provided date/time
                current_data["next_bonus_time"] = test_time
                save_user_data(user_data)
                await update.message.reply_text(
                    f"Тестовий час для бонусу встановлено на {test_date} {test_time} (відновлено з повідомлення).\n"
                    "Використайте /test_scheduler для перевірки відправки."
                )
            elif msg and "Ви отримаєте урок" in msg.text:
                # Try to extract lesson number
                import re
                match = re.search(r"урок (\d+)", msg.text)
                lesson_day = int(match.group(1)) if match else current_data.get('current_day', 1) + 1
                
                current_data["next_lesson_day"] = lesson_day
                current_data["next_lesson_date"] = test_date
                current_data["next_lesson_time"] = test_time
                save_user_data(user_data)
                await update.message.reply_text(
                    f"Тестовий час для уроку {lesson_day} встановлено на {test_date} {test_time} (відновлено з повідомлення).\n"
                    "Використайте /test_scheduler для перевірки відправки."
                )
            else:
                # We can't find scheduled info, let's create it based on current day
                current_day = current_data.get('current_day', 1)
                if current_day >= 3:
                    # Should be bonus next
                    current_data["next_bonus_date"] = test_date
                    current_data["next_bonus_time"] = test_time
                    save_user_data(user_data)
                    await update.message.reply_text(
                        f"Тестовий час для бонусу встановлено на {test_date} {test_time} (створено нове розклад).\n"
                        "Використайте /test_scheduler для перевірки відправки."
                    )
                else:
                    # Should be next lesson
                    next_day = current_day + 1
                    current_data["next_lesson_day"] = next_day
                    current_data["next_lesson_date"] = test_date
                    current_data["next_lesson_time"] = test_time
                    save_user_data(user_data)
                    await update.message.reply_text(
                        f"Тестовий час для уроку {next_day} встановлено на {test_date} {test_time} (створено нове розклад).\n"
                        "Використайте /test_scheduler для перевірки відправки."
                    )
    except ValueError:
        await update.message.reply_text(
            "Неправильний формат дати/часу.\n"
            "Використайте формат: YYYY-MM-DD HH:MM"
        )
    except Exception as e:
        logger.error(f"Error in set_test_time: {str(e)}")
        await update.message.reply_text(f"Помилка: {str(e)}")


async def check_scheduler_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /check_scheduler для ручної перевірки планувальника"""
    await update.message.reply_text("Запускаємо перевірку планувальника...")
    await check_and_send_scheduled_lessons()
    await update.message.reply_text("Перевірка планувальника завершена.")



def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("next", next_lesson_command))
    application.add_handler(CommandHandler("bonus", bonus_command))
    application.add_handler(CommandHandler("test_scheduler", test_scheduler_command))
    application.add_handler(CommandHandler("debug_schedule", debug_schedule_command))
    application.add_handler(CommandHandler("set_test_time", set_test_time_command))
    application.add_handler(CommandHandler("check_scheduler", check_scheduler_command))
    application.add_handler(CallbackQueryHandler(handle_button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
        lambda u, c: u.message.reply_text("Використайте /start для початку курсу.")))

    # Setup scheduler with application passed in
    scheduler = setup_scheduler(application)
    
    # Setup web server
    setup_web_server()
    
    # Run initial check to catch any missed scheduled items
    asyncio.run(check_and_send_scheduled_lessons(application.bot))
    
    # Log startup information
    logger.info("Bot started and ready to process messages")
    
    # Start polling
    application.run_polling()

if __name__ == "__main__":
    main()