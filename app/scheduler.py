from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from app.config import settings
from app.database import get_db, AdminState

scheduler = AsyncIOScheduler()

async def daily_job(bot: Bot):
    db = next(get_db())
    st = db.query(AdminState).first()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    if st.last_prompt_date == today:
        db.close()
        return 

    st.awaiting_menu_response = True
    st.last_prompt_date = today
    db.commit()
    
    await bot.send_message(settings.ADMIN_ID, "⏰ Hora de poner el menú de hoy!")
    
    # Recordatorio en 15 min
    scheduler.add_job(
        lambda: bot.send_message(settings.ADMIN_ID, "⚠️ Olvidaste el menú?"),
        'date', run_date=datetime.utcnow() + timedelta(minutes=15)
    )
    db.close()

def start(bot: Bot):
    scheduler.remove_all_jobs()
    h, m = map(int, settings.DAILY_PROMPT_TIME.split(':'))
    scheduler.add_job(daily_job, 'cron', hour=h, minute=m, args=[bot])
    scheduler.start()
