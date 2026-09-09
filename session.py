import os
import html
import re
import time
from dotenv import load_dotenv

import requests
import email
from email.header import decode_header
import imaplib

from aiogram import Bot
from aiogram.types import Message

load_dotenv()

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

EMAIL = os.getenv("EMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")

URL = "https://my.sdu.edu.kz/index.php"
VERIFICATION_URL = "https://my.sdu.edu.kz/verification.php"

CHAT_ID = int(os.getenv("CHAT_ID"))

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://my.sdu.edu.kz",
    "Referer": "https://my.sdu.edu.kz/index.php",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

login_data = {
    "username": USERNAME,
    "password": PASSWORD,
    "modstring": "",
    "LogIn": " Log in ",
}

session = requests.Session()
session.headers.update(HEADERS)


async def is_loged_in():
    try:
        response = session.get(URL, timeout=10)
        html_clean = html.unescape(response.text)
        if "access my account" in html_clean:
            return False
        return True
    except:
        return "Error"


async def is_confirm_pressed() -> bool | None:
    try:
        response = session.get(f"{URL}?mod=course_reg", timeout=10)
        if response.status_code == 200:
            if "Cancel registration" in response.text:
                return True
            else:
                return False
        else:
            print(
                f"Get data about course reg state page statues code {response.status_code}"
            )
    except Exception as e:
        print(f"Get data about course reg state page Error {e}")


async def login_to_site():
    try:
        response = session.post(URL, data=login_data, timeout=10)
        response.raise_for_status()  # Вызовет ошибку, если статус ответа 4xx или 5xx

        if "incorrect" in response.text or "Login or password" in response.text:
            print("Ошибка: Неверный логин или пароль")
            return "False"

        return response.url
    except Exception as e:
        print(f"Ошибка сети при логине: {e}")
        return "False"


async def get_otp_code():
    # Отправитель, от которого нужно найти последнее письмо
    TARGET_SENDER = "tfa@sdu.edu.kz"

    # 1. Подключаемся и авторизуемся
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, EMAIL_PASSWORD)
    mail.select("INBOX")

    # 2. Ищем письма по отправителю (критерий FROM)
    # Обратите внимание на синтаксис: строка запроса передается в кавычках
    search_criteria = f'(FROM "{TARGET_SENDER}")'
    status, messages = mail.search(None, search_criteria)

    if status != "OK" or not messages[0]:
        print(f"Писем от {TARGET_SENDER} не найдено.")
        mail.logout()
        exit()

    # 3. Получаем список ID и берем последнее (самое свежее)
    mail_ids = messages[0].split()
    latest_email_id = mail_ids[-1]

    # 4. Загружаем письмо по ID
    res, msg_data = mail.fetch(latest_email_id, "(RFC822)")

    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])

            # Декодируем тему
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")

            from_ = msg.get("From")

            # Читаем текст
            if msg.is_multipart():
                for part in msg.walk():
                    if (
                        part.get_content_type() == "text/plain"
                        and "attachment" not in str(part.get("Content-Disposition"))
                    ):
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

    # 5. Закрываем соединение
    mail.logout()

    # Ищем 6 цифр подряд (или можно использовать более общий паттерн для цифр)
    # \d{6} означает «ровно 6 цифр подряд»
    match = re.search(r"\d{6}", body)
    if match:
        otp_code = match.group(0)
        return int(otp_code)
    else:
        return 0


async def verificate():
    time.sleep(5)
    code = await get_otp_code()

    if code == 0:
        return False

    payload = {
        "code": f"{code}",
        "LogIn": "",
    }
    response = session.post(VERIFICATION_URL, data=payload, timeout=15)
    return True


async def login(message: Message = None, bot: Bot = None):
    login_response = await is_loged_in()
    if isinstance(login_response, bool) and not login_response:
        resp = await login_to_site()
        if "verification" in resp:
            if not await verificate():
                if message:
                    await message.answer("Verification Error!")
                else:
                    await bot.send_message(CHAT_ID, "Verification Error!")
                return False
        elif "False" == resp:
            if message:
                await message.answer("Login Error!")
            else:
                await bot.send_message(CHAT_ID, "Login Error!")
            return False
    elif login_response == "Error":
        if message:
            await message.answer("Is loged in Error!")
        else:
            await bot.send_message(CHAT_ID, "Is loged in Error!")
        return False
    return True
