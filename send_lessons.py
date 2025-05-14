# ����: send_lessons.py
import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from telegram.ext import Application

# ������������ ���������
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ��������� ������
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = os.getenv('TOKEN')
    if not TELEGRAM_BOT_TOKEN:
        logger.error("�� ������� ������ ����� ����. �������� ���� ����������.")
        sys.exit(1)

# ��������� ��� ����� ����� ������������
USER_DATA_FILE = 'user_data.json'

def load_user_data():
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"������� ��� ����������� ����� ������������: {e}")
    return {}

async def check_and_send_scheduled_lessons():
    from course_bot import send_lesson, send_bonus  # ��������� ������� � ��������� ����� ����
    
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        user_data = load_user_data()
        
        # ��������� ����� ��������� ���������� 
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        for user_id, data in user_data.items():
            # ���������� ������������, �� ��������� ������ ����
            if data.get('completed', False):
                continue
                
            # �������� �� ����������� ���� ���������� �����
            if "next_lesson_date" in data and data["next_lesson_date"] <= today:
                next_day = data.get("next_lesson_day", data['current_day'] + 1)
                try:
                    if next_day <= 3:
                        await send_lesson(app.bot, user_id, next_day)
                    else:
                        await send_bonus(app.bot, user_id)
                    
                    # ��������� ����������� ���� ���� ��������
                    if "next_lesson_date" in data:
                        del data["next_lesson_date"]
                    if "next_lesson_day" in data:
                        del data["next_lesson_day"]
                    
                    # �������� ������� ���
                    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
                        json.dump(user_data, f, ensure_ascii=False)
                        
                    logger.info(f"³��������� ������������ ���� {next_day} ����������� {user_id}")
                except Exception as e:
                    logger.error(f"������� ��� �������� ����� {next_day} ����������� {user_id}: {e}")
        
        await app.shutdown()
    except Exception as e:
        logger.error(f"������� ��� �������� �� �������� ������������ �����: {e}")

if __name__ == "__main__":
    asyncio.run(check_and_send_scheduled_lessons())
"""