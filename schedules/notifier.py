import time
import json
import html
import os
from dotenv import load_dotenv

from bs4 import BeautifulSoup
from aiogram import Bot

import session
from schedules import picker

load_dotenv()

CHAT_ID = int(os.getenv("CHAT_ID"))

COURSES = [
    # 12
    # "INF 365",
    # 11
    "INF 414",

    # RTM
    "CSS 410",
    # MDE
    "MDE 160",

    # "INF 407",
    # "INF 431",
    # 10
    # "CSS 314",
    # 9
    # "INF 406",
]

# elective9 6540
# elective10 6580
# elective11 6541
# elective12 6488


async def normalize_time_format(raw_time: str) -> str | None:
    formated_time = raw_time
    if len(formated_time) <= 1:
        return None
    elif len(formated_time) >= 8 and len(formated_time) < 15:
        return f"{formated_time[:7]}, {formated_time[7:]}"
    elif len(formated_time) >= 15:
        return f"{formated_time[:7]}, {formated_time[7:14]}, {formated_time[14:]}"
    return formated_time


async def get_time():
    return time.strftime("%H:%M:%S %d.%m.%Y", time.localtime())


async def parse_courses_availablity(bot: Bot) -> dict[str, dict]:
    all_data = {}
    for i in range(len(COURSES)):
        timestamp = str(int(time.time() * 1000))
        payload = {
            "ajx": "1",
            "mod": "course_reg",
            "action": "ShowAvailableAllSections",
            "dk": COURSES[i],
            "pc": "10103",
            "py": "2023",
            "track": "TRACK0",
            "muf_sq_id": "",
            timestamp: "",
        }

        if "MDE 160" in COURSES[i]:
            del payload["muf_sq_id"]

        lectures: dict[str, list] = {}
        try:
            response = session.session.post(
                session.URL, data=payload, headers=session.HEADERS, timeout=15
            )
            data = json.loads(response.text)
            html_raw = data["DATA"]
            html_clean = html.unescape(html_raw)

            soup = BeautifulSoup(html_clean, "lxml")

            listt = []

            # Lecture
            table = soup.find("table", class_="clsTbl")
            rows = table.find_all("tr")[1:]

            for tr in rows:
                td = tr.find_all("td")
                qouta = td[5].get_text(strip=True)
                Ntime = td[9].get_text(strip=True)
                Nname = tr.get("name")

                listt.append([int(qouta), await normalize_time_format(Ntime), Nname])

            # Practice
            div = soup.select_one("div.hideDiv")
            rows = div.find_all("tr")[3:]

            for tr in rows:
                td = tr.find_all("td")
                id = td[0].get_text(strip=True)
                qouta = td[5].get_text(strip=True)
                count = td[6].get_text(strip=True)
                reserved = td[7].get_text(strip=True)
                available = int(qouta) - int(count) - int(reserved)
                Ptime = td[9].get_text(strip=True)
                Pname = tr.get("name")

                listt[0][0] -= int(qouta)

                lectures[id] = [
                    available,
                    await normalize_time_format(Ptime),
                    Pname,
                    listt[0][1],
                    listt[0][2],
                ]

                if listt[0][0] == 0:
                    listt.pop(0)

        except Exception as e:
            await bot.send_message(
                CHAT_ID, f"Parse course {COURSES[i]} availability erorr: {e}"
            )

        all_data[COURSES[i]] = lectures

    return all_data


async def check_courses_availability_chenges(bot: Bot):
    if not await session.login(bot=bot):
        return

    new_data: dict[str, dict[str, list]] = await parse_courses_availablity(bot)

    if len(new_data) == 0:
        await bot.send_message(CHAT_ID, f"New data parse error!")
        return

    file_path = "courses_availability_data.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = {}
                print(f"{await get_time()} Ошибка получение данных о квотах")
    else:
        data = {}
        await bot.send_message(CHAT_ID, f"Course availablity data file will be created")
        print(f"{await get_time()} Course availablity data file will be created")

    if len(data) != len(COURSES):
        for key in COURSES:
            data.setdefault(key, {})

    new_coutas: dict[str, dict] = {}
    for code, section in new_data.items():
        courses: dict[str, list] = {}
        if len(section) > 0:
            for id, listt in section.items():
                if listt[0] != 0:
                    if id not in data[code]:
                        await bot.send_message(
                            CHAT_ID, f"Added new coutas for course {code}"
                        )
                        print(f"{await get_time()} Added new coutas for course {code}")
                        courses[id] = listt
                        continue
                    if data[code][id][0] == 0:
                        await bot.send_message(
                            CHAT_ID,
                            f"New place for course {code} with Practice id: {id}",
                        )
                        print(
                            f"{await get_time()} New place for course {code} with Practice id: {id}"
                        )
                        courses[id] = listt
        if courses:
            new_coutas[code] = courses

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(new_data, file, indent=4, ensure_ascii=False)

    print(f"{await get_time()} Attempt!")

    if len(new_coutas) > 0:
        await picker.check_is_needable(bot, new_coutas)
