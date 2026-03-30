import time
from urllib.parse import urljoin
from urllib.parse import urlsplit, urlunsplit

from tm_common import (
    NATIONAL_TEAMS_URL,
    build_absolute_url,
    create_session,
    extract_id_from_url,
    get_soup,
    save_json,
)

TEAMS_FILE = "tm_teams.json"
PLAYERS_URLS_FILE = "tm_players_urls.json"
include_list = [
    # "url_1",
    # "url_2",
]


def extract_player_photo_url(row):
    img = row.select_one("td:nth-child(2) > table img") or row.select_one("td:nth-child(2) img")
    if not img:
        return None
    return img.get("data-src") or img.get("src")


def is_default_photo(photo_url):
    return "default" in (photo_url or "").lower()


def parse_players_on_team_page(soup, team_id, team_name):
    players = []
    skipped_default = 0
    players_table = soup.select_one("#yw1 > table > tbody")
    if not players_table:
        return players, skipped_default

    for row in players_table.select("tr"):
        photo_url = extract_player_photo_url(row)
        if is_default_photo(photo_url):
            skipped_default += 1
            continue

        name_element = row.select_one("td:nth-child(2) a")
        if not name_element:
            continue

        player_url = build_absolute_url(name_element.get("href"))
        player_id = extract_id_from_url(player_url, "player")
        if not player_id:
            continue

        number_element = row.select_one("td.zentriert.rueckennummer > div, td:first-child div")
        number = number_element.text.strip() if number_element else "-"

        players.append({
            "id": player_id,
            "name": name_element.text.strip(),
            "url": player_url,
            "photo_url": photo_url,
            "number": number,
            "team_id": team_id,
            "team_name": team_name,
        })

    return players, skipped_default


def normalize_team_url(url):
    if not url:
        return None
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def parse_teams_page(session, page):
    page_url = f"{NATIONAL_TEAMS_URL}?page={page}"
    soup = get_soup(session, page_url)
    table = soup.select_one("#yw1 > table")
    if not table:
        return []

    teams = []
    for row in table.select("tbody tr"):
        link = row.select_one("td:nth-child(2) > a:nth-child(2)")
        if not link:
            continue

        team_url = urljoin(NATIONAL_TEAMS_URL, link.get("href"))
        teams.append({
            "name": link.text.strip(),
            "url": team_url,
        })

    return teams


def parse_teams_list(session):
    teams = []
    seen_urls = set()
    previous_page_urls = None
    page = 1

    while True:
        page_teams = parse_teams_page(session, page)
        if not page_teams:
            break

        page_urls = [normalize_team_url(team["url"]) for team in page_teams]
        if previous_page_urls == page_urls:
            break
        previous_page_urls = page_urls

        for team in page_teams:
            key = normalize_team_url(team["url"])
            if key in seen_urls:
                continue
            seen_urls.add(key)
            teams.append(team)

        if len(page_teams) < 25:
            break

        page += 1

    return teams


def parse_team_page(session, team_url):
    soup = get_soup(session, team_url)

    name_element = soup.select_one("#tm-main > header > div.data-header__headline-container > h1")
    team_name = name_element.text.strip() if name_element else "Unknown"

    logo_element = soup.select_one(
        "#tm-main > header > div.data-header__profile-container.data-header__profile-container--national-team > img"
    )
    logo_url = build_absolute_url(logo_element.get("src")) if logo_element and logo_element.get("src") else None

    team_id = extract_id_from_url(team_url, "team")
    players, skipped_default = parse_players_on_team_page(soup, team_id, team_name)

    team_data = {
        "id": team_id,
        "name": team_name,
        "logo_url": logo_url,
    }

    return team_data, players, skipped_default


def main():
    session = create_session()

    print("[1/3] Читаем список сборных...")
    teams = parse_teams_list(session)
    normalized_include = {normalize_team_url(url) for url in include_list if url}
    if normalized_include:
        teams = [team for team in teams if normalize_team_url(team["url"]) in normalized_include]
    print(f"Найдено сборных: {len(teams)}")

    all_team_data = []
    all_players_urls = []
    seen_player_ids = set()
    skipped_default_total = 0
    skipped_teams_no_photos = 0

    for index, team in enumerate(teams, 1):
        print(f"[{index}/{len(teams)}] {team['name']}")
        try:
            team_data, players, skipped_default = parse_team_page(session, team["url"])
            skipped_default_total += skipped_default
            if not players:
                skipped_teams_no_photos += 1
                print("  skip: нет игроков с реальными фото")
            else:
                all_team_data.append(team_data)

                for player in players:
                    if player["id"] in seen_player_ids:
                        continue
                    seen_player_ids.add(player["id"])
                    all_players_urls.append(player)

                print(f"  players: {len(players)}")
        except Exception as exc:
            print(f"  ошибка: {exc}")

        time.sleep(1)

    save_json(TEAMS_FILE, all_team_data)
    save_json(PLAYERS_URLS_FILE, all_players_urls)

    print(f"\nСохранено: {TEAMS_FILE} ({len(all_team_data)} сборных)")
    print(f"Сохранено: {PLAYERS_URLS_FILE} ({len(all_players_urls)} игроков)")
    print(f"Пропущено игроков с дефолтными фото: {skipped_default_total}")
    print(f"Пропущено сборных без реальных фото игроков: {skipped_teams_no_photos}")


if __name__ == "__main__":
    main()
