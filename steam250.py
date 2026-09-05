import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


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
# Steam250 标签中文翻译
# ============================================================

TAG_TRANSLATIONS = {
    "Roguelike Deckbuilder": "Roguelike 卡牌构筑",
    "Souls-like": "类魂",
    "Action": "动作",
    "RPG": "RPG",
    "Strategy": "策略",
    "Adventure": "冒险",
    "Indie": "独立",
    "Simulation": "模拟",
    "Casual": "休闲",
    "Puzzle": "解谜",
    "Platformer": "平台",
    "Early Access": "抢先体验",
    "Turn-Based": "回合制",
    "Survival": "生存",
    "Open World": "开放世界",
    "Singleplayer": "单人",
    "Multiplayer": "多人",
    "Co-op": "合作",
    "Online Co-Op": "在线合作",
    "Local Co-Op": "本地合作",
    "FPS": "第一人称射击",
    "Third Person": "第三人称",
    "Shooter": "射击",
    "Horror": "恐怖",
    "Psychological Horror": "心理恐怖",
    "Survival Horror": "生存恐怖",
    "Racing": "竞速",
    "Sports": "体育",
    "Fighting": "格斗",
    "Arcade": "街机",
    "Card Game": "卡牌游戏",
    "Deckbuilder": "卡组构筑",
    "Roguelike": "Roguelike",
    "Roguelite": "Roguelite",
    "Metroidvania": "银河恶魔城",
    "Hack and Slash": "砍杀",
    "CRPG": "CRPG",
    "JRPG": "JRPG",
    "RTS": "即时战略",
    "Turn-Based Strategy": "回合制策略",
    "City Builder": "城市建造",
    "Sandbox": "沙盒",
    "Story Rich": "剧情丰富",
    "Atmospheric": "氛围",
    "Funny": "搞笑",
    "Relaxing": "轻松",
    "Cute": "可爱",
    "Dark": "黑暗",
    "Fantasy": "奇幻",
    "Sci-fi": "科幻",
    "Sci-Fi": "科幻",
    "Mystery": "悬疑",
    "Exploration": "探索",
    "Building": "建造",
    "Crafting": "制作",
    "Resource Management": "资源管理",
    "Management": "经营管理",
    "Tactical": "战术",
    "Stealth": "潜行",
    "Psychological": "心理",
    "Choices Matter": "选择影响剧情",
    "Multiple Endings": "多结局",
}


def translate_tag(tag):
    """
    Steam250 标签中文化。

    优先使用精确映射；
    没有映射时保留原文，避免错误翻译。
    """

    tag = tag.strip()

    if tag in TAG_TRANSLATIONS:
        return TAG_TRANSLATIONS[tag]

    return tag


def clean_text(text):
    return " ".join(text.split())


# ============================================================
# State
# ============================================================

def load_state():
    if not STATE_FILE.exists():
        return set()

    try:
        data = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )

        return set(data.get("pushed", []))

    except Exception:
        return set()


