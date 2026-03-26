import time

import requests

from tm_common import load_json, request_with_retries, save_json

PLAYERS_FILE = "tm_players.json"
PLAYERS_PROFILES_FILE = "tm_players_profiles.json"
API_BASE_URL = "http://localhost:8000"


def fetch_player_profile(session, player_id, max_retries=3):
    api_url = f"{API_BASE_URL}/players/{player_id}/profile"

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

    print(f"[7/7] Получаем профили игроков: {len(players)}")

    profiles = []
    session = requests.Session()
    for index, player in enumerate(players, 1):
        player_id = player.get("id")
        if not player_id:
            print(f"[{index}/{len(players)}] SKIP игрок без id")
            continue

        print(f"[{index}/{len(players)}] id={player_id} name={player.get('name', '')}")
        profile = fetch_player_profile(session, player_id)

        profiles.append({
            "id": str(player_id),
            "name": player.get("name"),
            "profile": profile,
        })

        time.sleep(0.2)

    save_json(PLAYERS_PROFILES_FILE, profiles)
    print(f"\nСохранено: {PLAYERS_PROFILES_FILE} ({len(profiles)} записей)")


if __name__ == "__main__":
    main()
