import json
import os
from pathlib import Path
import re
import time

from bs4 import BeautifulSoup
import requests

# ============================================================
# Configuration
# ============================================================

STEAM250_URL = "https://steam250.com/7day"
STATE_FILE = Path("data/steam250_state.json")
WEBHOOK_URL = os.environ.get("STEAM250_DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
}

# ============================================================
# Steam250 → 简体中文标签
# ============================================================

TAG_TRANSLATIONS = {
    "1980s": "80年代",
    "1990's": "90年代",
    "2.5D": "2.5D",
    "2D": "2D",
    "2D Fighter": "2D格斗",
    "2D Platformer": "2D平台跳跃",
    "360 Video": "360度视频",
    "3D": "3D",
    "3D Fighter": "3D格斗",
    "3D Platformer": "3D平台跳跃",
    "4 Player Local": "本地四人",
    "4X": "4X",
    "6DOF": "六自由度",
    "8-bit Music": "8位音乐",
    "Abstract": "抽象",
    "Action": "动作",
    "Action-Adventure": "动作冒险",
    "Action Roguelike": "动作类Rogue",
    "Action RPG": "动作角色扮演",
    "Action RTS": "动作即时战略",
    "Addictive": "令人上瘾",
    "Adventure": "冒险",
    "Agriculture": "农业",
    "Aliens": "外星人",
    "Alternate History": "架空历史",
    "Animals": "动物",
    "Animation & Modeling": "动画与建模",
    "Anime": "日系动画",
    "Arcade": "街机",
    "Archery": "射箭",
    "Arena Shooter": "竞技场射击",
    "Artificial Intelligence": "人工智能",
    "Assassins": "刺客",
    "Asymmetric VR": "非对称VR",
    "Asynchronous Multiplayer": "异步多人",
    "Atmospheric": "氛围",
    "ATV": "全地形车",
    "Audio Production": "音频制作",
    "Auto Battler": "自走棋",
    "Automation": "自动化",
    "Automobile Sim": "汽车模拟",
    "Baseball": "棒球",
    "Base Building": "基地建造",
    "Based On A Novel": "改编自小说",
    "Basketball": "篮球",
    "Battle Royale": "大逃杀",
    "Beat 'em up": "清版动作",
    "Beautiful": "唯美",
    "Benchmark": "跑分",
    "Bikes": "自行车",
    "Billiards": "台球",
    "Birds": "鸟类",
    "BMX": "小轮车",
    "Board Game": "桌游",
    "Boomer Shooter": "复古射击",
    "Boss Rush": "Boss连战",
    "Bowling": "保龄球",
    "Boxing": "拳击",
    "Building": "建造",
    "Bullet Heaven": "弹幕天堂",
    "Bullet Hell": "弹幕",
    "Bullet Time": "子弹时间",
    "Capitalism": "资本主义",
    "Capybaras": "水豚",
    "Card Battler": "卡牌对战",
    "Card Game": "卡牌游戏",
    "Cartoon": "卡通",
    "Cartoony": "卡通风格",
    "Casual": "休闲",
    "Cats": "猫",
    "Character Action Game": "角色动作游戏",
    "Character Customization": "角色自定义",
    "Chess": "国际象棋",
    "Choices Matter": "选择影响剧情",
    "Choose Your Own Adventure": "自选冒险",
    "Cinematic": "电影化",
    "City Builder": "城市营造",
    "Class-Based": "职业制",
    "Classic": "经典",
    "Cleaning": "清洁",
    "Cold War": "冷战",
    "Collectathon": "收集马拉松",
    "Colony Sim": "殖民地模拟",
    "Colorful": "色彩鲜艳",
    "Combat": "战斗",
    "Combat Racing": "战斗竞速",
    "Comedy": "喜剧",
    "Comic Book": "漫画",
    "Competitive": "竞技",
    "Conspiracy": "阴谋",
    "Controller": "手柄",
    "Cooking": "烹饪",
    "Co-op": "合作",
    "Co-op Campaign": "合作战役",
    "Cozy": "温馨",
    "Crafting": "制作",
    "Creature Collector": "怪物收集",
    "Cricket": "板球",
    "Crime": "犯罪",
    "CRPG": "古典角色扮演",
    "Cult": "邪典",
    "Cute": "可爱",
    "Cyberpunk": "赛博朋克",
    "Cycling": "骑行",
    "Dark": "黑暗",
    "Dark Comedy": "黑色喜剧",
    "Dark Fantasy": "黑暗奇幻",
    "Dark Humor": "黑色幽默",
    "Dating Sim": "恋爱模拟",
    "Deckbuilding": "卡组构筑",
    "Decorating": "装饰",
    "Demons": "恶魔",
    "Design & Illustration": "设计与插画",
    "Desktop Companion": "桌面伴侣",
    "Destruction": "破坏",
    "Detective": "侦探",
    "Dialogue Heavy": "对话丰富",
    "Dice": "骰子",
    "Difficult": "高难度",
    "Dinosaurs": "恐龙",
    "Diplomacy": "外交",
    "Dogs": "狗",
    "Dragons": "龙",
    "Driving": "驾驶",
    "Dungeon Crawler": "地牢探索",
    "Dwarves": "矮人",
    "Dynamic Narration": "动态旁白",
    "Dystopian": "反乌托邦",
    "Early Access": "抢先体验",
    "Economy": "经济",
    "Education": "教育",
    "Electronic Music": "电子音乐",
    "Elves": "精灵",
    "Emotional": "情感",
    "Epic": "史诗",
    "Episodic": "章节式",
    "Escape Room": "密室逃脱",
    "Espionage": "间谍",
    "eSports": "电子竞技",
    "Experimental": "实验性",
    "Exploration": "探索",
    "Extraction Shooter": "撤离射击",
    "Faith": "信仰",
    "Falling Blocks": "落块",
    "Family Friendly": "阖家",
    "Fantasy": "奇幻",
    "Farming": "农耕",
    "Farming Sim": "农场模拟",
    "Fast-Paced": "节奏明快",
    "Female Protagonist": "女性主角",
    "Fighting": "格斗",
    "First-Person": "第一人称",
    "Fishing": "钓鱼",
    "Flight": "飞行",
    "FMV": "真人影像",
    "Football (American)": "美式足球",
    "Football (Soccer)": "足球",
    "Foxes": "狐狸",
    "FPS": "第一人称射击",
    "Free to Play": "免费游玩",
    "Funny": "搞笑",
    "Futuristic": "未来",
    "Gambling": "赌博",
    "Game Development": "游戏开发",
    "Gaming": "电子游戏",
    "God Game": "上帝模拟",
    "Golf": "高尔夫",
    "Gore": "血腥",
    "Gothic": "哥特",
    "Grand Strategy": "大战略",
    "Great Soundtrack": "优秀原声",
    "Grid-Based Movement": "网格移动",
    "Gun Customization": "枪械改装",
    "Hack and Slash": "砍杀",
    "Hacking": "黑客",
    "Hand-drawn": "手绘",
    "Hardware": "硬件",
    "Heist": "劫案",
    "Hentai": "成人",
    "Hero Shooter": "英雄射击",
    "Hex Grid": "六边形网格",
    "Hidden Object": "寻物",
    "Historical": "历史",
    "Hobby Sim": "爱好模拟",
    "Hockey": "冰球",
    "Horror": "恐怖",
    "Horses": "马匹",
    "Hunting": "狩猎",
    "Idler": "放置",
    "Immersive": "沉浸",
    "Immersive Sim": "沉浸式模拟",
    "Incremental": "增量",
    "Indie": "独立",
    "Instrumental Music": "器乐",
    "Intentionally Awkward Controls": "蹩脚操作",
    "Interactive Fiction": "互动小说",
    "Inventory Management": "物品栏管理",
    "Investigation": "调查",
    "Isometric": "等距视角",
    "Job Simulator": "职业模拟",
    "JRPG": "日式角色扮演",
    "Jump Scare": "跳吓",
    "Language Learning": "语言学习",
    "Lemmings": "旅鼠",
    "Level Editor": "关卡编辑器",
    "LGBTQ+": "LGBTQ+",
    "Life Sim": "生活模拟",
    "Linear": "线性",
    "Local Co-Op": "本地合作",
    "Local Multiplayer": "本地多人",
    "Logic": "逻辑",
    "Loot": "战利品",
    "Looter Shooter": "刷宝射击",
    "Lore-Rich": "设定丰富",
    "Lovecraftian": "洛夫克拉夫特式",
    "Magic": "魔法",
    "Mahjong": "麻将",
    "Management": "经营管理",
    "Mars": "火星",
    "Martial Arts": "武术",
    "Massively Multiplayer": "大型多人在线",
    "Match 3": "三消",
    "Mechs": "机甲",
    "Medical Sim": "医疗模拟",
    "Medieval": "中世纪",
    "Memes": "梗",
    "Metroidvania": "类银河恶魔城",
    "Military": "军事",
    "Minigames": "小游戏",
    "Mini Golf": "迷你高尔夫",
    "Minimalist": "极简",
    "Mining": "采矿",
    "MMORPG": "大型多人在线角色扮演",
    "MOBA": "MOBA",
    "Mod": "模组",
    "Moddable": "支持模组",
    "Modern": "现代",
    "Motocross": "越野摩托",
    "Motorbike": "摩托车",
    "Mouse Only": "仅鼠标",
    "Multiplayer": "多人",
    "Multiple Endings": "多结局",
    "Music": "音乐",
    "Music-Based Procedural Generation": "音乐驱动程序生成",
    "Musou": "无双",
    "Mystery": "悬疑",
    "Mystery Dungeon": "不可思议迷宫",
    "Mythology": "神话",
    "Narrative": "叙事",
    "Nature": "自然",
    "Naval": "海军",
    "Naval Combat": "海战",
    "Ninja": "忍者",
    "Noir": "黑色",
    "Nonlinear": "非线性",
    "Nostalgia": "怀旧",
    "Nudity": "裸露",
    "Offroad": "越野",
    "Old School": "老派",
    "Online Co-Op": "在线合作",
    "On-Rails Shooter": "轨道射击",
    "Open World": "开放世界",
    "Open World Survival Craft": "开放世界生存制作",
    "Organizing": "整理",
    "Otome": "乙女",
    "Outbreak Sim": "疫情模拟",
    "Parkour": "跑酷",
    "Parody": "恶搞",
    "Party": "派对",
    "Party-Based RPG": "队伍角色扮演",
    "Party Game": "派对游戏",
    "Perma Death": "永久死亡",
    "Philosophical": "哲学",
    "Photo Editing": "照片编辑",
    "Physics": "物理",
    "Pinball": "弹珠",
    "Pirates": "海盗",
    "Pixel Graphics": "像素画面",
    "Platformer": "平台跳跃",
    "Point & Click": "指向点击",
    "Poker": "扑克",
    "Political Sim": "政治模拟",
    "Post-apocalyptic": "后启示录",
    "Precision Platformer": "精准平台跳跃",
    "Procedural Generation": "程序生成",
    "Programming": "编程",
    "Psychedelic": "迷幻",
    "Psychological": "心理",
    "Psychological Horror": "心理恐怖",
    "Puzzle": "解谜",
    "Puzzle Platformer": "解谜平台跳跃",
    "PvE": "PvE",
    "PvP": "PvP",
    "Quick-Time Events": "快速反应事件",
    "Racing": "竞速",
    "Realistic": "拟真",
    "Real-Time": "即时",
    "Real Time Tactics": "即时战术",
    "Real-Time with Pause": "即时暂停",
    "Reboot": "重启",
    "Relaxing": "放松",
    "Remake": "重制",
    "Replay Value": "重玩价值",
    "Resource Management": "资源管理",
    "Retro": "复古",
    "Rhythm": "音游",
    "Robots": "机器人",
    "Rock Music": "摇滚乐",
    "Roguelike": "类Rogue",
    "Roguelike Deckbuilder": "类Rogue构筑",
    "Roguelite": "Roguelite",
    "Romance": "恋爱",
    "Rome": "罗马",
    "RPG": "角色扮演",
    "RTS": "即时战略",
    "Rugby": "橄榄球",
    "Runner": "跑动",
    "Sailing": "航海",
    "Samurai": "武士",
    "Sandbox": "沙盒",
    "Satire": "讽刺",
    "Science": "科学",
    "Sci-fi": "科幻",
    "Score Attack": "分数挑战",
    "Sequel": "续作",
    "Sexual Content": "性内容",
    "Shoot 'Em Up": "弹幕射击",
    "Shooter": "射击",
    "Shop Keeper": "店主",
    "Short": "短篇",
    "Side Scroller": "横版卷轴",
    "Silent Protagonist": "沉默主角",
    "Simulation": "模拟",
    "Singleplayer": "单人",
    "Skateboarding": "滑板",
    "Skating": "滑冰",
    "Skiing": "滑雪",
    "Sniper": "狙击",
    "Snow": "雪",
    "Snowboarding": "单板滑雪",
    "Social Deduction": "社交推理",
    "Software": "软件",
    "Software Training": "软件教学",
    "Sokoban": "推箱子",
    "Solitaire": "纸牌",
    "Souls-like": "类魂",
    "Soundtrack": "原声",
    "Space": "太空",
    "Spaceships": "飞船",
    "Space Sim": "太空模拟",
    "Spectacle fighter": "华丽格斗",
    "Spelling": "拼写",
    "Split Screen": "分屏",
    "Sports": "体育",
    "Stealth": "潜行",
    "Steampunk": "蒸汽朋克",
    "Story Rich": "剧情丰富",
    "Strategy": "策略",
    "Strategy RPG": "策略角色扮演",
    "Stylized": "风格化",
    "Submarine": "潜艇",
    "Superhero": "超级英雄",
    "Supernatural": "超自然",
    "Surreal": "超现实",
    "Survival": "生存",
    "Survival Horror": "生存恐怖",
    "Swordplay": "剑术",
    "Tabletop": "桌面游戏",
    "Tactical": "战术",
    "Tactical RPG": "战术角色扮演",
    "Tanks": "坦克",
    "Team-Based": "团队",
    "Tennis": "网球",
    "Text-Based": "文字",
    "Third Person": "第三人称",
    "Third-Person Shooter": "第三人称射击",
    "Thriller": "惊悚",
    "Time Attack": "计时挑战",
    "Time Management": "时间管理",
    "Time Manipulation": "时间操控",
    "Time Travel": "时间旅行",
    "Top-Down": "俯视",
    "Top-Down Shooter": "俯视射击",
    "Touch-Friendly": "触屏友好",
    "Tower Defense": "塔防",
    "TrackIR": "TrackIR",
    "Trading": "交易",
    "Trading Card Game": "集换式卡牌",
    "Traditional Roguelike": "传统Roguelike",
    "Trains": "火车",
    "Transhumanism": "超人类主义",
    "Transportation": "运输",
    "Trivia": "问答",
    "Turn-Based": "回合制",
    "Turn-Based Combat": "回合制战斗",
    "Turn-Based Strategy": "回合制策略",
    "Turn-Based Tactics": "回合制战术",
    "Tutorial": "教程",
    "Twin Stick Shooter": "双摇杆射击",
    "Typing": "打字",
    "Underground": "地下",
    "Underwater": "水下",
    "Utilities": "工具",
    "Vampires": "吸血鬼",
    "Vehicular Combat": "载具战斗",
    "Video Production": "视频制作",
    "Vikings": "维京",
    "Villain Protagonist": "反派主角",
    "Violent": "暴力",
    "Visual Novel": "视觉小说",
    "Voice Control": "语音控制",
    "Volleyball": "排球",
    "Voxel": "体素",
    "VR": "VR",
    "Walking Simulator": "步行模拟",
    "War": "战争",
    "Wargame": "战棋",
    "Werewolves": "狼人",
    "Western": "西部",
    "Wholesome": "治愈",
    "Wolves": "狼",
    "Word Game": "文字游戏",
    "World War I": "一战",
    "World War II": "二战",
    "Wrestling": "摔跤",
    "Wuxia": "武侠",
    "Xianxia": "仙侠",
    "Zombies": "僵尸",
    "Zoo": "动物园",
}


