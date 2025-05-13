import logging
import os
import json
from server import keep_alive
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
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
            {'file_id': 'BAACAgIAAyEFAASaGaDWAAMWaB4BuTq41XAp90PnvmCB4hMTGL4AAhZsAAJ_NfBI39cIf7_aME02BA', 
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
    
    # Відправити вступне повідомлення, якщо це не перший день (вступ для першого дня відправляється в команді start)
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
            # Спробувати відправити повідомлення про помилку
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
        
        # Відправити документи
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
        await bot.send_message(
            chat_id=user_id, 
            text=lesson['completion_message'],
            parse_mode='Markdown'
        )
    else:
        # Після дня 3 відправити повідомлення про бонус
        await bot.send_message(
            chat_id=user_id,
            text="Вітаємо! Ви завершили міні-курс! Завтра ви отримаєте спеціальний бонус.",
            parse_mode='Markdown'
        )
        
        # Якщо в тестовому режимі, відразу відправити бонусний контент
        if TEST_MODE:
            await send_bonus(bot, user_id)

async def send_bonus(bot, user_id: str) -> None:
    """Відправити бонусний контент користувачеві"""
    bonus = LESSONS[4]
    
    # Спочатку відправити бонусне текстове повідомлення
    await bot.send_message(
        chat_id=user_id,
        text=bonus['bonus_text'],
        parse_mode='Markdown'
    )
    
    # Потім відправити бонусне відео(а)
    for video in bonus['videos']:
        try:
            await bot.send_video(
                chat_id=user_id,
                video=video['file_id'],
                caption=video['caption']
            )
        except Exception as e:
            logger.error(f"Помилка при відправці бонусного відео: {e}")
    
    # Відправити інформацію про знижку
    if 'post_bonus_text' in bonus:
        await bot.send_message(
            chat_id=user_id,
            text=bonus['post_bonus_text'],
            parse_mode='Markdown'
        )
    
    # Оновити статус користувача
    user_data[user_id]['current_day'] = 4
    user_data[user_id]['completed'] = True
    save_user_data(user_data)

async def check_and_send_daily_lessons():
    """Перевірити, чи користувачі повинні отримати свій наступний урок"""
    # Пропустити, якщо в тестовому режимі
    if TEST_MODE:
        return
        
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Створюємо новий екземпляр застосунку 
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        for user_id, data in user_data.items():
            # Пропустити користувачів, які завершили повний курс (включаючи бонус)
            if data.get('completed', False):
                continue
                
            last_lesson_date = datetime.strptime(data['last_lesson_date'], '%Y-%m-%d')
            next_lesson_date = last_lesson_date + timedelta(days=1)
            
            # Якщо час для наступного уроку
            if next_lesson_date.strftime('%Y-%m-%d') <= today and data['current_day'] <= 3:
                next_day = data['current_day'] + 1
                try:
                    await send_lesson(app.bot, user_id, next_day)
                    logger.info(f"Відправлено урок {next_day} користувачу {user_id}")
                except Exception as e:
                    logger.error(f"Помилка при відправці уроку {next_day} користувачу {user_id}: {e}")
        
        await app.shutdown()
    except Exception as e:
        logger.error(f"Помилка при перевірці та відправці щоденних уроків: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправити повідомлення, коли видано команду /help"""
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
    # Відправити вступ для уроку 1
    await update.message.reply_text(
        LESSONS[1]['intro_message'],
        parse_mode='Markdown'
    )
    await send_lesson(context.bot, user_id, 1)
    
    await update.message.reply_text("📚 Урок 2:")
    # Відправити вступ для уроку 2
    await update.message.reply_text(
        LESSONS[2]['intro_message'],
        parse_mode='Markdown'
    )
    await send_lesson(context.bot, user_id, 2)
    
    await update.message.reply_text("📚 Урок 3:")
    # Відправити вступ для уроку 3
    await update.message.reply_text(
        LESSONS[3]['intro_message'],
        parse_mode='Markdown'
    )
    await send_lesson(context.bot, user_id, 3)
    
    # Бонус відправляється автоматично після уроку 3 в тестовому режимі
    
    await update.message.reply_text("✅ Тестування завершено! Всі повідомлення відправлено.")

async def test_mode_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Увімкнути тестовий режим"""
    global TEST_MODE
    TEST_MODE = True
    await update.message.reply_text(
        "🔧 Тестовий режим УВІМКНЕНО!\n"
        "Тепер ви можете отримати всі уроки одразу командою /test_all\n"
        "Вимкнути тестовий режим: /test_off"
    )

async def test_mode_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Вимкнути тестовий режим"""
    global TEST_MODE
    TEST_MODE = False
    await update.message.reply_text(
        "🔧 Тестовий режим ВИМКНЕНО!\n"
        "Бот працює в звичайному режимі - один урок на день."
    )

def main() -> None:
    """Запустити бота"""
    try:
        # Перевірка токену ще раз для впевненості
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'TELEGRAM_BOT_TOKEN':
            logger.error("Токен бота не знайдено або він неправильний. Перевірте змінні середовища.")
            raise ValueError("Неправильний токен бота")
            
        # Створити Application та передати токен бота
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Зареєструвати обробники команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("bonus", bonus_command))
        
        # Тестові команди
        application.add_handler(CommandHandler("test_all", test_all_lessons))
        application.add_handler(CommandHandler("test_on", test_mode_on))
        application.add_handler(CommandHandler("test_off", test_mode_off))

        # Налаштувати планувальник для щоденних уроків
        scheduler = BackgroundScheduler()
        scheduler.add_job(check_and_send_daily_lessons, 'interval', hours=1)  # Перевіряти кожну годину
        scheduler.start()
        
        # Обробка налаштувань webhook та polling для розгортання Render
        PORT = int(os.environ.get('PORT', 10000))
        
        # Правильне отримання URL для вебхука з середовища
        WEBHOOK_URL = os.environ.get('https://telegramcoursebot-18ir.onrender.com')

        if WEBHOOK_URL:
            logger.info(f"Запуск webhook на порту {PORT} з URL {WEBHOOK_URL}")
            application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=TELEGRAM_BOT_TOKEN,
                webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
            )
        else:
            logger.info("URL вебхука не знайдено, запуск в режимі polling")
            keep_alive()
            application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Помилка при запуску бота: {e}")
        raise

if __name__ == '__main__':
    main()