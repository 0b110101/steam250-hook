import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


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

    # --------------------------------------------------------
    # 基础类型
    # --------------------------------------------------------

    "Action": "动作",
    "Adventure": "冒险",
    "Casual": "休闲",
    "Puzzle": "解谜",
    "RPG": "RPG",
    "Racing": "竞速",
    "Simulation": "模拟",
    "Sports": "体育",
    "Strategy": "策略",

    "Action RPG": "动作 RPG",
    "Action-Adventure": "动作冒险",
    "Arcade": "街机",
    "Base Building": "基地建造",
    "Board Game": "桌游",
    "Building": "建造",
    "Card Game": "卡牌",
    "Exploration": "探索",
    "Hidden Object": "找物",
    "Horror": "恐怖",
    "Idler": "放置",
    "Interactive Fiction": "互动小说",
    "Management": "经营",
    "Open World": "开放世界",
    "Platformer": "平台跳跃",
    "Point & Click": "点击冒险",
    "Roguelike": "Roguelike",
    "Sandbox": "沙盒",
    "Shooter": "射击",
    "Stealth": "潜行",
    "Survival": "生存",
    "Tower Defense": "塔防",
    "Turn-Based Strategy": "回合制策略",
    "Visual Novel": "视觉小说",
    "Grand Strategy":'大战略',
    "Roguelike Deckbuilder":"Roguelike 卡牌构筑",
    "":"",
    "Colony Sim":"殖民模拟",
    "Walking Simulator": "步行模拟",

    # --------------------------------------------------------
    # 子类型
    # --------------------------------------------------------

    "2D Platformer": "2D 平台跳跃",
    "3D Platformer": "3D 平台跳跃",
    "Tactical RPG": "战术角色扮演", 
    "Action Roguelike": "动作 Roguelike",
    "Card Battler": "卡牌对战",
    "Bullet Hell": "弹幕射击",
    "Choose Your Own Adventure": "互动冒险",
    "Collectathon": "收集探索",
    "Dating Sim": "恋爱模拟",
    "Detective": "侦探",
    "Dungeon Crawler": "迷宫探索",
    "Education": "教育",
    "FPS": "第一人称射击",
    "Hack and Slash": "砍杀",
    "Immersive Sim": "沉浸式模拟",
    "Incremental": "增量游戏",
    "JRPG": "JRPG",
    "Life Sim": "生活模拟",
    "Precision Platformer": "精准平台跳跃",
    "Psychological Horror": "心理恐怖",
    "Puzzle Platformer": "解谜平台跳跃",
    "Roguelite": "Roguelite",
    "Shoot 'Em Up": "纵版射击",
    "Side Scroller": "横版",
    "Survival Horror": "生存恐怖",
    "Third-Person Shooter": "第三人称射击",
    "Top-Down Shooter": "俯视角射击",
    "Turn-Based Tactics": "回合制战术",
    "Sokoban": "推箱子",
    "Open World Survival Craft": "开放世界生存制作",
    "Rhythm": "音乐",

    # --------------------------------------------------------
    # 年代 / 氛围 / 世界观
    # --------------------------------------------------------

    "1980s": "1980 年代",
    "1990's": "1990 年代",
    "Atmospheric": "氛围",
    "Dark": "黑暗",
    "Dark Fantasy": "黑暗奇幻",
    "Demons": "恶魔",
    "Economy": "经济",
    "Family Friendly": "适合家庭",
    "Fantasy": "奇幻",
    "Futuristic": "未来",
    "Historical": "历史",
    "Investigation": "调查",
    "LGBTQ+": "LGBTQ+",
    "Logic": "逻辑",
    "Magic": "魔法",
    "Medieval": "中世纪",
    "Mystery": "悬疑",
    "Nature": "自然",
    "Old School": "复古",
    "Post-apocalyptic": "末日",
    "Retro": "复古",
    "Romance": "恋爱",
    "Sci-fi": "科幻",
    "Space": "太空",
    "Surreal": "超现实",
    "Tactical": "战术",
    "Thriller": "惊悚",
    "War": "战争",
    "Zombies": "僵尸",
    "Wargame": "战争模拟",

    # --------------------------------------------------------
    # 游戏机制
    # --------------------------------------------------------

    "Character Customization": "角色自定义",
    "Choices Matter": "选择影响剧情",
    "Combat": "战斗",
    "Crafting": "制作",
    "Dialogue Heavy": "大量对话",
    "Female Protagonist": "女性主角",
    "Linear": "线性",
    "Multiple Endings": "多结局",
    "Physics": "物理",
    "Procedural Generation": "程序生成",
    "PvE": "PvE",
    "Combat Racing": "战斗竞速",
    "Resource Management": "资源管理",
    "Score Attack": "分数挑战",
    "Time Management": "时间管理",
    "Turn-Based Combat": "回合制战斗",

    # --------------------------------------------------------
    # 视觉风格
    # --------------------------------------------------------

    "2.5D": "2.5D",
    "2D": "2D",
    "3D": "3D",
    "Abstract": "抽象",
    "Anime": "动漫",
    "Cartoon": "卡通",
    "Cartoony": "卡通风格",
    "Cinematic": "电影化",
    "Colorful": "多彩",
    "Cute": "可爱",
    "First-Person": "第一人称",
    "Hand-drawn": "手绘",
    "Isometric": "等距视角",
    "Minimalist": "极简",
    "Pixel Graphics": "像素画风",
    "Realistic": "写实",
    "Stylized": "风格化",
    "Text-Based": "文字游戏",
    "Third Person": "第三人称",
    "Top-Down": "俯视角",

    # --------------------------------------------------------
    # 体验 / 内容
    # --------------------------------------------------------

    "Comedy": "喜剧",
    "Dark Humor": "黑色幽默",
    "Difficult": "高难度",
    "Emotional": "情感丰富",
    "Funny": "搞笑",
    "Great Soundtrack": "优秀原声",
    "Lore-Rich": "丰富世界观",
    "Psychological": "心理",
    "Relaxing": "轻松",
    "Story Rich": "剧情丰富",

    # --------------------------------------------------------
    # 联机
    # --------------------------------------------------------

    "Co-op": "合作",
    "Local Co-Op": "本地合作",
    "Local Multiplayer": "本地多人",
    "Multiplayer": "多人",
    "Online Co-Op": "在线合作",
    "Singleplayer": "单人",

    # --------------------------------------------------------
    # 其他
    # --------------------------------------------------------

    "Controller": "支持手柄",

    "Gore": "血腥",
    "Hentai": "Hentai",
    "Nudity": "裸露",
    "Sexual Content": "色情内容",
    "Violent": "暴力",

    "Early Access": "抢先体验",
    "Free to Play": "免费游玩",
    "Indie": "独立",
}


