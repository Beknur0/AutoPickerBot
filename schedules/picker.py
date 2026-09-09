import json
import time
import html
import os
from dotenv import load_dotenv

from aiogram import Bot
from bs4 import BeautifulSoup, Tag

import session

load_dotenv()

USERNAME = int(os.getenv("USERNAME"))
CHAT_ID = int(os.getenv("CHAT_ID"))

NEEDABLE: dict[str, dict[str, list | str]] = {
    "INF 414": {"ids": ["2"], "replacement": "INF 407"},
    "CSS 410": {"ids": ["1", "2"], "replacement": "CSS 410"},
    # "MDE 160": {"ids": ["8", "5", "6", "1", "2", "3", "4", "7"], "replacement": ""},
    # "INF 407": {"ids": ["1"], "replacement": "INF 407"},
    # "INF 365": {"ids": ["2"], "replacement": "INF 365"},
    # "CSS 314": {"ids": ["6", "4"], "replacement": "CSS 314"},
}

ELECTIVE_SQ: dict[str, int] = {
    # 9
    "INF 406": 6540,
    # 10
    "INF 360": 6580,
    "CSS 314": 6580,
    # 11
    "INF 414": 6541,
    "INF 407": 6541,
    "INF 431": 6541,
    # 12
    "INF 415": 6488,
    "INF 365": 6488,
    "INF 429": 6488,
}


async def is_td_free(td: Tag, code: str) -> bool:
    div = td.find("div")
    if div:
        if NEEDABLE[code]["replacement"] in div.get_text(strip=True):
            return True
        else:
            return False
    else:
        return True


async def is_course_matches(bot: Bot, code: str, Ptime: str, Ntime: str) -> bool:
    try:
        response = session.session.get(f"{session.URL}?mod=course_reg", timeout=10)
        html_clean = html.unescape(response.text)
        soup = BeautifulSoup(html_clean, "lxml")

        table = soup.find_all("table")[6]
        if not Ptime:
            raw_list = [Ntime]
        elif not Ntime:
            raw_list = [Ptime]
        else:
            raw_list = [Ptime, Ntime]
        result = [item.strip() for sub in raw_list for item in sub.split(",")]

        for i in result:
            td = table.select_one(f"td[id*='{i}']")
            if not await is_td_free(td, code):
                return False
        return True

    except Exception as e:
        await bot.send_message(CHAT_ID, f"Course {code} matches check Error {e}")


async def is_still_available(bot: Bot, code: str, id: str) -> bool:
    timestamp = str(int(time.time() * 1000))
    payload = {
        "ajx": "1",
        "mod": "course_reg",
        "action": "ShowAvailableAllSections",
        "dk": code,
        "pc": "10103",
        "py": "2023",
        "track": "TRACK0",
        "muf_sq_id": "",
        timestamp: "",
    }
    if "MDE 160" in code:
        del payload["muf_sq_id"]

    try:
        response = session.session.post(
            session.URL, data=payload, headers=session.HEADERS, timeout=15
        )
        data = json.loads(response.text)
        html_raw = data["DATA"]
        html_clean = html.unescape(html_raw)

        soup = BeautifulSoup(html_clean, "lxml")

        div = soup.select_one("div.hideDiv")
        rows = div.find_all("tr")[3:]
        td = rows[int(id)-1].find_all("td")
        avilable = (
            int(td[5].get_text(strip=True))
            - int(td[6].get_text(strip=True))
            - int(td[7].get_text(strip=True))
        )

        if avilable > 0:
            return True
        else:
            return False

    except Exception as e:
        await bot.send_message(
            CHAT_ID, f"Is course {code} still available checking Error {e}"
        )


async def drop_course(bot: Bot, code: str):
    try:
        response = session.session.get(f"{session.URL}?mod=course_reg", timeout=10)
        html_clean = html.unescape(response.text)

        soup = BeautifulSoup(html_clean, "lxml")

        divs = soup.find_all(
            lambda tag: tag.name == "div"
            and tag.get("class") == ["inbasket"]
            and code in tag.text
        )
        old_names_set = set()
        for div in divs:
            old_names_set.add(int(div.get("name")))
        old_names_list = list(old_names_set)

        table = soup.find_all("table", class_="clsTbl")[1]
        rows = table.find_all("tr")[1:-4]

        for tr in rows:
            td = tr.find_all("td")
            course = td[1].get_text(strip=True)
            if course == code:
                href = td[10].find("a").get("href")
                params = {
                    "mod": "course_reg",
                    "a": "DropCourse",
                    "id": 928,
                    "did": href[-7:],
                }
                response = session.session.get(
                    session.URL, params=params, headers=session.HEADERS
                )
                if response.status_code == 200:
                    await bot.send_message(
                        CHAT_ID, f"Course {code} droped successfully"
                    )
                return old_names_list
        await bot.send_message(CHAT_ID, f"Can't find the course {code} to drop it")
        return False
    except Exception as e:
        await bot.send_message(CHAT_ID, f"Course {code} drop Error {e}")
        return False


