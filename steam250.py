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


def clean_text(text):
    return " ".join(text.split())


def load_state():
    if not STATE_FILE.exists():
        return set()

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(data.get("pushed", []))
    except Exception:
        return set()


def save_state(pushed_ids):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "pushed": list(pushed_ids)[-500:]
    }

    STATE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_main_ranking(soup):
    """
    只定位 Week Top 50 Games Ranking 对应的主榜单。
    不读取左侧 New entries，也不扫描整个页面。
    """

    heading = soup.find(
        lambda tag:
        tag.name in {"h1", "h2", "h3"}
        and "Week Top 50 Games Ranking"
        in clean_text(tag.get_text(" ", strip=True))
    )

    if not heading:
        raise RuntimeError("找不到 Week Top 50 Games Ranking")

    ranking = heading.find_next(
        lambda tag:
        tag.name == "section"
        and "applist" in tag.get("class", [])
    )

    if not ranking:
        raise RuntimeError("找到 Top 50 标题，但找不到对应的主榜单 section")

    return ranking


def parse_rating(review_div):
    """
    从：
    <div class="meter rating">
        <span style="width: 100%"></span>
        100%
    </div>

    提取 100%
    """

    meter = review_div.select_one("div.meter.rating")

    if not meter:
        return "N/A"

    rating_span = meter.find("span")

    if rating_span:
        style = rating_span.get("style", "")

        match = re.search(
            r"width\s*:\s*([\d.]+%)",
            style,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    # 备用：从可见文本中提取百分比
    text = clean_text(meter.get_text(" ", strip=True))

    match = re.search(r"(\d+(?:\.\d+)?%)", text)

    if match:
        return match.group(1)

    return "N/A"


def parse_game(row):
    # --------------------------------------------------
    # 1. 必须是 New
    # --------------------------------------------------

    rank_div = row.find("div", class_="rank", recursive=False)

    if not rank_div:
        return None

    new_marker = rank_div.find(
        "span",
        attrs={"title": "New entry"}
    )

    if not new_marker:
        return None

    # --------------------------------------------------
    # 2. 游戏标题
    # --------------------------------------------------

    title_div = row.find("div", class_="title", recursive=False)

    if not title_div:
        return None

    title_link = title_div.find("a", title=True)

    if not title_link:
        return None

    name = clean_text(title_link.get_text(" ", strip=True))

    if not name:
        return None

    # --------------------------------------------------
    # 3. Steam 商店链接
    #
    # 不使用 title 里的 club.steam250.com 链接
    # 改用：
    # <div class="actions stat">
    #     <a class="store" href="https://store.steampowered.com/...">
    # --------------------------------------------------

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

    # --------------------------------------------------
    # 4. Free 排除
    #
    # Steam250 免费游戏实际结构：
    #
    # <div class="price stat">
    #     <a class="free">Free</a>
    # </div>
    #
    # 所以直接检测 a.free
    # --------------------------------------------------

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
        return None

    # --------------------------------------------------
    # 5. Adult only 排除
    # --------------------------------------------------

    adult_marker = row.find(
        "a",
        href="/adult",
        title="Adult only"
    )

    if adult_marker:
        return None

    # --------------------------------------------------
    # 6. Horror 标签排除
    #
    # 只检查当前游戏 title 区域的 tag
    # --------------------------------------------------

    tags = [
        clean_text(tag.get_text(" ", strip=True))
        for tag in title_div.select("a.tag")
    ]

    if any("horror" in tag.lower() for tag in tags):
        return None

    # --------------------------------------------------
    # 7. Reviews 数量
    # --------------------------------------------------

    review_div = row.find(
        "div",
        class_="reviews",
        recursive=False
    )

    votes = "N/A"
    rating = "N/A"

    if review_div:
        votes_span = review_div.select_one("span.votes")

        if votes_span:
            votes = clean_text(
                votes_span.get_text(" ", strip=True)
            )

        rating = parse_rating(review_div)

    # --------------------------------------------------
    # 8. 当前价格
    #
    # 只取 price.stat 下的第一个 span
    #
    # $4.79 $5.99
    #   ↑
    # 只取这个
    # --------------------------------------------------

    price_spans = price_div.find_all(
        "span",
        recursive=False
    )

    if not price_spans:
        return None

    price = clean_text(
        price_spans[0].get_text(" ", strip=True)
    )

    if not price:
        return None

    return {
        "id": store_url,
        "name": name,
        "url": store_url,
        "votes": votes,
        "rating": rating,
        "price": price,
        "tags": tags,
    }


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

    ranking = get_main_ranking(soup)

    games = []

    # 只遍历主榜单 section 的直接子 div
    # 不碰页面其他 New entries 区域
    rows = ranking.find_all(
        "div",
        recursive=False
    )

    for row in rows:
        game = parse_game(row)

        if game:
            games.append(game)

    return games


def send_discord(games):
    if not games:
        return

    if not WEBHOOK_URL:
        raise RuntimeError(
            "未设置 STEAM250_DISCORD_WEBHOOK"
        )

    # --------------------------------------------------
    # 输出格式：
    #
    # 🆕 [Order Automatica](Steam商店链接) — 21/100% -$4.79
    #
    # 不显示 Steam250 Score
    # 不显示排名
    # --------------------------------------------------

    lines = []

    for game in games:
        line = (
            f"🆕 [{game['name']}]({game['url']})"
            f" — {game['votes']}/{game['rating']}"
            f" -{game['price']}"
        )

        lines.append(line)

    # Discord 单条 embed description 有长度限制，
    # 做简单分块。
    chunks = []
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > 3800:
            if current:
                chunks.append(current)

            current = line
        else:
            if current:
                current += "\n"

            current += line

    if current:
        chunks.append(current)

    for chunk in chunks:
        payload = {
            "embeds": [
                {
                    "title": "🎮 Steam250 — New Entries",
                    "description": chunk,
                    "footer": {
                        "text": "Steam250 7-day · 主榜单 New"
                    }
                }
            ]
        }

        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            timeout=30
        )

        response.raise_for_status()


def main():
    games = fetch_new_games()

    print(f"主榜单发现 New：{len(games)}")

    if not games:
        print("没有符合条件的 New 游戏。")
        return

    pushed_ids = load_state()

    new_games = []

    for game in games:
        if game["id"] in pushed_ids:
            print(f"跳过已推送：{game['name']}")
            continue

        new_games.append(game)

    print(f"本次待推送：{len(new_games)}")

    if not new_games:
        print("没有新的待推送游戏。")
        return

    for game in new_games:
        print(
            f"推送：{game['name']} | "
            f"{game['votes']}/{game['rating']} | "
            f"-{game['price']} | "
            f"{game['url']}"
        )

    send_discord(new_games)

    for game in new_games:
        pushed_ids.add(game["id"])

    save_state(pushed_ids)

    print("Discord 推送完成。")


if __name__ == "__main__":
    main()