def translate_tag(tag):
    tag = tag.strip()

    return TAG_TRANSLATIONS.get(
        tag,
        tag
    )


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
    return " ".join(
        text.split()
    )


# ============================================================
# State
# ============================================================

def load_state():

    if not STATE_FILE.exists():
        return set()

    try:

        data = json.loads(
            STATE_FILE.read_text(
                encoding="utf-8"
            )
        )

        return set(
            data.get(
                "pushed",
                []
            )
        )

    except Exception as e:

        print(
            f"读取 state.json 失败：{e}"
        )

        return set()


def save_state(pushed_ids):

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    data = {
        "pushed": list(
            pushed_ids
        )[-500:]
    }

    STATE_FILE.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


# ============================================================
# 找到主榜单
# ============================================================

def get_main_ranking(soup):

    heading = soup.find(
        lambda tag:
        tag.name in {
            "h1",
            "h2",
            "h3"
        }
        and
        "Week Top 50 Games Ranking"
        in clean_text(
            tag.get_text(
                " ",
                strip=True
            )
        )
    )

    if not heading:

        raise RuntimeError(
            "找不到 Week Top 50 Games Ranking"
        )

    ranking = heading.find_next(
        lambda tag:
        tag.name == "section"
        and
        "applist"
        in tag.get(
            "class",
            []
        )
    )

    if not ranking:

        raise RuntimeError(
            "找到 Top 50 标题，但找不到对应的主榜单 section"
        )

    return ranking


# ============================================================
# 好评率
# ============================================================

