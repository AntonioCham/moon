from __future__ import annotations

import sqlite3
import re
from pathlib import Path
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from zipfile import ZipFile


SCRIPT_ROLE_ORDER = ["何聽雨", "李克", "馬蓓蓓", "高析羽", "陳宏", "範仁"]
SCRIPT_STAGE_ORDER = [
    ("第一幕", 1),
    ("第二幕", 2),
    ("第三幕", 3),
    ("第四幕", 4),
    ("第五幕", 5),
    ("結局", 6),
]
SCRIPT_DOCX_BASE = Path.home() / "Downloads" / "月光下的持刀者" / "劇本"
DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_docx_paragraphs(path: Path) -> list[str]:
    with ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", DOCX_NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", DOCX_NS)).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def load_external_scripts() -> dict[str, list[tuple[int, str, str]]] | None:
    scripts_by_role: dict[str, list[tuple[int, str, str]]] = {role: [] for role in SCRIPT_ROLE_ORDER}
    for stage_name, act in SCRIPT_STAGE_ORDER:
        for role in SCRIPT_ROLE_ORDER:
            path = SCRIPT_DOCX_BASE / stage_name / f"{stage_name} {role}.docx"
            if not path.exists():
                return None
            paragraphs = read_docx_paragraphs(path)
            if len(paragraphs) < 2:
                return None
            scripts_by_role[role].append((act, paragraphs[0], "\n\n".join(paragraphs[1:]).strip()))
    return scripts_by_role


