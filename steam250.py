import json
import os
import re
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
# 基础
# ============================================================

def fetch_page():
    response = requests.get(
        STEAM250_URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


def clean_text(text):
    return " ".join(text.split()).strip()


# ============================================================
# 找到主榜单
# ============================================================

def find_main_ranking_table(soup):
    """
    只定位：

        Week Top 50 Games Ranking

    标题下面的主榜单 table。

    不扫描整个页面，因此左侧的
    New entries 区域不会被抓取。
    """

    heading = soup.find(
        lambda tag:
        tag.name in {"h1", "h2", "h3"}
        and "Week Top 50 Games Ranking"
        in clean_text(tag.get_text(" ", strip=True))
    )

    if heading is None:
        raise RuntimeError(
            "找不到 'Week Top 50 Games Ranking'，"
            "Steam250 页面结构可能发生变化。"
        )

    # 主榜单应该位于这个标题之后的第一个 table。
    table = heading.find_next("table")

    if table is None:
        raise RuntimeError(
            "找到 Top 50 标题，但找不到对应的主榜单 table。"
        )

    return table


# ============================================================
# 解析主榜单
# ============================================================

def parse_main_ranking(table):
    """
    只解析主 Top 50 table。

    每个游戏对应一个 <tr>。

    只保留主榜单中明确带 New 的游戏。
    """

    games = []

    rows = table.find_all("tr")

    for row in rows:
        row_text = clean_text(
            row.get_text(" ", strip=True)
        )

        if not row_text:
            continue

        # ----------------------------------------------------
        # 只处理带 New 的行
        # ----------------------------------------------------

        if not re.search(
            r"\bNew\b",
            row_text,
            re.IGNORECASE,
        ):
            continue

        # ----------------------------------------------------
        # 找单元格
        # ----------------------------------------------------

        cells = row.find_all(["td", "th"])

        if not cells:
            continue

        cell_texts = [
            clean_text(cell.get_text(" ", strip=True))
            for cell in cells
        ]

        # ----------------------------------------------------
        # 找排名
        # ----------------------------------------------------

        rank = None

        for cell_text in cell_texts:
            match = re.fullmatch(
                r"\d{1,2}",
                cell_text,
            )

            if match:
                rank = int(match.group())
                break

        # ----------------------------------------------------
        # 找游戏链接
        # ----------------------------------------------------

        game_link = None

        for a in row.find_all("a", href=True):
            name = clean_text(
                a.get_text(" ", strip=True)
            )

            href = a["href"].strip()

            if not name:
                continue

            # Steam250 游戏链接一般是 club.steam250.com
            # 这里排除明显的标签/日期/排名链接。
            if (
                "steam250.com" in href
                and name not in {
                    "New",
                    "Demo",
                    "Free",
                    "EA",
                }
            ):
                # 游戏名称通常是较长的链接文本，
                # 标签则通常位于游戏链接之后。
                game_link = a
                break

        if game_link is None:
            continue

        game_name = clean_text(
            game_link.get_text(" ", strip=True)
        )

        game_url = game_link["href"].strip()

        if game_url.startswith("/"):
            game_url = (
                "https://steam250.com"
                + game_url
            )

        # ----------------------------------------------------
        # Score
        # ----------------------------------------------------

        score = None

        for cell_text in cell_texts:
            if re.fullmatch(
                r"\d+\.\d{1,2}",
                cell_text,
            ):
                value = float(cell_text)

                # Steam250 Score 正常应该在这个范围
                if 0 <= value <= 10:
                    score = cell_text
                    break

        # ----------------------------------------------------
        # Reviews
        # ----------------------------------------------------

        reviews = None

        for cell_text in cell_texts:
            if re.fullmatch(
                r"[\d,]+",
                cell_text,
            ):
                value = int(
                    cell_text.replace(",", "")
                )

                # 避免把排名误认为 Reviews
                if value > 50:
                    reviews = cell_text
                    break

        # ----------------------------------------------------
        # 标签
        # ----------------------------------------------------

        tags = []

        for a in row.find_all("a", href=True):
            tag_text = clean_text(
                a.get_text(" ", strip=True)
            )

            if not tag_text:
                continue

            if tag_text == game_name:
                continue

            if tag_text in {
                "New",
                "Demo",
                "Free",
                "EA",
            }:
                continue

            # 排除日期、排名等非标签链接
            if re.fullmatch(
                r"\d+\s*(days?|day|yesterday)",
                tag_text,
                re.IGNORECASE,
            ):
                continue

            if len(tag_text) <= 80:
                tags.append(tag_text)

        # 去重，同时保持顺序
        tags = list(dict.fromkeys(tags))

        # ----------------------------------------------------
        # Price free
        # ----------------------------------------------------

        is_free = bool(
            re.search(
                r"Price\s+free",
                row_text,
                re.IGNORECASE,
            )
        )

        # Steam250 当前页面可能直接显示 Free
        # 也兼容 Price free 的情况。
        if re.search(
            r"\bFree\b",
            row_text,
            re.IGNORECASE,
        ):
            is_free = True

        # ----------------------------------------------------
        # Adult only
        # ----------------------------------------------------

        is_adult_only = bool(
            re.search(
                r"\bAdult\s+only\b",
                row_text,
                re.IGNORECASE,
            )
        )

        # ----------------------------------------------------
        # Horror
        # ----------------------------------------------------

        has_horror = any(
            "horror" in tag.lower()
            for tag in tags
        )

        games.append(
            {
                "rank": rank,
                "name": game_name,
                "score": score,
                "reviews": reviews,
                "tags": tags,
                "url": game_url,
                "is_free": is_free,
                "is_adult_only": is_adult_only,
                "has_horror": has_horror,
            }
        )

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
    """
    使用 Steam250 游戏 URL 作为唯一 ID。
    """

    if game["url"]:
        return game["url"]

    return game["name"].strip().lower()


# ============================================================
# Discord
# ============================================================

def build_discord_embeds(games):
    """
    Discord Embed description 上限为 4096 字符。

    因此根据长度自动拆分成多个 Embed，
    但仍然只发送一次 webhook。
    """

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
            if game["score"] is not None
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
        current_length += len(line) + 1

    if current_lines:
        chunks.append(
            "\n".join(current_lines)
        )

    embeds = []

    for index, description in enumerate(chunks):

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

    # Discord 一次 webhook 最多 10 个 embeds
    if len(embeds) > 10:
        raise RuntimeError(
            "New 游戏过多，Discord Embed "
            "数量超过 10 个。"
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
    # 抓取页面
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
    # 定位主榜单
    # --------------------------------------------------------

    print(
        "[2/5] Locating main Top 50 ranking..."
    )

    main_table = find_main_ranking_table(
        soup
    )

    # --------------------------------------------------------
    # 解析 New
    # --------------------------------------------------------

    print(
        "[3/5] Parsing New entries..."
    )

    new_games = parse_main_ranking(
        main_table
    )

    print(
        f"[INFO] Main ranking New entries: "
        f"{len(new_games)}"
    )

    if not new_games:
        print(
            "[INFO] No New games in main ranking."
        )
        return

    for game in new_games:
        print(
            f"[NEW] #{game['rank']} "
            f"{game['name']} "
            f"| score={game['score']} "
            f"| tags={game['tags']}"
        )

    # --------------------------------------------------------
    # 过滤
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
    # 防重复
    # --------------------------------------------------------

    state = load_state()

    pushed_games = set(
        state.get(
            "pushed_games",
            []
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
    # 保存 State
    # --------------------------------------------------------

    for game in games_to_send:
        pushed_games.add(
            get_game_id(game)
        )

    # 最多保存 500 个
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