def parse_rating(review_div):

    meter = review_div.select_one(
        "div.meter.rating"
    )

    if not meter:
        return "N/A"

    rating_span = meter.find(
        "span"
    )

    if rating_span:

        style = rating_span.get(
            "style",
            ""
        )

        match = re.search(
            r"width\s*:\s*([\d.]+%)",
            style,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    text = clean_text(
        meter.get_text(
            " ",
            strip=True
        )
    )

    match = re.search(
        r"(\d+(?:\.\d+)?%)",
        text
    )

    if match:
        return match.group(1)

    return "N/A"


# ============================================================
# Steam250 图片
# ============================================================

def parse_image(row):

    img = row.find(
        "img"
    )

    if not img:
        return None

    # Steam250 当前实际图片
    image_url = (
        img.get("data-src")
        or
        img.get("src")
    )

    if not image_url:
        return None

    if image_url.startswith("//"):

        image_url = (
            "https:"
            + image_url
        )

    elif image_url.startswith("/"):

        image_url = (
            "https://steam250.com"
            + image_url
        )

    return image_url


# ============================================================
# 从 Steam 商店 URL 获取 AppID
# ============================================================

def get_steam_appid(store_url):

    match = re.search(
        r"/app/(\d+)",
        store_url
    )

    if match:
        return match.group(1)

    return None


# ============================================================
# Steam Header 图片备用方案
# ============================================================

def get_fallback_image(store_url):

    appid = get_steam_appid(
        store_url
    )

    if not appid:
        return None

    return (
        "https://shared.cloudflare.steamstatic.com/"
        f"store_item_assets/steam/apps/{appid}/header.jpg"
    )


# ============================================================
# 解析游戏
# ============================================================

def parse_game(row):

    # --------------------------------------------------------
    # 1. 必须是 New
    # --------------------------------------------------------

    rank_div = row.find(
        "div",
        class_="rank",
        recursive=False
    )

    if not rank_div:
        return None

    new_marker = rank_div.find(
        "span",
        attrs={
            "title": "New entry"
        }
    )

    if not new_marker:
        return None

    # --------------------------------------------------------
    # 2. 标题
    # --------------------------------------------------------

    title_div = row.find(
        "div",
        class_="title",
        recursive=False
    )

    if not title_div:
        return None

    title_link = title_div.find(
        "a",
        title=True
    )

    if not title_link:
        return None

    name = clean_text(
        title_link.get_text(
            " ",
            strip=True
        )
    )

    if not name:
        return None

    # --------------------------------------------------------
    # 3. Steam 商店链接
    # --------------------------------------------------------

    actions_div = row.find(
        "div",
        class_="actions",
        recursive=False
    )

    if not actions_div:
        return None

    store_link = actions_div.find(
        "a",
        class_="store"
    )

    if not store_link:
        return None

    store_url = store_link.get(
        "href"
    )

    if not store_url:
        return None

    # --------------------------------------------------------
    # 4. Free 排除
    # --------------------------------------------------------

    price_div = row.find(
        "div",
        class_="price",
        recursive=False
    )

    if not price_div:
        return None

    free_marker = price_div.find(
        "a",
        class_="free"
    )

    if free_marker:

        print(
            f"排除 Free：{name}"
        )

        return None

    # --------------------------------------------------------
    # 5. Adult only 排除
    # --------------------------------------------------------

    adult_marker = row.find(
        "a",
        href="/adult",
        title="Adult only"
    )

    if adult_marker:

        print(
            f"排除 Adult only：{name}"
        )

        return None

    # --------------------------------------------------------
    # 6. Steam250 标签
    # --------------------------------------------------------

    tags = [
        clean_text(
            tag.get_text(
                " ",
                strip=True
            )
        )
        for tag in title_div.select(
            "a.tag"
        )
    ]

    # --------------------------------------------------------
    # 7. 排除指定标签
    # --------------------------------------------------------

    excluded = [
        tag
        for tag in tags
        if tag in EXCLUDED_TAGS
    ]

    if excluded:

        print(
            f"排除指定标签：{name} "
            f"({', '.join(excluded)})"
        )

        return None

    # --------------------------------------------------------
    # 8. 中文标签
    #
    # 最多显示三个
    # --------------------------------------------------------

    translated_tags = [
        translate_tag(tag)
        for tag in tags
    ]

    translated_tags = translated_tags[:3]

    # --------------------------------------------------------
    # 9. 评论数 + 好评率
    # --------------------------------------------------------

    review_div = row.find(
        "div",
        class_="reviews",
        recursive=False
    )

    votes = "N/A"
    rating = "N/A"

    if review_div:

        votes_span = review_div.select_one(
            "span.votes"
        )

        if votes_span:

            votes = clean_text(
                votes_span.get_text(
                    " ",
                    strip=True
                )
            )

        rating = parse_rating(
            review_div
        )

    # --------------------------------------------------------
    # 10. 当前价格
    #
    # 只取第一个 span
    # --------------------------------------------------------

    price_spans = price_div.find_all(
        "span",
        recursive=False
    )

    if not price_spans:
        return None

    price = clean_text(
        price_spans[0].get_text(
            " ",
            strip=True
        )
    )

    if not price:
        return None

    # --------------------------------------------------------
    # 11. 图片
    #
    # 第一优先：
    # Steam250 当前页面的真实图片
    #
    # 第二优先：
    # Steam header.jpg
    # --------------------------------------------------------

    image_url = parse_image(
        row
    )

    if not image_url:

        image_url = get_fallback_image(
            store_url
        )

    # --------------------------------------------------------
    # 12. 返回
    # --------------------------------------------------------

    return {
        "id": store_url,
        "name": name,
        "url": store_url,
        "votes": votes,
        "rating": rating,
        "price": price,
        "tags": translated_tags,
        "image": image_url,
    }


# ============================================================
# 获取主榜单 New
# ============================================================

def fetch_new_games():

    print(
        "========================================"
    )

    print(
        "[1/5] Fetching Steam250..."
    )

    response = requests.get(
        STEAM250_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    print(
        "[2/5] Locating main Top 50 ranking..."
    )

    ranking = get_main_ranking(
        soup
    )

    games = []

    # 只读取主榜单的直接子元素
    # 因此不会抓到左侧 New 小区域
    rows = ranking.find_all(
        "div",
        recursive=False
    )

    print(
        f"[3/5] Main ranking rows: {len(rows)}"
    )

    for row in rows:

        game = parse_game(
            row
        )

        if game:

            games.append(
                game
            )

    print(
        f"[4/5] Qualified New games: {len(games)}"
    )

    return games


# ============================================================
# Discord Embed
# ============================================================

def create_embed(game):

    # --------------------------------------------------------
    # 文字内容
    # --------------------------------------------------------

    description = (
        f"{game['votes']} 评论数 · "
        f"{game['rating']} 好评率\n"
        f"💰 {game['price']}"
    )

    if game["tags"]:

        description += (
            "\n🏷️ "
            +
            " · ".join(
                game["tags"]
            )
        )

    # --------------------------------------------------------
    # Embed
    # --------------------------------------------------------

    embed = {
        "title": f"🆕 {game['name']}",
        "url": game["url"],
        "description": description,

        "footer": {
            "text": "Steam250 · New Entry"
        }
    }

    # --------------------------------------------------------
    # 大图
    # --------------------------------------------------------

    if game.get("image"):

        embed["image"] = {
            "url": game["image"]
        }

    return embed


# ============================================================
# Discord 推送
# ============================================================

def send_discord(games):

    if not games:
        return

    if not WEBHOOK_URL:

        raise RuntimeError(
            "未设置 STEAM250_DISCORD_WEBHOOK"
        )

    # Discord Webhook 一条消息最多 10 个 Embed
    for start in range(
        0,
        len(games),
        10
    ):

        batch = games[
            start:start + 10
        ]

        payload = {
            "username": "Steam250",

            "embeds": [
                create_embed(game)
                for game in batch
            ]
        }

        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        print(
            f"Discord message sent: "
            f"{len(batch)} embeds"
        )


# ============================================================
# Main
# ============================================================

def main():

    print(
        "Steam250 New Games"
    )

    print(
        "========================================"
    )

    games = fetch_new_games()

    if not games:

        print(
            "没有符合条件的 New 游戏。"
        )

        return

    pushed_ids = load_state()

    new_games = []

    print(
        "========================================"
    )

    print(
        "[5/5] Checking pushed state..."
    )

    for game in games:

        if game["id"] in pushed_ids:

            print(
                f"跳过已推送："
                f"{game['name']}"
            )

            continue

        new_games.append(
            game
        )

    print(
        f"本次待推送："
        f"{len(new_games)}"
    )

    if not new_games:

        print(
            "没有新的待推送游戏。"
        )

        return

    # --------------------------------------------------------
    # 输出日志
    # --------------------------------------------------------

    print(
        "========================================"
    )

    for game in new_games:

        print(
            f"推送：{game['name']} | "
            f"{game['votes']} 评论数 | "
            f"{game['rating']} 好评率 | "
            f"{game['price']}"
        )

        print(
            f"  Steam: {game['url']}"
        )

        print(
            f"  Image: {game['image']}"
        )

        if game["tags"]:

            print(
                f"  Tags: "
                f"{' · '.join(game['tags'])}"
            )

    # --------------------------------------------------------
    # Discord
    # --------------------------------------------------------

    send_discord(
        new_games
    )

    # --------------------------------------------------------
    # 更新 state
    # --------------------------------------------------------

    for game in new_games:

        pushed_ids.add(
            game["id"]
        )

    save_state(
        pushed_ids
    )

    print(
        "========================================"
    )

    print(
        "Discord 推送完成。"
    )

    print(
        "State saved."
    )


if __name__ == "__main__":
    main()