def init_db(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passkey TEXT UNIQUE NOT NULL,
            role_name TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS game_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_act INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            act INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS web_clues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act INTEGER NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            snippet TEXT NOT NULL,
            keywords TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act INTEGER NOT NULL,
            username TEXT NOT NULL,
            display_name TEXT NOT NULL,
            content TEXT NOT NULL,
            posted_at TEXT NOT NULL,
            reply_content TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS chat_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            intro TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            act INTEGER NOT NULL,
            trigger_keywords TEXT NOT NULL,
            response_text TEXT NOT NULL,
            FOREIGN KEY(contact_id) REFERENCES chat_contacts(id)
        );
        """
    )

    user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    tweet_columns = [row[1] for row in cursor.execute("PRAGMA table_info(tweets)").fetchall()]
    if "reply_content" not in tweet_columns:
        cursor.execute(
            "ALTER TABLE tweets ADD COLUMN reply_content TEXT NOT NULL DEFAULT ''"
        )

    if user_count == 0:
        users = [
            ("001", "何聽雨", 0),
            ("002", "李克", 0),
            ("003", "馬蓓蓓", 0),
            ("004", "高析羽", 0),
            ("005", "陳宏", 0),
            ("006", "範仁", 0),
            ("8888", "管理員", 1),
        ]
        cursor.executemany(
            "INSERT INTO users (passkey, role_name, is_admin) VALUES (?, ?, ?)",
            users,
        )

        user_rows = cursor.execute(
            "SELECT id, role_name FROM users WHERE is_admin = 0 ORDER BY passkey"
        ).fetchall()

        imported_scripts = load_external_scripts()
        script_templates = {
            1: "第一幕：你接到一通來自吳銘的電話，他聲稱自己失憶了，希望你講出自己知道的故事，幫助他找回真相。",
            2: "第二幕：你開始從吳銘留下的隻字片語與線索中拼湊事件，並意識到每個人都在隱瞞過去。",
            3: "第三幕：你發現旅途中最顯而易見的細節，往往正是被忽略的關鍵。",
            4: "第四幕：你逐步看見所有人故事交纏的方式，也更接近那些幽暗歲月中的真相。",
            5: "第五幕：隨著真相逼近，你不得不重新審視自己、吳銘以及所有人背負的命運。",
            6: "結局：旅程並未真正結束，每個人都將帶著自己的答案走向不同的前路。",
        }
        for user in user_rows:
            role_name = user["role_name"]
            role_scripts = imported_scripts.get(role_name) if imported_scripts else None
            if role_scripts:
                iterable = role_scripts
            else:
                iterable = [
                    (
                        act,
                        f"第 {act} 幕",
                        (
                            f"{base_content}\n\n"
                            f"角色補充：{role_name} 對這一幕的直覺反應與其他人不同，"
                            "請留意自己曾否在晚宴前後離開大廳。"
                        ),
                    )
                    for act, base_content in script_templates.items()
                ]
            for act, title, content in iterable:
                cursor.execute(
                    """
                    INSERT INTO scripts (user_id, act, title, content)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user["id"], act, title, content),
                )

        cursor.executemany(
            """
            INSERT INTO web_clues (act, title, url, snippet, keywords)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    1,
                    "信科互聯網公司網站",
                    "https://moon.local/search/a1-1",
                    "2018年7月15日，陳宏、吳銘兩人攻克技術難關，超標準完成項目，他們兩兄弟齊頭並進，希望他們下一季度再創輝煌。",
                    "陳宏 互聯網公司 信科 吳銘",
                ),
                (
                    1,
                    "信科互聯網公司網站",
                    "https://moon.local/search/a1-2",
                    "2021年1月25日，陳宏總經理對下一季度的工作制定了新的目標，並且進行了部署，相信在總經理的帶領下公司能夠再創佳績。",
                    "陳宏 互聯網公司 信科 總經理",
                ),
                (
                    1,
                    "信科互聯網公司官網",
                    "https://moon.local/search/a1-3",
                    "聯繫我們（服務熱線）00136583。",
                    "陳宏 互聯網公司 官網 熱線 00136583",
                ),
                (
                    1,
                    "CLUB酒吧",
                    "https://moon.local/search/a2-1",
                    "營業時間18:00--4:00，訂座請致電00167999。",
                    "CLUB酒吧 酒吧 00167999",
                ),
                (
                    1,
                    "弗里餐廳(人民廣場店)",
                    "https://moon.local/search/a3-1",
                    "營業時間11:00--22:00，訂座請致電00169922。",
                    "弗里餐廳 弗里 人民廣場店 00169922",
                ),
                (
                    1,
                    "弗里餐廳(千百貨店)",
                    "https://moon.local/search/a3-2",
                    "營業時間11:00--22:00，訂座請致電00169933。",
                    "弗里餐廳 弗里 千百貨店 00169933",
                ),
                (
                    1,
                    "何聽雨心理診所",
                    "https://moon.local/search/a5-1",
                    "何聽雨心理診所是由一批海歸心理咨詢領域專家組建的心理咨詢機構，為您提供心理咨詢服務。咨詢客服熱線00130464。",
                    "何聽雨 心理醫生 心理診所 00130464",
                ),
                (
                    1,
                    "淮陰市日報",
                    "https://moon.local/search/a5-2",
                    "淮陰市日報2019年3月13日報道，對於早前給患者開過量鎮定劑藥物而受到處罰一事，何聽雨心理醫生表示今後一定反思自己，改正錯誤，也請社會廣大群眾監督。",
                    "何聽雨 心理醫生 淮陰市日報 鎮定劑 處方藥",
                ),
                (
                    1,
                    "淮陰實驗中學簡介",
                    "https://moon.local/search/a7-1",
                    "淮陰實驗中學，1998年成立，是一所由淮陰市教育局主管的十二年一貫制民辦學校，是淮陰市一級學校、國家級示範性普通高中。",
                    "淮陰(市)實驗中學 淮陰實驗中學 學校",
                ),
                (
                    1,
                    "合德大學",
                    "https://moon.local/search/a8-1",
                    "合德大學網站2018年12月28日報道，合德大學愛心助力通道自2008年開通至今，已經幫助了近千名家庭貧困或者是身患疾病的學生。可通過電話00164488聯繫負責老師。",
                    "合德大學 00164488 愛心助力通道",
                ),
                (
                    1,
                    "無憂律師事務所",
                    "https://moon.local/search/a9-1",
                    "專注法律服務，李克律師、XX律師、XX律師等專業律師非訴及訴訟經驗豐富，專門處理疑難雜件，案件收費公開透明。詳情請咨詢00139002。",
                    "無憂律師事務所 李克律師 00139002",
                ),
                (
                    1,
                    "2020年4月1日淮陰市新聞",
                    "https://moon.local/search/a9-2",
                    "針對馬雲溪心理診所醫療效果無效的起訴，作為被告的辯護律師，李克律師表示一定會最大程度保障委托人的利益，李律師曾負責多起相關類型的案件，在這方面比較有經驗。",
                    "無憂律師事務所 李克律師 淮陰市新聞 馬雲溪",
                ),
                (
                    1,
                    "雀仔麻將館",
                    "https://moon.local/search/a12-1",
                    "營業時間12:00--22:00，訂座請致電00168888。",
                    "雀仔麻將館 00168888 麻將館",
                ),
                (
                    1,
                    "器質性心臟病 駕駛證",
                    "https://moon.local/search/a13-1",
                    "1、有器質性心臟病、癲癇病、美尼爾氏癥、眩暈癥、癔病、震顫麻痹、精神病、癡呆以及影響肢體活動的神經系統疾病等妨礙安全駕駛疾病的；2、吸食、注射毒品、長期服用依賴性精神藥品成癮尚未戒除的；3、吊銷機動車駕駛證未滿二年的；4、造成交通事故後逃逸被吊銷機動車駕駛證的；5、駕駛許可依法被撤銷未滿三年的；",
                    "器質性心臟病 駕駛證",
                ),
                (
                    1,
                    "淮陰市日報",
                    "https://moon.local/search/a16-1",
                    "淮陰市日報2014年5月報道，近期，我市警方在特聘刑偵顧問的幫助下，破獲多起案伴，將多名在逃多年的犯罪分子拘捕，正應了那句“天網恢恢疏而不漏”。由於警方不肯透露這位刑偵顧問的姓名和身份，因其斷案如神乎，市民都稱他為“無名神探”。",
                    "無名神探 淮陰市日報 刑偵顧問",
                ),
                (
                    1,
                    "淮陰市日報",
                    "https://moon.local/search/a16-2",
                    "淮陰市日報2019年1月報道，市民們注意到，曾經名噪一時的“無名神探”已經沉寂許久，目前網上有消息稱其不過是警方自編自導的騙局，也有消息稱其可能遇害。記者對此向警方求證時，警方表示目前網上言論皆為謠傳。",
                    "無名神探 淮陰市日報 謠傳",
                ),
                (
                    1,
                    "硝酸酯類藥物",
                    "https://moon.local/search/a17-1",
                    "硝酸酯類藥物臨床上常見的有硝酸甘油等，臨床上主要用於減少心肌需氧量，起到緩解心臟病患者心絞痛和抗缺血的作用。",
                    "硝酸酯類藥物 硝酸甘油 心臟病",
                ),
                (
                    1,
                    "福定西",
                    "https://moon.local/search/a18-1",
                    "一種近年來新研制的鎮靜類藥物，常用於治療精神類疾病。其鎮靜功效顯著，但其用量需要謹慎把握，近年來也出現多起福定西服用不當而造成患者死亡或失憶的情況，因此該藥物的使用和監管上一直存在較大爭議。",
                    "福定西 鎮靜類藥物 精神類疾病",
                ),
                (
                    1,
                    "孤兒院",
                    "https://moon.local/search/a19-1",
                    "本市共有三所孤兒院，承擔對孤兒、棄嬰等兒童的救助教育工作。結婚多年，並經區縣一級醫院確認一方無生育能力才可直接前往市孤兒院申請辦理領養登記手續。經院方審核後即可待領。",
                    "孤兒院 領養 棄嬰",
                ),
            ],
        )

        cursor.executemany(
            """
            INSERT INTO tweets (act, username, display_name, content, posted_at, reply_content)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "高析羽", "高析羽", "如果有一天，你發現你的好朋友可能犯了不可饒恕的錯誤，你會怎麼做？", "2021年11月1日", ""),
                (1, "高析羽", "高析羽", "今天拘捕了一個人，涉嫌非法侵犯他人隱私，他說他是什麼私家偵探。據說是匿名人出高價委托他調查當年的案件，已經查出了一些線索。或許是天意，老頭，你到死都記掛的事情，終於有眉目了…", "2021年10月28日", ""),
                (1, "高析羽", "高析羽", "哎，12年了，每年都要拿出來看一次，老頭，想你了。\n\n[附圖：父親手寫信照片]", "2020年12月1日", ""),
                (1, "何聽雨-心理醫生", "何聽雨-心理醫生", "不知不覺已經12年了，想你，我的妹妹，醫人難醫己。", "2021年3月27日", "@鳴: 何醫生加油！\n@盼得天明: 何醫生怎麼了？\n@發條橙: 何醫生，你以前是淮陰實驗的嗎？我好像見過你，我是你的學妹！\n@路人回覆 @發條橙: 我也是，加個聯系！\n@發條橙回覆 @路人: 模糊了嘿，我從以前一個同班女生叫馬蓉蓉的Twitter那裡扒來的。\n\n[附圖：合照截圖]"),
                (1, "何聽雨-心理醫生", "何聽雨-心理醫生", "我真的非常痛恨一些媒體為了博取關注度而不擇手段。雖然沒有人直接證據，但是我敢肯定，當年如果沒有他們的介入或許一切都會不一樣。作為受害者家屬，懷著那樣忐忑不安的心情日覆一日地等待著，自我安慰著，卻在短短幾天內就看到大鋪天蓋地的報道宣稱我至親之人的死亡。你們是醫生嗎？你們是警察嗎？你們憑什麼？", "2021年3月27日", ""),
                (1, "李克律師", "李克律師", "思念與愛意，藏在每一個我想跟你分享的瞬間…", "2021年11月2日", "@羅思Ross要堅強: 李大律師也有這麼矯情的時候吶～"),
                (1, "羅思Ross要堅強", "羅思Ross要堅強", "祝賀寶貝今天三周歲生日！", "2021年4月25日", "@李克律師: 生日快樂～"),
                (1, "羅思Ross要堅強", "羅思Ross要堅強", "害怕，無助…………", "2020年3月1日", ""),
                (1, "羅思Ross要堅強", "羅思Ross要堅強", "記得許久以前和媽媽討論過這個問題，當時媽媽作為新聞總編，說她選擇這個職業所信仰和堅持的，就是保障公眾的知情權。\n\n好文賞析——《社會健康發展需維護和保障社會公眾知情權》", "2019年12月1日", ""),
                (1, "蓓蓓今晚有好夢", "蓓蓓今晚有好夢", "今天幹了一件痛快事兒！", "2021年11月23日", "@小魚崽仔小公主: 哈哈哈哈！痛快！下次多去那家餐廳，說不定又碰到了！\n@是蓓蓓不是貝貝 回覆 @小魚崽仔小公主: 她敢！婊子！\n@耀: 我錯過了什麼？\n@小魚崽仔小公主 回覆 @耀: 哈哈哈哈，人民廣場的弗里餐廳，約會也哈哈哈哈哈。\n@耀 回覆 @小魚崽仔小公主: 什麼啊??\n@小魚崽仔小公主 回覆 @耀: 反正就是我們撈到了錢，還幫蓓蓓教訓了一下一個臭婊子。"),
                (1, "蓓蓓今晚有好夢", "蓓蓓今晚有好夢", "又做噩夢了……", "2021年11月20日", "@小魚崽仔小公主: 抱抱。\n@耀: 抱抱。"),
                (1, "蓓蓓今晚有好夢", "蓓蓓今晚有好夢", "我就是那頭小象，明明當時可以反抗，如果一開始就不去做，後面什麼都不會發生。為什麼？一步錯，步步錯。\n\n讀文：在印度和泰國，拴住一頭千斤重的大象只需要一根小小的柱子和一截細繩的繩子。因為在大象還是小象的時候，那些訓象人就用一條鐵鏈將它綁在水泥走或鋼柱上，小象無論怎麼掙扎都無法掙脫。漸漸地，小象放棄了掙扎，習慣了不掙扎，直到長成了大象。此時它完全可以輕而易舉地掙脫鏈子了，它也不再想到要去掙脫了。", "2021年1月5日", ""),
                (1, "小魚崽仔小公主", "小魚崽仔小公主", "媽的，最煩出軌的人了！今天幹了件痛快事，有的人不流點血不出點錢就不會長記性。", "2021年11月23日", ""),
            ],
        )

    time_only_pattern = re.compile(r"^\d{2}:\d{2}$")
    tweet_date_fallbacks = {
        "高析羽": "2021年11月1日",
        "何聽雨-心理醫生": "2021年3月27日",
        "李克律師": "2021年11月2日",
        "羅思ross要堅強": "2021年4月25日",
        "蓓蓓今晚有好夢": "2021年11月23日",
        "小魚崽仔小公主": "2021年11月23日",
    }
    tweet_rows = cursor.execute("SELECT id, username, posted_at, reply_content FROM tweets").fetchall()
    tweet_reply_fallbacks = {
        "李克律師": "@羅思Ross要堅強: 李大律師也有這麼矯情的時候吶～",
        "羅思Ross要堅強": "@李克律師: 生日快樂～",
    }
    for row in tweet_rows:
        if time_only_pattern.match(row["posted_at"]):
            cursor.execute(
                "UPDATE tweets SET posted_at = ? WHERE id = ?",
                (tweet_date_fallbacks.get(row["username"], "2024年10月12日"), row["id"]),
            )
        if not row["reply_content"]:
            cursor.execute(
                "UPDATE tweets SET reply_content = ? WHERE id = ?",
                (tweet_reply_fallbacks.get(row["username"], ""), row["id"]),
            )

    supplemental_web_clues = [
        (
            1,
            "淮陰日報",
            "https://moon.local/search/a21-1",
            "2002年7月10日淮陰日報報道，今日，我市公安局局長高為民榮獲國家“人民好警察”榮譽稱號，高為民從警多年，工作認真負責，兢兢業業，破案無數。",
            "高為民 淮陰日報 人民好警察 警察局長",
        ),
        (
            1,
            "淮陰日報",
            "https://moon.local/search/a21-2",
            "2008年11月29日淮陰日報報道，今日淮陰市警察局局長高為民召開記者會，就“何曦曦案”回答現場記者質詢，提到《時間》對於該案的獨家報道時，高為民情緒激動，破口大罵該文章記者不辨是非，為了獨家報道及博取公眾關注度而擅自對警方行動進行跟蹤拍攝，並認為極可能因此而暴露了警方行動，驚動了綁匪不排除追究其法律責任。",
            "高為民 淮陰日報 何曦曦 《時間》 記者會",
        ),
        (
            1,
            "淮陰日報",
            "https://moon.local/search/a21-3",
            "2008年12月1日淮陰日報報道，針對公眾質疑淮陰市警察隊伍內部有人擅自向媒體走漏行動消息而致使行動失敗的質疑今日省將成立專項調查組對此事進行深入調查，暫對淮陰市公安局多名相關人員，包括局長高為民作停職調查。",
            "高為民 淮陰日報 停職調查 行動消息",
        ),
        (
            1,
            "淮陰日報",
            "https://moon.local/search/a21-4",
            "2008年12月3日淮陰日報報道，今日曾獲國家“人民好警察”榮譽表彰的淮陰市公安局局長高為民疑因“何曦曦案”而跳樓身亡。高為民作為局長，親自部署抓捕行動，但最終被歹徒逃脫，人質何曦曦及秦靜怡目前生死未卜，也有報道指出兩人極大可能已經遇害。",
            "高為民 淮陰日報 何曦曦 秦靜怡 跳樓",
        ),
        (
            1,
            "淮陰(市)地圖",
            "https://moon.local/search/a22-1",
            "淮陰(市)地圖。",
            "淮陰(市)地圖 淮陰 地圖",
        ),
        (
            1,
            "淮陰(市)公交線路",
            "https://moon.local/search/a23-1",
            "淮陰市全市共有216條公交線路，公交車輛總保有量達到4014輛，為市民提供出行提供便利的服務。市民可以搜索查詢具體線路的公交線路圖。（可篩選）篩選條件:描述線路號特征,始發站或終點站、線路號碼特點等。",
            "淮陰(市) 公交線路 公交 地圖",
        ),
        (
            1,
            "好一家便利店",
            "https://moon.local/search/a24-1",
            "好一家連鎖便利店隸屬於淮陰市銀信實業有限公司，成立於1995年3月，在淮陰市本土已擁有200多間連鎖便利店。（可篩選）篩選條件:便利店所在的道路。",
            "好一家便利店 銀信實業 便利店 道路",
        ),
        (
            1,
            "好一家便利店 2008年",
            "https://moon.local/search/a25-1",
            "好一家連鎖便利店2008年在淮陰市共有55家分店，分布於惠濟區、金水區、五林區等淮陰市多個行政區。（可篩選）篩選條件:便利店所在的道路。",
            "好一家便利店 2008年 55家分店 道路",
        ),
        (
            1,
            "2008年11月28日新聞",
            "https://moon.local/search/a26-1",
            "2008年11月28日新聞，淮陰市著名企業家何國威向警方報案聲稱自己的女兒何曦曦遭到了綁架，目前下落不明。何國威表示3天前自己的女兒在放學路上被人綁架，一同被劫走的還有陪其回家的老師秦靜怡。歹徒以兩人性命威脅，要求何國威不準報警，並且準備100W贖金於25日放在時代公園指定垃圾桶旁。",
            "何曦曦 2008年11月28日新聞 何國威 秦靜怡 綁架",
        ),
        (
            1,
            "2013年11月28日新聞",
            "https://moon.local/search/a26-2",
            "2013年11月28日新聞，今日，距離當時震驚淮陰市的“何曦曦綁架案”已經過去了5年，但是目前警方尚無法掌握兩名被綁架者的行蹤以及綁匪的相關信息。何曦曦相關的專家分析，被綁架兩人極有可能已經遇害。",
            "何曦曦 2013年11月28日新聞 綁架案",
        ),
        (
            1,
            "何國威",
            "https://moon.local/search/a27-1",
            "何國威，國威集團董事長，何先生作為淮陰市知名企業家，與妻子育有兩女。2008年，其次女何曦曦遭遇綁架，至今下落不明，綁匪至今仍未被捕捉。何先生多年來一致致力於公益事業成立了“曦曦慈善基金會”，不僅如此，何先生還曾匿名資助了多名條件艱苦的貧困學生。",
            "何國威 國威集團 曦曦慈善基金會 企業家",
        ),
        (
            1,
            "淮陰日報",
            "https://moon.local/search/a27-2",
            "2008年11月30日淮陰日報報道，何國威接受采訪時針對《時間》“何曦曦案”的報道文章表示抗議和譴責，認為該文章記者極有可能采取非正當手段獲取有關此案的信息，包括警方的行動等，懷疑是有警方內部人員向媒體透露消息。",
            "何國威 淮陰日報 《時間》 何曦曦",
        ),
        (
            1,
            "螞蟻",
            "https://moon.local/search/a28-1",
            "螞蟻洞穴一般都有著固定的朝向，其洞口一般朝南，而野外工作者也經常利用這一點來判斷方向。",
            "螞蟻 洞口 朝南 判斷方向",
        ),
        (
            1,
            "秦靜怡",
            "https://moon.local/search/a29-1",
            "淮陰市“最美女教師”，2008年秦靜怡秦老師為了保護自己的學生，被綁匪一同綁架，至今下落不明，綁匪至今仍未被捕。其事跡感動千萬淮陰市市民，我市洪定授予其“見義勇為”優秀青年榮譽，其家屬上台領獎時泣不成聲，表示絕對不會放棄一絲希望。",
            "秦靜怡 最美女教師 見義勇為 綁架",
        ),
        (
            1,
            "《時間》雜志(期刊)",
            "https://moon.local/search/a30-1",
            "《時間》是國內的新聞類期刊雜志,2005年創刊。2008年該刊對於“何曦曦案”的獨家報道文章引發了社會的巨大反響，其銷量和知名度獲得了極大的提升。但對於該案報道的爭議一直不斷，目前該雜志的總編正是當年“何曦曦案”報道的記者張清伊。",
            "《時間》雜志(期刊) 《時間》 張清伊 何曦曦",
        ),
        (
            1,
            "2019年4月1日《時間》",
            "https://moon.local/search/a31-1",
            "2019年4月1日《時間》，張清伊接棒,成為《時間》總編,張清伊表示一定盡全力做好這份工作,不負重托。",
            "張清伊 時間總編 2019年4月1日《時間》",
        ),
        (
            1,
            "2020年3月《時間》",
            "https://moon.local/search/a31-2",
            "《“我的信念是保障公眾知情權”——張清伊人物專訪》：張清伊作為《時間》的總編,一直把保障公眾知情權作為其行事的帶尺和準則。但是也因為對工作過於認真負責,導致與丈夫分開,對女兒感到非常的愧疚。",
            "張清伊 時間總編 人物專訪 公眾知情權",
        ),
    ]
    existing_web_urls = {
        row["url"] for row in cursor.execute("SELECT url FROM web_clues").fetchall()
    }
    missing_web_clues = [
        row for row in supplemental_web_clues if row[2] not in existing_web_urls
    ]
    if missing_web_clues:
        cursor.executemany(
            """
            INSERT INTO web_clues (act, title, url, snippet, keywords)
            VALUES (?, ?, ?, ?, ?)
            """,
            missing_web_clues,
        )

    canonical_contacts = [
        ("00136583", "信科互聯網公司", "你好，信科互聯網公司。"),
        ("00134466", "聶雲溪心理診所", "你好，聶雲溪心理診所。"),
        ("00130464", "何聽雨心理診所", "你好，何聽雨心理診所。"),
        ("00167999", "CLUB酒吧", "你好，CLUB酒吧。客人不好意思哦，我們還沒開始營業。"),
        ("00168888", "雀仔麻將館", "你好，雀仔麻將館"),
        ("00169922", "弗里餐廳", "你好，弗里餐廳。"),
        ("00164488", "合德大學愛心助力通道", "你好，這里是合德大學愛心助力通道。"),
        ("00139002", "無憂律師事務所", "你好，無憂律師事務所，請問有什麼能幫您？"),
    ]
    existing_contact_phones = {
        row["phone"] for row in cursor.execute("SELECT phone FROM chat_contacts").fetchall()
    }
    missing_contacts = [
        row for row in canonical_contacts if row[0] not in existing_contact_phones
    ]
    if missing_contacts:
        cursor.executemany(
            "INSERT INTO chat_contacts (phone, name, intro) VALUES (?, ?, ?)",
            missing_contacts,
        )

    contact_rows = cursor.execute("SELECT id, phone FROM chat_contacts").fetchall()
    contact_by_phone = {row["phone"]: row["id"] for row in contact_rows}

    canonical_responses = [
        (
            "00136583",
            1,
            "陳宏經理在嗎 陳宏在嗎 請問陳宏經理在嗎 請問陳宏在嗎",
            "陳經理不在。他作為我們的經理，表現一直很好。他昨晚加班了，他今天可能會晚一點到公司。具體加班到幾點我也不清楚。",
        ),
        (
            "00136583",
            1,
            "我是陳宏 我是陈宏",
            "你別玩了，陳經理的聲音我認得出來",
        ),
        (
            "00136583",
            1,
            "我是吳銘 我是吴铭 吳銘在嗎 請問吳銘在嗎",
            "吳銘？他已經辭職很久了，現在也不是本公司的職員了。辭職的原因我不方便跟你透露，只能說是他個人的原因。真的非常可惜，他作為一名數據分析員，其實表現的一直非常好。如果你有事找他，可以試著聯系陳經理，他們是兄弟。",
        ),
        (
            "00134466",
            1,
            "聶雲溪醫生在嗎 聶醫生在嗎 請問聶雲溪醫生在嗎",
            "聶醫生不在。對，他現在在國外學習，我們也沒法聯系上他。請問你是哪一位患者？我們可以幫你查看，看看能不能轉介其他醫生。",
        ),
        (
            "00134466",
            1,
            "訊息洩漏 信息泄漏 數據洩漏 泄漏事故",
            "你從那里聽說？絕無可能，我們診所一向對病患的信息十分重視，最近也就此加強保護。你所說的，不過是以訛傳訛，惡意誹毀。",
        ),
        (
            "00134466",
            1,
            "我是吳銘 我想了解自己病情 吳銘在你們診所就診",
            "很抱歉，我們在電話里不能透露患者的信息，即便是本人也不可以。",
        ),
        (
            "00134466",
            1,
            "何聽雨醫生 何聽雨 你認識何聽雨醫生嗎",
            "是的，她和我們聶雲溪醫生師出同門，也會經常過來我們診所與聶雲溪醫生進行學術交流。",
        ),
        (
            "00134466",
            1,
            "我是聶雲溪 我是聂云溪",
            "聶醫生？我認識聶醫生的聲音。不好意思，這個是辦公電話，請不要開這種無聊的玩笑。",
        ),
        (
            "00130464",
            1,
            "何聽雨醫生在嗎 何醫生在嗎 請問何聽雨醫生在嗎",
            "何聽雨醫生昨天加班得很晚，所以今天不在。昨晚就何聽雨醫生一個人在，她怕自己睡著要我們點打電話到辦公室喊他。",
        ),
        (
            "00130464",
            1,
            "訊息洩漏 信息泄漏 數據洩漏 泄漏事故",
            "你從那里聽說？這是不可能的，我們最近也聽到其他診所發生類似事故的傳言。所以最近又對患者資料室進行了加強保護。",
        ),
        (
            "00130464",
            1,
            "我是吳銘 我想了解自己病情 吳銘在你們診所就診",
            "很抱歉，我們在電話里不能透露患者的信息，即便是本人也不可以。",
        ),
        (
            "00130464",
            1,
            "聶雲溪醫生 聶雲溪 你認識聶雲溪醫生嗎",
            "是的，她和我們何聽雨醫生師出同門，也會經常進行學術交流。",
        ),
        (
            "00130464",
            1,
            "我是何聽雨",
            "何醫生？我認識何醫生的聲音。不好意思，這個是辦公電話，請不要開這種無聊的玩笑。",
        ),
        (
            "00167999",
            1,
            "錢好似付多了 付多了 查一下 昨晚11點 4點左右",
            "我查看一下，那個時候，哦？李克先生？聽你的聲音不像李先生啊。你是不是搞錯了先生",
        ),
        (
            "00167999",
            1,
            "我是李克 因為感冒聲音不一樣 昨晚我發生了甚麼",
            "哦，原來是這樣。哈哈，你昨晚可能是跟你愛的人吵架了吧。你從11點待到我們4點打烊呢，我們服務生問你的時候，你還苦笑是為了一個你愛的女人，你真是一位深情的人",
        ),
        (
            "00167999",
            1,
            "李克先生的朋友 我想訂位 李克先生 朋友",
            "哦，歡迎歡迎，李先生啊，他是我們常客了。他就住在附近。對了，昨天晚上他也來了，從11點待到4點呢，不過他看起來心情很不好，我問他，他只是苦笑地說為了一個他愛的女人。",
        ),
        (
            "00168888",
            1,
            "我是範仁 我是范仁",
            "什麼？範仁？你搞笑呢，範仁天天晚上來，我還能不認得他的聲咩嗎？你到底是誰？是範仁介紹來的？",
        ),
        (
            "00168888",
            1,
            "範仁的朋友 昨晚也去了嗎 昨晚也去 範仁朋友",
            "我們10點就關門了，他也是打到我們關門就走了。不過說實話這幾天他最不知怎麼了，單氣特別大，動不動就發火。我們都不想接待了。你訂位嗎？不訂位打電話問那麼多有的沒的幹嘛？",
        ),
        (
            "00168888",
            1,
            "範仁有欠債嗎 欠債 秘密 小金庫",
            "我們這就是小麻將店，誰也不會賴那個個錢啦！不過說到欠債，範仁每天都在我們面前誇海口，說只要他和他那個兒子有共同的秘密，那他們就是他永遠的小金庫，你再問他是啥秘密，他又神秘兮兮跟他說，死人才配共享他的秘密。你說哪有這樣嚇人的。",
        ),
        (
            "00169922",
            1,
            "我是高析羽 你好我是高析羽",
            "不好意思，我不知道您說的哪一位客人我們每天客人比較多。",
        ),
        (
            "00169922",
            1,
            "23日11點左右 23號11點左右 少付了錢 多付了錢",
            "我幫您看一下，嗯，23號11點左右，付款人顯示高析羽……是您嗎？啊你就是那個很帥的小姐姐嗎？那天人比較少，我有印象，我記得當時還有一名女士跟您一起的。您當時一共支付了200元，我看了一下，賬單沒有什麼問題，請問您覺得付款哪里存在問題呢？",
        ),
        (
            "00164488",
            1,
            "我是吳銘 愛心捐贈 我來進行愛心捐贈",
            "上次真的太感謝你和其他校友的捐贈了，你還好嗎？上次我看你聽到一直以來匿名幫助你的那個好心人的真實姓名後，臉色很差啊。",
        ),
        (
            "00164488",
            1,
            "曾經合德大學的學生 吳銘的朋友 介紹我來進行愛心捐贈",
            "上次真的非常感謝吳銘和其他校友的捐贈。吳銘身體還好吧？上次捐贈儀式上，他知道一直以來匿名幫助他的那個好心人的真實姓名後，臉煞白，我們都很擔心他呢。",
        ),
        (
            "00139002",
            1,
            "李克律師在嗎 李克律師",
            "李克律師是我們這里的資深律師了，不過他今天不在需要為您介紹其他的律師嗎？",
        ),
        (
            "00139002",
            1,
            "聶雲溪醫生的案子 聶雲溪案子",
            "那個案子確實是李克律師負責的，我們李克律師負責這類案件也較多，跟他合作的醫生有聶雲溪醫生，還有本市很有名的何聽雨醫生，說起來，還是何聽雨醫生介紹李律師給聶醫生認識的呢。請問你是要咨詢類似案件嗎？",
        ),
        (
            "00139002",
            1,
            "我是李克",
            "您別鬧了，我很熟悉李克律師的聲音。",
        ),
    ]

    existing_response_keys = {
        (
            row["phone"],
            row["act"],
            row["trigger_keywords"],
            row["response_text"],
        )
        for row in cursor.execute(
            """
            SELECT c.phone, r.act, r.trigger_keywords, r.response_text
            FROM chat_responses r
            JOIN chat_contacts c ON c.id = r.contact_id
            """
        ).fetchall()
    }
    missing_responses = [
        (contact_by_phone[phone], act, trigger_keywords, response_text)
        for phone, act, trigger_keywords, response_text in canonical_responses
        if (phone, act, trigger_keywords, response_text) not in existing_response_keys
    ]
    if missing_responses:
        cursor.executemany(
            """
            INSERT INTO chat_responses (contact_id, act, trigger_keywords, response_text)
            VALUES (?, ?, ?, ?)
            """,
            missing_responses,
        )

    cursor.execute(
        """
        INSERT INTO game_state (id, current_act, updated_at)
        VALUES (1, 1, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        (utc_now(),),
    )

    connection.commit()
