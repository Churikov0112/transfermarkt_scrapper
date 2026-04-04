import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from tm_common import extract_id_from_url, load_json, request_with_retries, save_json

CLUBS_URL_FILE = "tm_clubs_urls.json"
CLUBS_FILE = "tm_clubs.json"
API_BASE_URL = "http://localhost:8000"
MAX_WORKERS = int(os.getenv("TM_CLUBS_WORKERS", "10"))
REQUEST_DELAY_SEC = float(os.getenv("TM_CLUBS_REQUEST_DELAY", "0"))
MAX_RETRIES = int(os.getenv("TM_CLUBS_MAX_RETRIES", "3"))

_thread_local = threading.local()


def get_thread_session():
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    return session


def fetch_club_profile(club_id, max_retries=MAX_RETRIES):
    api_url = f"{API_BASE_URL}/clubs/{club_id}/profile"
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


def fetch_for_club(club):
    club_url = club.get("url")
    club_id = club.get("id") or extract_id_from_url(club_url, "club")
    if not club_id:
        return None

    profile = fetch_club_profile(club_id)

    if REQUEST_DELAY_SEC > 0:
        time.sleep(REQUEST_DELAY_SEC)

    return {
        "id": str(club_id),
        "name": club.get("name"),
        "url": club_url,
        "profile": profile,
    }


def main():
    clubs = load_json(CLUBS_URL_FILE, [])
    if not clubs:
        print(f"Файл {CLUBS_URL_FILE} пуст или не найден")
        return

    print(f"[4/4 MT] Получаем профили клубов: {len(clubs)}")
    print(f"Потоков: {MAX_WORKERS}")

    results = []
    futures = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for index, club in enumerate(clubs, 1):
            future = executor.submit(fetch_for_club, club)
            futures[future] = (index, club)

        for done_count, future in enumerate(as_completed(futures), 1):
            index, club = futures[future]
            club_id = club.get("id") or extract_id_from_url(club.get("url"), "club") or "?"
            club_name = club.get("name", "")
            try:
                item = future.result()
                if item:
                    results.append((index, item))
                    print(f"[{done_count}/{len(clubs)}] OK id={club_id} name={club_name}")
                else:
                    print(f"[{done_count}/{len(clubs)}] SKIP id={club_id} name={club_name}")
            except Exception as exc:
                print(f"[{done_count}/{len(clubs)}] ERROR id={club_id} name={club_name}: {exc}")

    results.sort(key=lambda x: x[0])
    clubs_output = [item[1] for item in results]

    save_json(CLUBS_FILE, clubs_output)
    print(f"\nСохранено: {CLUBS_FILE} ({len(clubs_output)} записей)")


if __name__ == "__main__":
    main()