def translate_tag(tag):
    tag = tag.strip()
    return TAG_TRANSLATIONS.get(tag, tag)


# ============================================================
# 排除标签
# ============================================================

EXCLUDED_TAGS = {
    "Horror",
    "Hentai",
    "Sexual Content",
    "Nudity",
}


# ============================================================
# Utility
# ============================================================


def clean_text(text):
    return " ".join(text.split())


# ============================================================
# State
# ============================================================


def load_state():
    if not STATE_FILE.exists():
        return set()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(data.get("pushed", []))
    except Exception as e:
        print(f"读取 state.json 失败：{e}")
        return set()


def save_state(pushed_ids):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"pushed": list(pushed_ids)[-500:]}
    STATE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ============================================================
# Steam 价格与信息接口
# ============================================================


def get_steam_appid(store_url):
    match = re.search(r"/app/(\d+)", store_url)
    return match.group(1) if match else None


def get_cny_price(appid):
    """通过 Steam Store API 获取中国区人民币价格"""
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": appid, "cc": "cn", "l": "schinese"}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json().get(str(appid), {})
        if not data.get("success"):
            return None

        app_data = data.get("data", {})
        if "price_overview" in app_data:
            return app_data["price_overview"].get("final_formatted")
        return None
    except Exception as e:
        print(f"获取 CNY 定价失败 (AppID {appid}): {e}")
        return None


