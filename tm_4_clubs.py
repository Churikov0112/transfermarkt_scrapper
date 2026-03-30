import time

import requests

from tm_common import extract_id_from_url, load_json, request_with_retries, save_json

CLUBS_URL_FILE = "tm_clubs_urls.json"
CLUBS_FILE = "tm_clubs.json"
API_BASE_URL = "http://localhost:8000"


def fetch_club_profile(session, club_id, max_retries=3):
    api_url = f"{API_BASE_URL}/clubs/{club_id}/profile"

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
    clubs = load_json(CLUBS_URL_FILE, [])
    if not clubs:
        print(f"Файл {CLUBS_URL_FILE} пуст или не найден")
        return

    print(f"[4/4] Получаем профили клубов: {len(clubs)}")

    clubs_output = []
    session = requests.Session()
    for index, club in enumerate(clubs, 1):
        club_url = club.get("url")
        club_id = club.get("id") or extract_id_from_url(club_url, "club")

        if not club_id:
            print(f"[{index}/{len(clubs)}] SKIP клуб без id")
            continue

        print(f"[{index}/{len(clubs)}] id={club_id} name={club.get('name', '')}")
        profile = fetch_club_profile(session, club_id)

        clubs_output.append({
            "id": str(club_id),
            "name": club.get("name"),
            "url": club_url,
            "profile": profile,
        })

        time.sleep(0.2)

    save_json(CLUBS_FILE, clubs_output)
    print(f"\nСохранено: {CLUBS_FILE} ({len(clubs_output)} записей)")


if __name__ == "__main__":
    main()
