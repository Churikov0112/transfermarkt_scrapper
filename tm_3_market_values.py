import time

import requests

from tm_common import load_json, request_with_retries, save_json

PLAYERS_FILE = "tm_players.json"
MARKET_VALUES_FILE = "tm_market_values.json"
API_BASE_URL = "http://localhost:8000"


def fetch_market_value(session, player_id, max_retries=3):
    api_url = f"{API_BASE_URL}/players/{player_id}/market_value"

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


def main():
    players = load_json(PLAYERS_FILE, [])
    if not players:
        print(f"Файл {PLAYERS_FILE} пуст или не найден")
        return

    print(f"[3/3] Получаем market values для {len(players)} игроков")

    session = requests.Session()
    market_values = []  # список для сохранения ответов API

    for index, player in enumerate(players, 1):
        player_id = player.get("id")
        if not player_id:
            continue

        print(f"[{index}/{len(players)}] id={player_id} name={player.get('name', '')}")
        market_value_data = fetch_market_value(session, player_id)

        if market_value_data is not None:
            market_values.append(market_value_data)

        time.sleep(0.3)

    save_json(MARKET_VALUES_FILE, market_values)
    print(f"\nСохранено: {MARKET_VALUES_FILE} ({len(market_values)} записей)")


if __name__ == "__main__":
    main()