async def pick_course(bot: Bot, code: str, Pname: str, Nname: str):
    if NEEDABLE[code]["replacement"]:
        old_names: list[int] | bool = await drop_course(
            bot, NEEDABLE[code]["replacement"]
        )
        if not old_names:
            return

    timestamp = str(int(time.time() * 1000))

    payload = {
        "ajx": "1",
        "mod": "course_reg",
        "action": "AddCourse",
        "tid": 928,
        "stud": USERNAME,
        "secN": Nname,
        "secP": Pname,
        "secL": "",
        "secSQ": ELECTIVE_SQ[code] if code in ELECTIVE_SQ else "",
        "derskod": code,
        timestamp: "",
    }

    try:
        for _ in range(3):
            response = session.session.post(
                session.URL, data=payload, headers=session.HEADERS, timeout=15
            )
        if response.status_code == 200:
            await bot.send_message(
                CHAT_ID,
                f"Course {code} picked successfully. \nLecture: {Nname} \nPractice: {Pname}",
            )
    except Exception as e:
        await bot.send_message(CHAT_ID, f"Course {code} pick Error {e}")

    if NEEDABLE[code]["replacement"]:
        old_names.sort()
        payload2 = {
            "ajx": "1",
            "mod": "course_reg",
            "action": "AddCourse",
            "tid": 928,
            "stud": USERNAME,
            "secN": old_names[0],
            "secP": old_names[1],
            "secL": "",
            "secSQ": ELECTIVE_SQ[code] if code in ELECTIVE_SQ else "",
            "derskod": NEEDABLE[code]["replacement"],
            timestamp: "",
        }

        try:
            for _ in range(3):
                response = session.session.post(
                    session.URL, data=payload2, headers=session.HEADERS, timeout=15
                )
        except Exception as e:
            await bot.send_message(CHAT_ID, f"Old course pick Error {e}")

        return True


async def press_cancel(bot: Bot):
    try:
        timestamp = str(int(time.time() * 1000))
        payload = {
            "ajx": 1,
            "mod": "course_reg",
            "action": "StudentCancelConfirmedReg",
            "tid": 928,
            "stud": USERNAME,
            timestamp: ""
        }
        response = session.session.post(session.URL, headers=session.HEADERS, data=payload)
        if response.status_code == 200:
            await bot.send_message(CHAT_ID, f"Cancel pressed successfully!")
            return True
    except Exception as e:
        await bot.send_message(CHAT_ID, f"Cancel press Error {e}")


async def press_confirm(bot: Bot):
    try:
        timestamp = str(int(time.time() * 1000))
        payload = {
            "ajx": 1,
            "mod": "course_reg",
            "action": "StudConfirm",
            "tid": 928,
            "stud": USERNAME,
            timestamp: ""
        }
        response = session.session.post(session.URL, headers=session.HEADERS, data=payload)
        if response.status_code == 200:
            await bot.send_message(CHAT_ID, f"Confirm pressed successfully!")
            return True
    except Exception as e:
        await bot.send_message(CHAT_ID, f"Confirm press Error {e}")



async def check_is_needable(bot: Bot, new_coutas: dict[str, dict]):
    is_reg_confirmed = await session.is_confirm_pressed()

    if is_reg_confirmed:
        await press_cancel(bot)

    for code, section in new_coutas.items():
        if code in NEEDABLE:
            for id in NEEDABLE[code]["ids"]:
                if id in section:
                    await bot.send_message(
                        CHAT_ID,
                        f"Check if the course {code} with pracitce id {id} fits to schedule",
                    )
                    is_matches = await is_course_matches(
                        bot, code, section[id][1], section[id][3]
                    )
                    if is_matches:
                        await bot.send_message(
                            CHAT_ID,
                            f"Checking is that course {code}.{id} still available",
                        )
                        is_available = await is_still_available(bot, code, id)
                        if is_available:
                            if await pick_course(
                                bot, code, section[id][2], section[id][4]
                            ):
                                break
                        elif is_available == False:
                            bot.send_message(
                                CHAT_ID, f"Course {code}.{id} already taken"
                            )
                    elif is_matches == False:
                        bot.send_message(CHAT_ID, f"Course {code}.{id} desn't match")

    if is_reg_confirmed:
        await press_confirm(bot)

    print(f"{time.strftime("%H:%M:%S %d.%m.%Y", time.localtime())} Auto Pick Attempt!")