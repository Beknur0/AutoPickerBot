import asyncio
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from handlers import q
from schedules import notifier

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    dp.include_routers(q.router)

    scheduler = AsyncIOScheduler(timezone="Asia/Yekaterinburg")

    scheduler.add_job(
        notifier.check_courses_availability_chenges, "interval", seconds=15, args=(bot,)
    )
    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
