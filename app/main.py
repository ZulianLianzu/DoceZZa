import sys
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.database import init_db
from app.bot import router as bot_router
from app.scheduler import start as start_sched

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
bot = Bot(token=settings.TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(bot_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_sched(bot)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "bot is running"}

@app.post(settings.WEBHOOK_PATH)
async def webhook(req: Request):
    if req.headers.get("X-Telegram-Bot-Api-Secret-Token") != settings.SECRET_TOKEN:
        return Response(status_code=403)
    try:
        update = types.Update(**(await req.json()))
        await dp.feed_update(bot, update)
    except Exception as e: logging.error(e)
    return Response(status_code=200)
