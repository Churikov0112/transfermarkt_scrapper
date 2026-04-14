import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
from urllib.parse import urlsplit, urlunsplit

import requests

from tm_common import (
    NATIONAL_TEAMS_URL,
    build_absolute_url,
    create_session,
    extract_id_from_url,
    get_soup,
    save_json,
    request_with_retries,
)

TEAMS_FILE = "tm_teams.json"
PLAYERS_URLS_FILE = "tm_players_urls.json"
COACHES_PROFILES_FILE = "tm_coach_profiles.json"
API_BASE_URL = "http://localhost:8000"
MAX_WORKERS = int(os.getenv("TM_TEAMS_WORKERS", "8"))
REQUEST_DELAY_SEC = float(os.getenv("TM_TEAMS_REQUEST_DELAY", "0"))
MAX_RETRIES = int(os.getenv("TM_COACHES_MAX_RETRIES", "3"))
include_list = [
    "https://www.transfermarkt.com/england/startseite/verein/3299",
    "https://www.transfermarkt.com/frankreich/startseite/verein/3377",
    "https://www.transfermarkt.com/spanien/startseite/verein/3375",
    "https://www.transfermarkt.com/portugal/startseite/verein/3300",
    "https://www.transfermarkt.com/brasilien/startseite/verein/3439",
    "https://www.transfermarkt.com/deutschland/startseite/verein/3262",
    "https://www.transfermarkt.com/niederlande/startseite/verein/3379",
    "https://www.transfermarkt.com/argentinien/startseite/verein/3437",
    "https://www.transfermarkt.com/belgien/startseite/verein/3382",
    "https://www.transfermarkt.com/norwegen/startseite/verein/3440",
    "https://www.transfermarkt.com/senegal/startseite/verein/3499",
    "https://www.transfermarkt.com/marokko/startseite/verein/3575",
    "https://www.transfermarkt.com/turkei/startseite/verein/3381",
    "https://www.transfermarkt.com/elfenbeinkuste/startseite/verein/3591",
    "https://www.transfermarkt.com/ecuador/startseite/verein/5750",
    "https://www.transfermarkt.com/schweden/startseite/verein/3557",
    "https://www.transfermarkt.com/uruguay/startseite/verein/3449",
    "https://www.transfermarkt.com/vereinigte-staaten/startseite/verein/3505",
    "https://www.transfermarkt.com/schweiz/startseite/verein/3384",
    "https://www.transfermarkt.com/kolumbien/startseite/verein/3816",
    "https://www.transfermarkt.com/kroatien/startseite/verein/3556",
    "https://www.transfermarkt.com/japan/startseite/verein/3435",
    "https://www.transfermarkt.com/osterreich/startseite/verein/3383",
    "https://www.transfermarkt.com/algerien/startseite/verein/3614",
    "https://www.transfermarkt.com/ghana/startseite/verein/3441",
    "https://www.transfermarkt.com/schottland/startseite/verein/3380",
    "https://www.transfermarkt.com/tschechien/startseite/verein/3445",
    "https://www.transfermarkt.com/mexiko/startseite/verein/6303",
    "https://www.transfermarkt.com/demokratische-republik-kongo/startseite/verein/3854",
    "https://www.transfermarkt.com/sudkorea/startseite/verein/3589",
    "https://www.transfermarkt.com/paraguay/startseite/verein/3581",
    "https://www.transfermarkt.com/kanada/startseite/verein/3510",
    "https://www.transfermarkt.com/bosnien-herzegowina/startseite/verein/3446",
    "https://www.transfermarkt.com/agypten/startseite/verein/3672",
    "https://www.transfermarkt.com/usbekistan/startseite/verein/3563",
    "https://www.transfermarkt.com/haiti/startseite/verein/14161",
    "https://www.transfermarkt.com/tunesien/startseite/verein/3670",
    "https://www.transfermarkt.com/australien/startseite/verein/3433",
    "https://www.transfermarkt.com/kap-verde/startseite/verein/4311",
    "https://www.transfermarkt.com/sudafrika/startseite/verein/3806",
    "https://www.transfermarkt.com/iran/startseite/verein/3582",
    "https://www.transfermarkt.com/panama/startseite/verein/3577",
    "https://www.transfermarkt.com/curacao/startseite/verein/32364",
    "https://www.transfermarkt.com/saudi-arabien/startseite/verein/3807",
    "https://www.transfermarkt.com/neuseeland/startseite/verein/9171",
    "https://www.transfermarkt.com/irak/startseite/verein/3560",
    "https://www.transfermarkt.com/katar/startseite/verein/14162",
    "https://www.transfermarkt.com/jordanien/startseite/verein/15737",
]

_thread_local = threading.local()


def get_thread_session():
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = create_session()
        _thread_local.session = session
    return session


def get_thread_requests_session():
    session = getattr(_thread_local, "requests_session", None)
    if session is None:
        session = requests.Session()
        _thread_local.requests_session = session
    return session


def extract_player_photo_url(row):
    img = row.select_one("td:nth-child(2) > table img") or row.select_one("td:nth-child(2) img")
    if not img:
        return None
    return img.get("data-src") or img.get("src")


def is_default_photo(photo_url):
    return "default" in (photo_url or "").lower()


