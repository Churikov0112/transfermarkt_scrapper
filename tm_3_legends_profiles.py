import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from tm_common import load_json, request_with_retries, save_json

PLAYERS_FILE = "legends_ids.json"
PLAYERS_PROFILES_FILE = "tm_legends_profiles.json"
API_BASE_URL = "http://localhost:8000"
MAX_WORKERS = int(os.getenv("TM_PLAYERS_PROFILES_WORKERS", "12"))
REQUEST_DELAY_SEC = float(os.getenv("TM_PLAYERS_PROFILES_REQUEST_DELAY", "0"))
MAX_RETRIES = int(os.getenv("TM_PLAYERS_PROFILES_MAX_RETRIES", "3"))

_thread_local = threading.local()


def get_thread_session():
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    return session


def fetch_player_profile(player_id, max_retries=MAX_RETRIES):
    api_url = f"{API_BASE_URL}/players/{player_id}/profile"
    session = get_thread_session()

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


def fetch_for_player(player):
    player_id = player.get("id")
    if not player_id:
        return None

    profile = fetch_player_profile(player_id)

    if REQUEST_DELAY_SEC > 0:
        time.sleep(REQUEST_DELAY_SEC)

    return {
        "id": str(player_id),
        "name": player.get("name"),
        "profile": profile,
    }


def main():
    players = load_json(PLAYERS_FILE, [])
    if not players:
        print(f"Файл {PLAYERS_FILE} пуст или не найден")
        return

    print(f"[7/7 MT] Получаем профили игроков: {len(players)}")
    print(f"Потоков: {MAX_WORKERS}")

    results = []
    futures = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for index, player in enumerate(players, 1):
            future = executor.submit(fetch_for_player, player)
            futures[future] = (index, player)

        for done_count, future in enumerate(as_completed(futures), 1):
            index, player = futures[future]
            player_id = player.get("id") or "?"
            player_name = player.get("name", "")
            try:
                item = future.result()
                if item:
                    results.append((index, item))
                    print(f"[{done_count}/{len(players)}] OK id={player_id} name={player_name}")
                else:
                    print(f"[{done_count}/{len(players)}] SKIP id={player_id} name={player_name}")
            except Exception as exc:
                print(f"[{done_count}/{len(players)}] ERROR id={player_id} name={player_name}: {exc}")

    results.sort(key=lambda x: x[0])
    profiles = [item[1] for item in results]

    for item in profiles:
        profile = item.get("profile")
        if not isinstance(profile, dict):
            continue

        club = profile.get("club")
        if not isinstance(club, dict):
            continue

        club_id = club.get("id")
        if not club_id:
            continue

    save_json(PLAYERS_PROFILES_FILE, profiles)
    print(f"\nСохранено: {PLAYERS_PROFILES_FILE} ({len(profiles)} записей)")


if __name__ == "__main__":
    main()
