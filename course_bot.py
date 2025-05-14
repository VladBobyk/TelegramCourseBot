import logging
import os
import json
import time
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler

# Спроба імпортувати dotenv, продовжуємо, якщо не вдалося
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Якщо dotenv не встановлено, просто продовжуємо
    pass

# Отримання токену - використовуємо TELEGRAM_BOT_TOKEN як назву змінної
# для відповідності з іншими файлами проекту
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Перевірка наявності токену
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'TELEGRAM_BOT_TOKEN':
    # Спробуємо отримати токен з TOKEN (альтернативна назва змінної)
    TELEGRAM_BOT_TOKEN = os.getenv('TOKEN')
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("Не вдалося знайти токен бота. Перевірте змінні середовища.")

# URL додатку на Render - для підтримки активності
RENDER_APP_URL = os.getenv('RENDER_APP_URL', 'https://telegramcoursebot-18ir.onrender.com')

# Увімкнення логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфігурація
USER_DATA_FILE = 'user_data.json'

# Прапорець для контролю тестового режиму - встановіть False для нормальної роботи
TEST_MODE = False

# Відеоуроки з правильним кодуванням кирилиці та форматуванням
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
            {'file_id': 'BAACAgIAAyEFAASaGaDWAAMeaCNM2Q1tPOzDskUXmsxCs9PhHjgAAnd1AAK5ARhJo4zf7IIDr282BA', 
             'caption': ''}
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
             'caption': ''}
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
             'caption': ''}
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
        'post_bonus_text': "**ЗНИЖКА – 10 % ДЛЯ МОЇХ!** 🎁🎁🎁\nВ магазині [LianaNail Official Ukraine](https://www.instagram.com/lianail_official_ukraine/)\n\n**За моїм промокодом** **STELLA09**\n\n**Як скористатися знижкою** 🤔:\n1. Заходиш на сайт магазину, додаєш усе потрібне в кошик.\n2. Після оформлення з тобою зв'яжеться менеджер — просто скажи:\n\"**У мене є промокод STELLA09**\" — і знижку буде застосовано. ✅\n\nАбо:\n3. Пиши одразу в Instagram-магазин у дірект —\n**вкажи мій промокод STELLA09**, і менеджер оформить тобі знижку вручну. ✅\n\n**Роби красу — вигідно.**\n**Працюй з любов'ю.**"
    }
}

def load_user_data():
    """Завантаження даних користувачів з файлу"""
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Помилка при завантаженні даних користувачів: {e}")
    return {}

def save_user_data(data):
    """Збереження даних користувачів у файл"""
    try:
        # Створюємо директорію, якщо вона не існує
        os.makedirs(os.path.dirname(USER_DATA_FILE) or '.', exist_ok=True)
        
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Помилка при збереженні даних користувачів: {e}")

# Ініціалізація зберігання даних користувачів
user_data = load_user_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправити привітальне повідомлення та перший урок, коли видано команду /start"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    # Перевірка, чи користувач вже розпочав курс
    if user_id in user_data:
        await update.message.reply_text(f"З поверненням, {user_name}! Ваш курс вже розпочато.")
        return
    
    # Реєстрація нового користувача
    current_date = datetime.now().strftime('%Y-%m-%d')
    user_data[user_id] = {
        'name': user_name,
        'start_date': current_date,
        'current_day': 1,
        'last_lesson_date': current_date
    }
    save_user_data(user_data)
    
    # Відправити привітальне повідомлення з уроку 1
    await update.message.reply_text(
        LESSONS[1]['intro_message'],
        parse_mode='Markdown'
    )
    
    # Відправити перший урок
    await send_lesson(context.bot, user_id, 1)

