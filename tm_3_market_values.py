import time

import requests

from tm_common import load_json, request_with_retries, save_json

PLAYERS_FILE = "tm_players.json"
PLAYERS_WITH_MARKET_VALUES_FILE = "tm_players_with_market_values.json"
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


def calc_max_market_value(market_value_data):
    if not isinstance(market_value_data, dict):
        return None
    history = market_value_data.get("marketValueHistory")
    if not isinstance(history, list):
        return None

    max_value = None
    for item in history:
        if not isinstance(item, dict):
            continue
        value = item.get("marketValue")
        if isinstance(value, int):
            if max_value is None or value > max_value:
                max_value = value
    return max_value


def main():
    players = load_json(PLAYERS_FILE, [])
    if not players:
        print(f"Файл {PLAYERS_FILE} пуст или не найден")
        return

    print(f"[3/3] Получаем market values для {len(players)} игроков")

    session = requests.Session()
    for index, player in enumerate(players, 1):
        player_id = player.get("id")
        if not player_id:
            continue

        print(f"[{index}/{len(players)}] id={player_id} name={player.get('name', '')}")
        market_value_data = fetch_market_value(session, player_id)

        if market_value_data is not None:
            player["market_value"] = market_value_data
            max_market_value = calc_max_market_value(market_value_data)
            if max_market_value is not None:
                player["max_market_value"] = max_market_value

        time.sleep(0.3)

    save_json(PLAYERS_WITH_MARKET_VALUES_FILE, players)
    print(f"\nСохранено: {PLAYERS_WITH_MARKET_VALUES_FILE} ({len(players)} игроков)")


if __name__ == "__main__":
    main()