def save_state(pushed_ids):
    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    data = {
        "pushed": list(pushed_ids)[-500:]
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
# 找到 Steam250 主榜单
# ============================================================

def get_main_ranking(soup):
    """
    只定位 Week Top 50 Games Ranking 对应的主榜单。

    不读取：
    - 左侧 New entries
    - Daily movement
    - 页面其他区域
    """

    heading = soup.find(
        lambda tag:
        tag.name in {"h1", "h2", "h3"}
        and
        "Week Top 50 Games Ranking"
        in clean_text(
            tag.get_text(" ", strip=True)
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
        "applist" in tag.get("class", [])
    )

    if not ranking:
        raise RuntimeError(
            "找到 Top 50 标题，但找不到对应的主榜单 section"
        )

    return ranking


# ============================================================
# 解析好评率
# ============================================================

def parse_rating(review_div):
    """
    从：

    <div class="meter rating">
        <span style="width: 100%"></span>
        100%
    </div>

    获取：

    100%
    """

    meter = review_div.select_one(
        "div.meter.rating"
    )

    if not meter:
        return "N/A"

    rating_span = meter.find("span")

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

    # 备用方案
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
# 获取 Steam 图片
# ============================================================

def parse_image(row):
    """
    Steam250 中：

    <img
        alt="logo"
        class="lazy entered loaded"
        data-src="//shared.cloudflare.steamstatic.com/..."
        src="//shared.cloudflare.steamstatic.com/..."
    >

    优先使用 data-src。
    """

    img = row.find(
        "img",
        class_=lambda classes:
        classes and "lazy" in classes
    )

    if not img:
        return None

    image_url = (
        img.get("data-src")
        or
        img.get("src")
    )

    if not image_url:
        return None

    # //shared.cloudflare...
    if image_url.startswith("//"):
        image_url = "https:" + image_url

    elif image_url.startswith("/"):
        image_url = "https://steam250.com" + image_url

    return image_url


# ============================================================
# 解析游戏
# ============================================================

def parse_game(row):

    # --------------------------------------------------------
    # 1. 只接受 New
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
    # 2. 游戏标题
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
    #
    # 不使用：
    # club.steam250.com/app/xxxx
    #
    # 使用：
    # actions.stat > a.store
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

    store_url = store_link.get("href")

    if not store_url:
        return None

    # --------------------------------------------------------
    # 4. 排除 Free
    #
    # Steam250 Free 的实际 HTML：
    #
    # <div class="price stat">
    #     <a class="free">Free</a>
    # </div>
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
    # 5. 排除 Adult only
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
    # 6. 获取 Steam250 标签
    # --------------------------------------------------------

    tags = [
        clean_text(
            tag.get_text(
                " ",
                strip=True
            )
        )
        for tag in title_div.select("a.tag")
    ]

    # --------------------------------------------------------
    # 7. 排除 Horror
    # --------------------------------------------------------

    if any(
        "horror" in tag.lower()
        for tag in tags
    ):
        print(
            f"排除 Horror：{name}"
        )
        return None

    # --------------------------------------------------------
    # 8. 标签翻译
    #
    # 最多显示 3 个
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
    # 11. Steam Capsule 图片
    # --------------------------------------------------------

    image_url = parse_image(row)

    # --------------------------------------------------------
    # 返回
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
# 获取 New 游戏
# ============================================================

def fetch_new_games():

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

    ranking = get_main_ranking(
        soup
    )

    games = []

    # 只读取主榜单直接子元素
    rows = ranking.find_all(
        "div",
        recursive=False
    )

    for row in rows:

        game = parse_game(row)

        if game:
            games.append(game)

    return games


# ============================================================
# 创建 Discord Embed
# ============================================================

def create_embed(game):

    # ---------------------------------------------
    # Description
    # ---------------------------------------------

    description = (
        f"{game['votes']} 评论数 · "
        f"{game['rating']} 好评率\n"
        f"💰 {game['price']}"
    )

    # ---------------------------------------------
    # 标签
    # ---------------------------------------------

    if game["tags"]:

        description += (
            "\n🏷️ "
            +
            " · ".join(
                game["tags"]
            )
        )

    # ---------------------------------------------
    # Embed
    # ---------------------------------------------

    embed = {
        "title": f"🆕 {game['name']}",
        "url": game["url"],
        "description": description,
        "footer": {
            "text": "Steam250 · New Entry"
        }
    }

    # ---------------------------------------------
    # Steam Capsule
    # ---------------------------------------------

    if game.get("image"):

        embed["thumbnail"] = {
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

    # Discord webhook：
    # 一次最多 10 个 embeds
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


# ============================================================
# Main
# ============================================================

def main():

    games = fetch_new_games()

    print(
        f"主榜单发现符合条件的 New：{len(games)}"
    )

    if not games:
        print(
            "没有符合条件的 New 游戏。"
        )
        return

    pushed_ids = load_state()

    new_games = []

    for game in games:

        if game["id"] in pushed_ids:

            print(
                f"跳过已推送：{game['name']}"
            )

            continue

        new_games.append(game)

    print(
        f"本次待推送：{len(new_games)}"
    )

    if not new_games:

        print(
            "没有新的待推送游戏。"
        )

        return

    # --------------------------------------------------------
    # 推送前日志
    # --------------------------------------------------------

    for game in new_games:

        print(
            f"推送：{game['name']} | "
            f"{game['votes']} 评论数 | "
            f"{game['rating']} 好评率 | "
            f"{game['price']} | "
            f"{game['url']}"
        )

    # --------------------------------------------------------
    # Discord
    # --------------------------------------------------------

    send_discord(
        new_games
    )

    # --------------------------------------------------------
    # 更新状态
    # --------------------------------------------------------

    for game in new_games:

        pushed_ids.add(
            game["id"]
        )

    save_state(
        pushed_ids
    )

    print(
        "Discord 推送完成。"
    )


if __name__ == "__main__":
    main()