def fetch_coach_profile(coach_id, max_retries=MAX_RETRIES):
    """Получает профиль тренера через локальный API"""
    api_url = f"{API_BASE_URL}/coaches/{coach_id}/profile"
    session = get_thread_requests_session()

    try:
        response = request_with_retries(
            session,
            "GET",
            api_url,
            timeout=15,
            max_retries=max_retries,
            retry_statuses={503},
        )
        if response.status_code == 503:
            return None
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def extract_coach_id_from_staff_page(team_id):
    """
    Получает ID тренера со страницы сотрудников команды
    URL: https://www.transfermarkt.com/-/mitarbeiter/verein/{team_id}
    """
    staff_url = f"https://www.transfermarkt.com/-/mitarbeiter/verein/{team_id}"
    session = get_thread_session()

    try:
        soup = get_soup(session, staff_url)

        # Ищем ссылку на главного тренера
        coach_link = soup.select_one(
            "div.large-8.columns table.inline-table tr:first-child td:nth-child(2) a[href*='/trainer/']")

        if not coach_link:
            coach_link = soup.select_one("a[href*='/profil/trainer/']")

        if not coach_link:
            return None

        coach_url = coach_link.get("href")

        # Извлекаем ID из URL
        coach_id = None
        if "/trainer/" in coach_url:
            coach_id = coach_url.split("/trainer/")[-1].split("/")[0]
        elif "/profil/trainer/" in coach_url:
            coach_id = coach_url.split("/profil/trainer/")[-1].split("/")[0]

        return coach_id

    except Exception:
        return None


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


def parse_team_page(team):
    session = get_thread_session()
    team_url = team["url"]
    soup = get_soup(session, team_url)

    name_element = soup.select_one("#tm-main > header > div.data-header__headline-container > h1")
    team_name = name_element.text.strip() if name_element else team.get("name", "Unknown")

    logo_element = soup.select_one(
        "#tm-main > header > div.data-header__profile-container.data-header__profile-container--national-team > img"
    )
    logo_url = build_absolute_url(logo_element.get("src")) if logo_element and logo_element.get("src") else None

    team_id = extract_id_from_url(team_url, "team")
    players, skipped_default = parse_players_on_team_page(soup, team_id, team_name)

    # Получаем ID тренера со страницы сотрудников
    coach_id = extract_coach_id_from_staff_page(team_id)

    # Если тренер найден, получаем его профиль через API
    coach_profile = None

    if coach_id:
        coach_profile = fetch_coach_profile(coach_id)
        if REQUEST_DELAY_SEC > 0:
            time.sleep(REQUEST_DELAY_SEC)

    if REQUEST_DELAY_SEC > 0:
        time.sleep(REQUEST_DELAY_SEC)

    team_data = {
        "id": team_id,
        "name": team_name,
        "logo_url": logo_url,
        "players_ids": [p["id"] for p in players],
        "coach_id": coach_id,
    }

    return team_data, players, skipped_default, coach_id, coach_profile


def main():
    session = create_session()

    print("[1/3] Читаем список сборных...")
    teams = parse_teams_list(session)
    normalized_include = {normalize_team_url(url) for url in include_list if url}
    if normalized_include:
        teams = [team for team in teams if normalize_team_url(team["url"]) in normalized_include]
    if not teams:
        print("Список сборных пуст")
        return

    print(f"Найдено сборных: {len(teams)}")
    print(f"Потоков: {MAX_WORKERS}")

    teams_results = []
    players_results = []
    coaches_profiles = []
    skipped_default_total = 0
    skipped_teams_no_photos = 0
    coaches_found = 0

    futures = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for index, team in enumerate(teams, 1):
            future = executor.submit(parse_team_page, team)
            futures[future] = (index, team)

        for done_count, future in enumerate(as_completed(futures), 1):
            index, team = futures[future]
            team_name = team.get("name", "Unknown")
            try:
                team_data, players, skipped_default, coach_id, coach_profile = future.result()
                skipped_default_total += skipped_default

                # Обработка тренера
                if coach_id:
                    coaches_found += 1
                    if coach_profile:
                        coaches_profiles.append(coach_profile)
                        print(f"[{done_count}/{len(teams)}] OK {team_name} players={len(players)}, coach={coach_id}")
                    else:
                        print(
                            f"[{done_count}/{len(teams)}] OK {team_name} players={len(players)}, coach={coach_id} (profile not fetched)")
                else:
                    print(f"[{done_count}/{len(teams)}] OK {team_name} players={len(players)}, coach=None")

                if not players:
                    skipped_teams_no_photos += 1

                teams_results.append((index, team_data))
                players_results.append((index, players))

            except Exception as exc:
                print(f"[{done_count}/{len(teams)}] ERROR {team_name}: {exc}")

    teams_results.sort(key=lambda x: x[0])
    players_results.sort(key=lambda x: x[0])

    all_team_data = [item[1] for item in teams_results]

    all_players_urls = []
    seen_player_ids = set()
    for _, players in players_results:
        for player in players:
            player_id = player.get("id")
            if not player_id or player_id in seen_player_ids:
                continue
            seen_player_ids.add(player_id)
            all_players_urls.append(player)

    save_json(TEAMS_FILE, all_team_data)
    save_json(PLAYERS_URLS_FILE, all_players_urls)
    save_json(COACHES_PROFILES_FILE, coaches_profiles)

    print(f"\nСохранено: {TEAMS_FILE} ({len(all_team_data)} сборных)")
    print(f"Сохранено: {PLAYERS_URLS_FILE} ({len(all_players_urls)} игроков)")
    print(f"Сохранено: {COACHES_PROFILES_FILE} ({len(coaches_profiles)} тренеров)")
    print(f"Пропущено игроков с дефолтными фото: {skipped_default_total}")
    print(f"Пропущено сборных без реальных фото игроков: {skipped_teams_no_photos}")


if __name__ == "__main__":
    main()