def get_display_price(store_url, usd_price):
    """根据国区是否有定价返回对应显示格式"""
    appid = get_steam_appid(store_url)
    cny_price = get_cny_price(appid) if appid else None

    if cny_price:
        return f"💰 {cny_price}"
    else:
        return f"💰 CNY：暂无价格\n💰 USD：{usd_price}"


def get_fallback_image(store_url):
    appid = get_steam_appid(store_url)
    if not appid:
        return None
    return f"https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"


# ============================================================
# 找到主榜单
# ============================================================


def get_main_ranking(soup):
    heading = soup.find(
        lambda tag: tag.name in {"h1", "h2", "h3"}
        and "Week Top 50 Games Ranking"
        in clean_text(tag.get_text(" ", strip=True))
    )
    if not heading:
        raise RuntimeError("找不到 Week Top 50 Games Ranking")

    ranking = heading.find_next(
        lambda tag: tag.name == "section" and "applist" in tag.get("class", [])
    )
    if not ranking:
        raise RuntimeError("找到 Top 50 标题，但找不到对应的主榜单 section")

    return ranking


# ============================================================
# 好评率
# ============================================================


def parse_rating(review_div):
    meter = review_div.select_one("div.meter.rating")
    if not meter:
        return "N/A"

    rating_span = meter.find("span")
    if rating_span:
        style = rating_span.get("style", "")
        match = re.search(r"width\s*:\s*([\d.]+%)", style, re.IGNORECASE)
        if match:
            return match.group(1)

    text = clean_text(meter.get_text(" ", strip=True))
    match = re.search(r"(\d+(?:\.\d+)?%)", text)
    if match:
        return match.group(1)

    return "N/A"