async def send_lesson(bot, user_id: str, day: int) -> None:
    """Відправити конкретний урок користувачеві"""
    if day > 3:
        # Відправити бонусний контент
        await send_bonus(bot, user_id)
        return
    
    lesson = LESSONS[day]
    
    # Відправити вступне повідомлення, якщо це не перший день
    if day > 1 and 'intro_message' in lesson:
        await bot.send_message(
            chat_id=user_id,
            text=lesson['intro_message'],
            parse_mode='Markdown'
        )
    
    # Відправити кожне відео в уроці
    for video in lesson['videos']:
        try:
            await bot.send_video(
                chat_id=user_id,
                video=video['file_id'],
                caption=video['caption']
            )
        except Exception as e:
            logger.error(f"Помилка при відправці відео: {e}")
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"Не вдалося відправити відео. Спробуйте пізніше або зверніться до підтримки."
                )
            except:
                pass
    
    # Для дня 2 відправити спеціальні документи та повідомлення
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
                    logger.error(f"Помилка при відправці документа: {e}")
    
    # Оновити дані користувача
    user_data[user_id]['current_day'] = day
    user_data[user_id]['last_lesson_date'] = datetime.now().strftime('%Y-%m-%d')
    save_user_data(user_data)
    
    if day < 3:
        # Після уроків 1 і 2 показуємо кнопки для вибору дня наступного уроку
        keyboard = [
            [
                InlineKeyboardButton("Отримати наступний урок зараз", callback_data=f"next_now_{day+1}"),
            ],
            [
                InlineKeyboardButton("Завтра", callback_data=f"next_day_{day+1}"),
            ],
            [
                InlineKeyboardButton("Через 2 дні", callback_data=f"next_2days_{day+1}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await bot.send_message(
            chat_id=user_id, 
            text=f"Коли ви хочете отримати наступний урок?",
            reply_markup=reply_markup
        )
    else:
        # Після дня 3 показуємо кнопки для бонусу
        keyboard = [
            [
                InlineKeyboardButton("Отримати бонус зараз", callback_data="bonus_now"),
            ],
            [
                InlineKeyboardButton("Завтра", callback_data="bonus_day"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await bot.send_message(
            chat_id=user_id,
            text="Вітаємо! Ви завершили основну частину курсу! Коли ви хочете отримати бонусний матеріал?",
            reply_markup=reply_markup
        )

async def ask_for_time_selection(bot, user_id: str, lesson_day: int, selected_date: str):
    """Запитати користувача про вибір часу для отримання уроку"""
    # Клавіатура з варіантами часу
    keyboard = [
        [
            InlineKeyboardButton("Ранок (08:00)", callback_data=f"time_08_{lesson_day}_{selected_date}"),
            InlineKeyboardButton("День (12:00)", callback_data=f"time_12_{lesson_day}_{selected_date}"),
        ],
        [
            InlineKeyboardButton("Вечір (18:00)", callback_data=f"time_18_{lesson_day}_{selected_date}"),
            InlineKeyboardButton("Ніч (22:00)", callback_data=f"time_22_{lesson_day}_{selected_date}"),
        ],
        [
            InlineKeyboardButton("Скасувати", callback_data=f"cancel_{lesson_day}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await bot.send_message(
        chat_id=user_id,
        text=f"Оберіть бажаний час отримання уроку {lesson_day} ({selected_date}):",
        reply_markup=reply_markup
    )

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробка натискання кнопок для вибору часу отримання наступного уроку"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    callback_data = query.data
    
    # Перевірка, чи є користувач в базі даних
    if user_id not in user_data:
        await query.edit_message_text(
            text="Спочатку почніть курс за допомогою команди /start"
        )
        return
    
    if callback_data.startswith("next_now_"):
        # Користувач хоче отримати урок одразу
        lesson_day = int(callback_data.split("_")[2])
        await query.edit_message_text(text=f"Відправляємо вам урок {lesson_day} прямо зараз!")
        await send_lesson(context.bot, user_id, lesson_day)
    
    elif callback_data.startswith("next_day_"):
        # Користувач хоче отримати урок завтра
        lesson_day = int(callback_data.split("_")[2])
        selected_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        await query.edit_message_text(text=f"Ви обрали отримання уроку {lesson_day} завтра ({selected_date}). Тепер оберіть час:")
        await ask_for_time_selection(context.bot, user_id, lesson_day, selected_date)
    
    elif callback_data.startswith("next_2days_"):
        # Користувач хоче отримати урок через 2 дні
        lesson_day = int(callback_data.split("_")[2])
        selected_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        await query.edit_message_text(text=f"Ви обрали отримання уроку {lesson_day} через 2 дні ({selected_date}). Тепер оберіть час:")
        await ask_for_time_selection(context.bot, user_id, lesson_day, selected_date)
    
    elif callback_data.startswith("time_"):
        # Користувач обрав конкретний час
        parts = callback_data.split("_")
        hour = parts[1]
        lesson_day = int(parts[2])
        selected_date = parts[3]
        
        # Зберігаємо час у форматі HH:MM
        selected_time = f"{hour}:00"
        
        # Оновлюємо дані користувача
        user_data[user_id]["next_lesson_day"] = lesson_day
        user_data[user_id]["next_lesson_date"] = selected_date
        user_data[user_id]["next_lesson_time"] = selected_time
        save_user_data(user_data)
        
        await query.edit_message_text(
            text=f"Добре! Ви отримаєте урок {lesson_day} {selected_date} о {selected_time}."
        )
    
    elif callback_data.startswith("cancel_"):
        # Користувач скасував вибір часу
        lesson_day = int(callback_data.split("_")[1])
        await query.edit_message_text(
            text=f"Вибір часу скасовано. Ви можете обрати інший час за допомогою команди /next."
        )
    
    elif callback_data == "bonus_now":
        # Користувач хоче отримати бонус зараз
        await query.edit_message_text(text="Відправляємо вам бонусний матеріал прямо зараз!")
        await send_bonus(context.bot, user_id)
    
    elif callback_data == "bonus_day":
        # Користувач хоче отримати бонус завтра
        selected_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        await query.edit_message_text(text=f"Ви обрали отримання бонусу завтра ({selected_date}). Тепер оберіть час:")
        await ask_for_time_selection(context.bot, user_id, 4, selected_date)

async def check_and_send_scheduled_lessons():
    """Перевірити та відправити заплановані уроки з урахуванням часу"""
    try:
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M')
        
        # Створюємо новий екземпляр застосунку 
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        for user_id, data in user_data.items():
            # Пропустити користувачів, які завершили повний курс
            if data.get('completed', False):
                continue
                
            # Перевірка на заплановану дату та час наступного уроку
            if ("next_lesson_date" in data and 
                "next_lesson_time" in data and
                data["next_lesson_date"] <= current_date and
                data["next_lesson_time"] <= current_time):
                
                next_day = data.get("next_lesson_day", data['current_day'] + 1)
                try:
                    await send_lesson(app.bot, user_id, next_day)
                    # Видаляємо заплановані дані після відправки
                    for key in ["next_lesson_date", "next_lesson_time", "next_lesson_day"]:
                        if key in data:
                            del data[key]
                    save_user_data(user_data)
                    logger.info(f"Відправлено запланований урок {next_day} користувачу {user_id}")
                except Exception as e:
                    logger.error(f"Помилка при відправці уроку {next_day} користувачу {user_id}: {e}")
        
        await app.shutdown()
    except Exception as e:
        logger.error(f"Помилка при перевірці та відправці запланованих уроків: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправити повідомлення, коли видано команду /help"""
    await update.message.reply_text(
        "Цей бот відправить вам 3-денний міні-курс.\n\n"
        "Команди:\n"
        "/start - Почати курс\n"
        "/help - Показати це повідомлення\n"
        "/status - Перевірити ваш прогрес\n"
        "/next - Отримати наступний урок (якщо доступний)\n"
        "/bonus - Отримати бонусний матеріал (якщо доступний)\n"
        "/test_on - Включити тестовий режим (всі повідомлення відразу)\n"
        "/test_off - Виключити тестовий режим (стандартний режим)"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Перевірити статус курсу для цього користувача"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_data:
        await update.message.reply_text("Ви ще не почали курс. Використайте /start щоб почати.")
        return
    
    data = user_data[user_id]
    current_day = data['current_day']
    
    if data.get('completed', False):
        await update.message.reply_text("Ви повністю завершили курс, включаючи бонусний матеріал! Вітаємо!")
    elif current_day >= 3:
        if "next_lesson_date" in data and data.get("next_lesson_day") == 4:
            next_date = data["next_lesson_date"]
            await update.message.reply_text(
                f"Ви завершили основну частину курсу!\n"
                f"Ваш бонусний матеріал буде надіслано {next_date}.\n"
                f"Або скористайтесь командою /bonus, щоб отримати його зараз."
            )
        else:
            await update.message.reply_text(
                "Ви завершили основну частину курсу! Бонусний матеріал готовий для вас.\n"
                "Використайте /bonus щоб отримати його зараз."
            )
    else:
        if "next_lesson_date" in data:
            next_day = data.get("next_lesson_day", current_day + 1)
            next_date = data["next_lesson_date"]
            await update.message.reply_text(
                f"Ви на дні {current_day} курсу.\n"
                f"Ваш наступний урок (День {next_day}) заплановано на {next_date}.\n"
                f"Використайте /next щоб отримати його прямо зараз."
            )
        else:
            await update.message.reply_text(
                f"Ви на дні {current_day} курсу.\n"
                f"Використайте /next щоб отримати наступний урок."
            )

async def next_lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправити наступний урок на запит користувача"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_data:
        await update.message.reply_text("Ви ще не почали курс. Використайте /start щоб почати.")
        return
    
    data = user_data[user_id]
    current_day = data['current_day']
    
    if data.get('completed', False):
        await update.message.reply_text("Ви вже завершили весь курс, включаючи бонусний матеріал!")
    elif current_day >= 3:
        await update.message.reply_text(
            "Ви завершили основну частину курсу! Для отримання бонусного матеріалу використайте команду /bonus."
        )
    else:
        next_day = current_day + 1
        await update.message.reply_text(f"Відправляємо вам урок {next_day}...")
        await send_lesson(context.bot, user_id, next_day)

async def bonus_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправити бонусний контент негайно, якщо користувач завершив основний курс"""
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
    """Тестова команда для відправки всіх уроків одразу"""
    user_id = str(update.effective_user.id)
    
    # Зареєструвати користувача, якщо не існує
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
    
    # Відправити всі уроки з короткими затримками
    await update.message.reply_text("📚 Урок 1:")
    # Відправити вступ для уроку
    await send_lesson(context.bot, user_id, 1)
    await context.bot.send_message(chat_id=user_id, text="⏳ Затримка між уроками...")
    time.sleep(2)
    
    await context.bot.send_message(chat_id=user_id, text="📚 Урок 2:")
    await send_lesson(context.bot, user_id, 2)
    await context.bot.send_message(chat_id=user_id, text="⏳ Затримка між уроками...")
    time.sleep(2)
    
    await context.bot.send_message(chat_id=user_id, text="📚 Урок 3:")
    await send_lesson(context.bot, user_id, 3)
    await context.bot.send_message(chat_id=user_id, text="⏳ Затримка між уроками...")
    time.sleep(2)
    
    await context.bot.send_message(chat_id=user_id, text="🎁 Бонусний матеріал:")
    await send_bonus(context.bot, user_id)
    
    await context.bot.send_message(chat_id=user_id, text="✅ Тестування завершено. Всі уроки відправлено.")

async def test_mode_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Увімкнути тестовий режим"""
    global TEST_MODE
    TEST_MODE = True
    await update.message.reply_text("🧪 Тестовий режим увімкнено. Уроки будуть доступні без обмежень часу.")

async def test_mode_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Вимкнути тестовий режим"""
    global TEST_MODE
    TEST_MODE = False
    await update.message.reply_text("✅ Тестовий режим вимкнено. Бот працює у звичайному режимі.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробка звичайних повідомлень"""
    await update.message.reply_text(
        "Привіт! Я бот для курсу по бʼюті-освіті. Використайте /start щоб почати курс або /help для додаткової інформації."
    )

# Функція для регулярного пінгування застосунку, щоб запобігти "засинанню" на Render
def ping_server():
    """Пінгує застосунок, щоб запобігти засинанню на Render"""
    try:
        response = requests.get(RENDER_APP_URL)
        logger.info(f"Ping server response: {response.status_code}")
    except Exception as e:
        logger.error(f"Помилка при пінгуванні сервера: {e}")

# Функція для створення веб-сервера на Flask для підтримки активності бота
def setup_web_server():
    """Налаштування простого веб-сервера для підтримки активності на Render"""
    from flask import Flask
    
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "Telegram Course Bot is running!"
    
    @app.route('/health')
    def health():
        return "OK", 200
    
    # Запустити сервер у фоновому режимі
    import threading
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))).start()

def setup_scheduler():
    """Налаштування планувальника для щогодинної перевірки та відправки уроків"""
    scheduler = BackgroundScheduler()
    
    # Заплановати перевірку кожну годину для точнішої відправки за часом
    scheduler.add_job(
        check_and_send_scheduled_lessons,
        'cron',
        minute=0  # Перевіряємо на початку кожної години
    )
    
    # Додати задачу для пінгування сервера кожні 10 хвилин
    scheduler.add_job(
        ping_server,
        'interval',
        minutes=10
    )
    
    scheduler.start()
    logger.info("Планувальник запущено!")

def main() -> None:
    """Основна функція для запуску бота"""
    # Створюємо новий екземпляр застосунку
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Додаємо обробники команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("next", next_lesson_command))
    application.add_handler(CommandHandler("bonus", bonus_command))
    application.add_handler(CommandHandler("test", test_all_lessons))
    application.add_handler(CommandHandler("test_on", test_mode_on_command))
    application.add_handler(CommandHandler("test_off", test_mode_off_command))
    application.add_handler(CallbackQueryHandler(handle_button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаємо планувальник для щоденної перевірки та відправки уроків
    setup_scheduler()
    
    # Запускаємо веб-сервер для підтримки активності на Render
    setup_web_server()
    
    # Запускаємо бота
    application.run_polling()

if __name__ == "__main__":
    main()