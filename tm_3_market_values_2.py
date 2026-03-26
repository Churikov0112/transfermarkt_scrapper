import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from tm_common import load_json, request_with_retries, save_json

PLAYERS_FILE = "tm_players.json"
MARKET_VALUES_FILE = "tm_market_values.json"
API_BASE_URL = "http://localhost:8000"
MAX_WORKERS = int(os.getenv("TM_MARKET_WORKERS", "12"))
REQUEST_DELAY_SEC = float(os.getenv("TM_MARKET_REQUEST_DELAY", "0"))
MAX_RETRIES = int(os.getenv("TM_MARKET_MAX_RETRIES", "3"))

_thread_local = threading.local()


def get_thread_session():
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    return session


def fetch_market_value(player_id, max_retries=MAX_RETRIES):
    api_url = f"{API_BASE_URL}/players/{player_id}/market_value"
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

    market_value_data = fetch_market_value(player_id)

    if REQUEST_DELAY_SEC > 0:
        time.sleep(REQUEST_DELAY_SEC)

    return {
        "id": player_id,
        "name": player.get("name"),
        "team_id": player.get("team_id"),
        "team_name": player.get("team_name"),
        "market_value": market_value_data,
    }


def main():
    players = load_json(PLAYERS_FILE, [])
    if not players:
        print(f"Файл {PLAYERS_FILE} пуст или не найден")
        return

    print(f"[3/3 MT] Получаем market values для {len(players)} игроков")
    print(f"Потоков: {MAX_WORKERS}")

    results = []
    futures = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for index, player in enumerate(players, 1):
            future = executor.submit(fetch_for_player, player)
            futures[future] = (index, player)

        for done_count, future in enumerate(as_completed(futures), 1):
            index, player = futures[future]
            player_id = player.get("id", "?")
            name = player.get("name", "")
            try:
                item = future.result()
                if item:
                    results.append((index, item))
                    print(f"[{done_count}/{len(players)}] OK id={player_id} name={name}")
                else:
                    print(f"[{done_count}/{len(players)}] SKIP id={player_id} name={name}")
            except Exception as exc:
                print(f"[{done_count}/{len(players)}] ERROR id={player_id} name={name}: {exc}")

    results.sort(key=lambda x: x[0])
    market_values = [item[1] for item in results]

    save_json(MARKET_VALUES_FILE, market_values)
    print(f"\nСохранено: {MARKET_VALUES_FILE} ({len(market_values)} записей)")


if __name__ == "__main__":
    main()