# ============================================================
# Steam250 图片
# ============================================================


def parse_image(row):
    img = row.find("img")
    if not img:
        return None

    image_url = img.get("data-src") or img.get("src")
    if not image_url:
        return None

    if image_url.startswith("//"):
        image_url = "https:" + image_url
    elif image_url.startswith("/"):
        image_url = "https://steam250.com" + image_url

    return image_url


# ============================================================
# 解析游戏
# ============================================================


def parse_game(row):
    # 1. 必须是 New
    rank_div = row.find("div", class_="rank", recursive=False)
    if not rank_div:
        return None

    new_marker = rank_div.find("span", attrs={"title": "New entry"})
    if not new_marker:
        return None

    # 2. 标题
    title_div = row.find("div", class_="title", recursive=False)
    if not title_div:
        return None

    title_link = title_div.find("a", title=True)
    if not title_link:
        return None

    name = clean_text(title_link.get_text(" ", strip=True))
    if not name:
        return None

    # 3. Steam 商店链接
    actions_div = row.find("div", class_="actions", recursive=False)
    if not actions_div:
        return None

    store_link = actions_div.find("a", class_="store")
    if not store_link:
        return None

    store_url = store_link.get("href")
    if not store_url:
        return None

    # 4. Free 排除
    price_div = row.find("div", class_="price", recursive=False)
    if not price_div:
        return None

    free_marker = price_div.find("a", class_="free")
    if free_marker:
        print(f"排除 Free：{name}")
        return None

    # 5. Adult only 排除
    adult_marker = row.find("a", href="/adult", title="Adult only")
    if adult_marker:
        print(f"排除 Adult only：{name}")
        return None

    # 6. Steam250 标签
    tags = [
        clean_text(tag.get_text(" ", strip=True))
        for tag in title_div.select("a.tag")
    ]

    # 7. 排除指定标签
    excluded = [tag for tag in tags if tag in EXCLUDED_TAGS]
    if excluded:
        print(f"排除指定标签：{name} ({', '.join(excluded)})")
        return None

    # 8. 中文标签 (最多三个)
    translated_tags = [translate_tag(tag) for tag in tags][:3]

    # 9. 评论数 + 好评率
    review_div = row.find("div", class_="reviews", recursive=False)
    votes = "N/A"
    rating = "N/A"
    if review_div:
        votes_span = review_div.select_one("span.votes")
        if votes_span:
            votes = clean_text(votes_span.get_text(" ", strip=True))
        rating = parse_rating(review_div)

    # 10. Steam250 原价 (美元，用于回退展示)
    price_spans = price_div.find_all("span", recursive=False)
    if not price_spans:
        return None

    usd_price = clean_text(price_spans[0].get_text(" ", strip=True))
    if not usd_price:
        return None

    # 11. 图片
    image_url = parse_image(row)
    if not image_url:
        image_url = get_fallback_image(store_url)

    # 12. 获取实际展示价格 (请求 Steam 官方 API)
    display_price = get_display_price(store_url, usd_price)
    time.sleep(1)  # 短暂延迟，避免频繁请求 Steam API 被限流

    return {
        "id": store_url,
        "name": name,
        "url": store_url,
        "votes": votes,
        "rating": rating,
        "price": display_price,
        "tags": translated_tags,
        "image": image_url,
    }


