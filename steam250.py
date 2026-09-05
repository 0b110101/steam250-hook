import json
import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup


STEAM250_URL = "https://steam250.com/7day"
STATE_FILE = Path("data/steam250_state.json")

DISCORD_WEBHOOK = os.environ.get("STEAM250_DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
}


# ============================================================
# 基础工具
# ============================================================

def clean_text(text):
    return " ".join(text.split()).strip()


def fetch_page():
    response = requests.get(
        STEAM250_URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


# ============================================================
# 找主榜单
# ============================================================

def find_main_ranking(soup):
    """
    Steam250 /7day 的主榜单结构：

    <section class="applist compact no-wl anim8">
        <header>...</header>

        <div id="1">...</div>
        <div id="2">...</div>
        ...

    页面左侧还有一个独立的 New entries 区域。

    这里严格只寻找：
        Week Top 50 Games Ranking

    标题之后对应的主榜单 section。

    不读取左侧 New entries。
    """

    heading = soup.find(
        lambda tag:
        tag.name in {"h1", "h2", "h3"}
        and "Week Top 50 Games Ranking"
        in clean_text(tag.get_text(" ", strip=True))
    )

    if heading is None:
        raise RuntimeError(
            "找不到 'Week Top 50 Games Ranking'。"
        )

    # 标题之后寻找 class 包含 applist 的 section
    ranking = heading.find_next(
        "section",
        class_=lambda classes: (
            classes
            and "applist" in classes
        ),
    )

    if ranking is None:
        raise RuntimeError(
            "找到 Top 50 标题，但找不到对应的 "
            "applist 主榜单。"
        )

    return ranking


# ============================================================
# 解析主榜单
# ============================================================

def parse_main_ranking(ranking):
    """
    只解析主榜单 section。

    New 的判断方式：

        <div class="rank">
            <span title="New entry">New</span>
            3
        </div>

    所以严格判断：
        span[title="New entry"]

    不搜索整个页面的 New。
    """

    games = []

    # 主榜单的每个游戏都是直接位于 section 下的 div
    rows = ranking.find_all(
        "div",
        recursive=False,
    )

    for row in rows:

        # ----------------------------------------------------
        # 必须是游戏行
        # ----------------------------------------------------

        rank_div = row.find(
            "div",
            class_="rank",
            recursive=False,
        )

        if rank_div is None:
            continue

        # ----------------------------------------------------
        # 判断 New
        # ----------------------------------------------------

        new_marker = rank_div.find(
            "span",
            attrs={
                "title": "New entry"
            },
        )

        if new_marker is None:
            continue

        # ----------------------------------------------------
        # Rank
        # ----------------------------------------------------

        rank = None

        rank_text = clean_text(
            rank_div.get_text(" ", strip=True)
        )

        # 例如：
        # "New 3"
        # "3"
        parts = rank_text.split()

        for part in reversed(parts):
            if part.isdigit():
                rank = int(part)
                break

        # ----------------------------------------------------
        # Game title
        # ----------------------------------------------------

        title_div = row.find(
            "div",
            class_="title",
            recursive=False,
        )

        if title_div is None:
            continue

        game_link = title_div.find(
            "a",
            href=True,
        )

        if game_link is None:
            continue

        game_name = clean_text(
            game_link.get_text(" ", strip=True)
        )

        if not game_name:
            continue

        game_url = game_link["href"].strip()

        # ----------------------------------------------------
        # Steam250 Game URL
        # ----------------------------------------------------

        if game_url.startswith("/"):
            game_url = (
                "https://steam250.com"
                + game_url
            )

        # ----------------------------------------------------
        # Score
        # ----------------------------------------------------

        score_div = row.find(
            "div",
            class_="score",
            recursive=False,
        )

        score = None

        if score_div:
            score_span = score_div.find("span")

            if score_span:
                score = clean_text(
                    score_span.get_text(
                        " ",
                        strip=True,
                    )
                )

        # ----------------------------------------------------
        # Reviews
        # ----------------------------------------------------

        reviews_div = row.find(
            "div",
            class_="reviews",
            recursive=False,
        )

        reviews = None

        if reviews_div:

            votes = reviews_div.find(
                "span",
                class_="votes",
            )

            if votes:
                reviews = clean_text(
                    votes.get_text(
                        " ",
                        strip=True,
                    )
                )

        # ----------------------------------------------------
        # Price
        # ----------------------------------------------------

        price_div = row.find(
            "div",
            class_="price",
            recursive=False,
        )

        price_text = ""

        if price_div:
            price_text = clean_text(
                price_div.get_text(
                    " ",
                    strip=True,
                )
            )

        # ----------------------------------------------------
        # Tags
        # ----------------------------------------------------

        tags = []

        for tag in title_div.select(
            "div a.tag"
        ):
            tag_name = clean_text(
                tag.get_text(
                    " ",
                    strip=True,
                )
            )

            if tag_name:
                tags.append(tag_name)

        # 去重
        tags = list(
            dict.fromkeys(tags)
        )

        # ----------------------------------------------------
        # Free
        # ----------------------------------------------------

        is_free = False

        if "free" in price_text.lower():
            is_free = True

        # ----------------------------------------------------
        # Adult only
        # ----------------------------------------------------

        row_text = clean_text(
            row.get_text(
                " ",
                strip=True,
            )
        )

        is_adult_only = (
            "adult only" in row_text.lower()
        )

        # ----------------------------------------------------
        # Horror
        # ----------------------------------------------------

        has_horror = any(
            "horror" in tag.lower()
            for tag in tags
        )

        game = {
            "rank": rank,
            "name": game_name,
            "score": score,
            "reviews": reviews,
            "price": price_text,
            "tags": tags,
            "url": game_url,
            "is_free": is_free,
            "is_adult_only": is_adult_only,
            "has_horror": has_horror,
        }

        games.append(game)

    return games


# ============================================================
# 过滤
# ============================================================

def filter_games(games):

    result = []

    for game in games:

        if game["is_free"]:
            print(
                f"[FILTER] Price free -> "
                f"{game['name']}"
            )
            continue

        if game["is_adult_only"]:
            print(
                f"[FILTER] Adult only -> "
                f"{game['name']}"
            )
            continue

        if game["has_horror"]:
            print(
                f"[FILTER] Horror -> "
                f"{game['name']} "
                f"| tags={game['tags']}"
            )
            continue

        result.append(game)

    return result


# ============================================================
# State
# ============================================================

def load_state():

    if not STATE_FILE.exists():
        return {
            "pushed_games": []
        }

    try:

        with STATE_FILE.open(
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {
                "pushed_games": []
            }

        if "pushed_games" not in data:
            data["pushed_games"] = []

        return data

    except Exception as e:

        print(
            f"[WARNING] Failed to load state: {e}"
        )

        return {
            "pushed_games": []
        }


def save_state(state):

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with STATE_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2,
        )


def get_game_id(game):

    if game["url"]:
        return game["url"]

    return game["name"].strip().lower()


# ============================================================
# Discord
# ============================================================

def build_discord_embeds(games):

    chunks = []

    current_lines = []
    current_length = 0

    for game in games:

        rank = (
            str(game["rank"])
            if game["rank"] is not None
            else "?"
        )

        score = (
            game["score"]
            if game["score"]
            else "N/A"
        )

        name = game["name"]

        if game["url"]:

            line = (
                f"🆕 **#{rank}** "
                f"[{name}]({game['url']}) "
                f"— **{score}**"
            )

        else:

            line = (
                f"🆕 **#{rank}** "
                f"**{name}** "
                f"— **{score}**"
            )

        new_length = (
            current_length
            + len(line)
            + 1
        )

        if (
            current_lines
            and new_length > 3800
        ):

            chunks.append(
                "\n".join(current_lines)
            )

            current_lines = []
            current_length = 0

        current_lines.append(line)

        current_length += (
            len(line) + 1
        )

    if current_lines:

        chunks.append(
            "\n".join(current_lines)
        )

    embeds = []

    for index, description in enumerate(
        chunks
    ):

        if index == 0:

            title = (
                "🎮 Steam250 — New Entries"
            )

        else:

            title = (
                "🎮 Steam250 — New Entries "
                f"({index + 1}/{len(chunks)})"
            )

        embeds.append(
            {
                "title": title,
                "description": description,
                "url": STEAM250_URL,
                "footer": {
                    "text": (
                        "Steam250 7-day · "
                        "主榜单 New"
                    )
                },
            }
        )

    return embeds


def send_discord(games):

    if not DISCORD_WEBHOOK:
        raise RuntimeError(
            "没有设置 "
            "STEAM250_DISCORD_WEBHOOK"
        )

    embeds = build_discord_embeds(
        games
    )

    if len(embeds) > 10:
        raise RuntimeError(
            "New 游戏数量过多，"
            "Discord Embed 超过 10 个。"
        )

    payload = {
        "embeds": embeds
    }

    response = requests.post(
        DISCORD_WEBHOOK,
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    print(
        f"[DISCORD] Sent "
        f"{len(games)} game(s)"
    )


# ============================================================
# Main
# ============================================================

def main():

    print(
        "========================================"
    )
    print(
        "Steam250 New Games"
    )
    print(
        "========================================"
    )

    # --------------------------------------------------------
    # 1. Fetch
    # --------------------------------------------------------

    print(
        "[1/5] Fetching Steam250..."
    )

    html = fetch_page()

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # --------------------------------------------------------
    # 2. Main ranking
    # --------------------------------------------------------

    print(
        "[2/5] Locating main Top 50 ranking..."
    )

    ranking = find_main_ranking(
        soup
    )

    # --------------------------------------------------------
    # 3. New
    # --------------------------------------------------------

    print(
        "[3/5] Parsing New entries..."
    )

    new_games = parse_main_ranking(
        ranking
    )

    print(
        f"[INFO] Main ranking New entries: "
        f"{len(new_games)}"
    )

    if not new_games:

        print(
            "[INFO] No New entries."
        )

        return

    for game in new_games:

        print(
            f"[NEW] "
            f"#{game['rank']} "
            f"{game['name']} "
            f"| score={game['score']} "
            f"| reviews={game['reviews']} "
            f"| price={game['price']} "
            f"| tags={game['tags']}"
        )

    # --------------------------------------------------------
    # 4. Filters
    # --------------------------------------------------------

    print(
        "[4/5] Applying filters..."
    )

    filtered_games = filter_games(
        new_games
    )

    print(
        f"[INFO] After filtering: "
        f"{len(filtered_games)}"
    )

    if not filtered_games:

        print(
            "[INFO] No games remain "
            "after filtering."
        )

        return

    # --------------------------------------------------------
    # 5. Duplicate protection
    # --------------------------------------------------------

    state = load_state()

    pushed_games = set(
        state.get(
            "pushed_games",
            [],
        )
    )

    games_to_send = []

    for game in filtered_games:

        game_id = get_game_id(game)

        if game_id in pushed_games:

            print(
                f"[SKIP] Already pushed: "
                f"{game['name']}"
            )

            continue

        games_to_send.append(game)

    if not games_to_send:

        print(
            "[INFO] All matching New games "
            "have already been pushed."
        )

        return

    # --------------------------------------------------------
    # Discord
    # --------------------------------------------------------

    print(
        "[5/5] Sending Discord notification..."
    )

    send_discord(
        games_to_send
    )

    # --------------------------------------------------------
    # Save state
    # --------------------------------------------------------

    for game in games_to_send:

        pushed_games.add(
            get_game_id(game)
        )

    # 最多保存最近 500 个
    state["pushed_games"] = list(
        pushed_games
    )[-500:]

    save_state(state)

    print(
        "[INFO] State saved."
    )

    print(
        "========================================"
    )
    print(
        "Done."
    )
    print(
        "========================================"
    )


if __name__ == "__main__":
    main()
