import os
import time
import json
import html
from dotenv import load_dotenv

from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command, CommandObject
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

import session

router = Router()

load_dotenv()


@router.message(Command("q"))
async def q(
    message: Message,
    command: CommandObject,
):
    if command.args is None:
        await message.answer("Write the Course code")
        return

    if len(command.args) == 7 and len(command.args.split(" ")[0]) == 3:
        pass
    else:
        await message.answer("Write the correct Course code")
        return

    if not await session.login(message=message):
        return

    timestamp = str(int(time.time() * 1000))

    payload = {
        "ajx": "1",
        "mod": "course_reg",
        "action": "ShowAvailableAllSections",
        "dk": command.args,
        "pc": "10103",
        "py": "2023",
        "track": "TRACK0",
        "muf_sq_id": 6488,
        timestamp: "",
    }

    if command.args == "MDE 160":
        del payload["muf_sq_id"]

    try:
        response_grades = session.session.post(session.URL, data=payload, timeout=15)

        if response_grades.status_code != 200:
            await message.answer(
                f"Get sections Error! /n Status code: {response_grades.status_code}"
            )

        data = json.loads(response_grades.text)
        html_raw = data["DATA"]
        html_clean = html.unescape(html_raw)
        html_visible = html_clean.replace(
            "display: none", "display: table-row"
        ).replace("display:none", "display:block")

        soup = BeautifulSoup(html_visible, "lxml")

        not_open_flag = False
        if "is not open for your program" in html_visible:
            not_open_flag = True

        if not not_open_flag:
            listt = []

            table = soup.select_one("table.clsTbl")
            rows = table.find_all("tr")[1:]
            for i in range(len(rows)):
                if i % 2 == 0:
                    rows[i]["style"] = "background-color: lightskyblue;"
                td = rows[i].find_all("td")
                qouta = td[5].get_text(strip=True)
                listt.append(int(qouta))
                td[-1].string = rows[i].get("name")

            div = soup.select_one("div.hideDiv")
            rows = div.find_all("tr")[3:]

            flag = True
            for tr in rows:
                if flag:
                    tr["style"] = "background-color: lightskyblue;"
                td = tr.find_all("td")
                qouta = td[5].get_text(strip=True)
                listt[0] -= int(qouta)
                td[-1].string = tr.get("name")

                if listt[0] == 0:
                    if flag:
                        flag = False
                    else:
                        flag = True
                    listt.pop(0)

        filename = f"{command.args}.html"
        image_filename = f"{command.args}.png"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(soup.prettify())

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1200, "height": 800})

            await page.goto(f"file://{os.path.abspath(filename)}")

            # Ждём, пока страница полностью загрузится
            await page.wait_for_load_state("networkidle")

            # Скриншот всей страницы
            await page.screenshot(path=image_filename, full_page=True)

            await browser.close()

        await message.answer_photo(FSInputFile(image_filename), caption=command.args)

        if os.path.exists(filename):
            os.remove(filename)

        if os.path.exists(image_filename):
            os.remove(image_filename)

    except Exception as e:
        await message.answer(f"Error: {e}", parse_mode=None)