# ============================================================
# 获取主榜单 New
# ============================================================


def fetch_new_games():
    print("========================================")
    print("[1/5] Fetching Steam250...")

    response = requests.get(STEAM250_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    print("[2/5] Locating main Top 50 ranking...")
    ranking = get_main_ranking(soup)

    rows = ranking.find_all("div", recursive=False)
    print(f"[3/5] Main ranking rows: {len(rows)}")

    games = []
    for row in rows:
        game = parse_game(row)
        if game:
            games.append(game)

    print(f"[4/5] Qualified New games: {len(games)}")
    return games


# ============================================================
# Discord Embed
# ============================================================


def create_embed(game):
    # game['price'] 已经包含了预格式化好的货币符号与排版
    description = (
        f"{game['votes']} 评论数 · {game['rating']} 好评率\n"
        f"{game['price']}"
    )

    if game["tags"]:
        description += "\n🏷️ " + " · ".join(game["tags"])

    embed = {
        "title": f"🆕 {game['name']}",
        "url": game["url"],
        "description": description,
        "footer": {"text": "Steam250 · New Entry"},
    }

    if game.get("image"):
        embed["image"] = {"url": game["image"]}

    return embed


# ============================================================
# Discord 推送
# ============================================================


def send_discord(games):
    if not games:
        return

    if not WEBHOOK_URL:
        raise RuntimeError("未设置 STEAM250_DISCORD_WEBHOOK")

    for start in range(0, len(games), 10):
        batch = games[start : start + 10]
        payload = {
            "username": "Steam250",
            "embeds": [create_embed(game) for game in batch],
        }

        response = requests.post(
            WEBHOOK_URL, json=payload, timeout=30, headers=HEADERS
        )
        response.raise_for_status()
        print(f"Discord message sent: {len(batch)} embeds")


# ============================================================
# Main
# ============================================================


def main():
    print("Steam250 New Games")
    print("========================================")

    games = fetch_new_games()
    if not games:
        print("没有符合条件的 New 游戏。")
        return

    pushed_ids = load_state()
    new_games = []

    print("========================================")
    print("[5/5] Checking pushed state...")

    for game in games:
        if game["id"] in pushed_ids:
            print(f"跳过已推送：{game['name']}")
            continue
        new_games.append(game)

    print(f"本次待推送：{len(new_games)}")
    if not new_games:
        print("没有新的待推送游戏。")
        return

    print("========================================")
    for game in new_games:
        clean_price_log = game["price"].replace("\n", " | ")
        print(
            f"推送：{game['name']} | "
            f"{game['votes']} 评论数 | "
            f"{game['rating']} 好评率 | "
            f"{clean_price_log}"
        )
        print(f"  Steam: {game['url']}")
        print(f"  Image: {game['image']}")
        if game["tags"]:
            print(f"  Tags: {' · '.join(game['tags'])}")

    send_discord(new_games)

    for game in new_games:
        pushed_ids.add(game["id"])
    save_state(pushed_ids)

    print("========================================")
    print("Discord 推送完成。")
    print("State saved.")


if __name__ == "__main__":
    main()
