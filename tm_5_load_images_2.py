import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

from PIL import Image

from tm_common import create_session, load_json, request_with_retries

TEAMS_FILE = "tm_teams.json"
PLAYERS_FILE = "tm_players_urls.json"
COACHES_FILE = "tm_coach_profiles.json"
CLUBS_FILE = "tm_clubs.json"

FLAGS_DIR = "flags"
PLAYER_FACES_DIR = "players_faces"
COACH_FACES_DIR = "coach_faces"
LOGOS_DIR = "logos"

MAX_WORKERS = int(os.getenv("TM_IMAGES_WORKERS", "20"))
MAX_RETRIES = int(os.getenv("TM_IMAGES_MAX_RETRIES", "4"))

_thread_local = threading.local()


def get_thread_session():
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = create_session()
        _thread_local.session = session
    return session


def reset_thread_session():
    session = getattr(_thread_local, "session", None)
    if session is not None:
        try:
            session.close()
        except Exception:
            pass
    _thread_local.session = None


def ensure_dirs():
    os.makedirs(FLAGS_DIR, exist_ok=True)
    os.makedirs(PLAYER_FACES_DIR, exist_ok=True)
    os.makedirs(COACH_FACES_DIR, exist_ok=True)
    os.makedirs(LOGOS_DIR, exist_ok=True)


def is_default_image(url):
    """Проверяет, является ли URL ссылкой на дефолтное изображение."""
    if not url:
        return True
    url_lower = url.lower()
    # Проверяем наличие слова default в URL
    if "default" in url_lower:
        return True
    # Дополнительные проверки на известные паттерны дефолтных изображений
    default_patterns = [
        "noimage",
        "placeholder",
        "avatar.svg",
        "missing"
    ]
    for pattern in default_patterns:
        if pattern in url_lower:
            return True
    return False


def to_high_res_player_url(url):
    if not url:
        return None
    if "/header/" in url:
        return url.replace("/header/", "/big/")
    if "/medium/" in url:
        return url.replace("/medium/", "/big/")
    return None


def download_as_png(url, output_path, timeout=30, max_retries=MAX_RETRIES):
    if not url or is_default_image(url):
        return False
    try:
        session = get_thread_session()
        response = request_with_retries(session, "GET", url, timeout=timeout, max_retries=max_retries, stream=True)
        response.raise_for_status()

        raw = BytesIO()
        for chunk in response.iter_content(chunk_size=1024 * 64):
            if chunk:
                raw.write(chunk)

        image = Image.open(BytesIO(raw.getvalue())).convert("RGBA")
        tmp_path = f"{output_path}.tmp"
        image.save(tmp_path, format="PNG")
        os.replace(tmp_path, output_path)
        return True
    except Exception:
        reset_thread_session()
        raise


def collect_tasks():
    tasks = []

    teams = load_json(TEAMS_FILE, [])
    for team in teams:
        team_id = team.get("id")
        logo_url = team.get("logo_url")
        if team_id and logo_url and not is_default_image(logo_url):
            tasks.append({
                "kind": "team",
                "id": str(team_id),
                "url": logo_url,
                "path": os.path.join(FLAGS_DIR, f"{team_id}.png"),
            })

    players = load_json(PLAYERS_FILE, [])
    for player in players:
        player_id = player.get("id")
        photo_url = to_high_res_player_url(player.get("photo_url"))
        if player_id and photo_url and not is_default_image(photo_url):
            tasks.append({
                "kind": "player",
                "id": str(player_id),
                "url": photo_url,
                "path": os.path.join(PLAYER_FACES_DIR, f"{player_id}.png"),
            })

    coaches = load_json(COACHES_FILE, [])
    for coach in coaches:
        coach_id = coach.get("id")
        image_url = to_high_res_player_url(coach.get("image_url"))
        if coach_id and image_url and not is_default_image(image_url):
            tasks.append({
                "kind": "coach",
                "id": str(coach_id),
                "url": image_url,
                "path": os.path.join(COACH_FACES_DIR, f"{coach_id}.png"),
            })

    clubs = load_json(CLUBS_FILE, [])
    for club in clubs:
        club_id = club.get("id")
        profile = club.get("profile") or {}
        image_url = profile.get("image")
        if club_id and image_url and not is_default_image(image_url):
            tasks.append({
                "kind": "club",
                "id": str(club_id),
                "url": image_url,
                "path": os.path.join(LOGOS_DIR, f"{club_id}.png"),
            })

    return tasks


def process_task(task):
    download_as_png(task["url"], task["path"])
    return task


def main():
    ensure_dirs()
    tasks = collect_tasks()

    if not tasks:
        print("Нет задач на скачивание (проверьте tm_teams.json, tm_players.json, tm_clubs.json)")
        return

    print(f"[5/5 MT] Скачиваем изображений: {len(tasks)}")
    print(f"Потоков: {MAX_WORKERS}")

    ok = 0
    failed = 0
    futures = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for index, task in enumerate(tasks, 1):
            future = executor.submit(process_task, task)
            futures[future] = (index, task)

        for done_count, future in enumerate(as_completed(futures), 1):
            index, task = futures[future]
            try:
                future.result()
                ok += 1
                print(f"[{done_count}/{len(tasks)}] OK {task['kind']} id={task['id']} -> {task['path']}")
            except Exception as exc:
                failed += 1
                print(f"[{done_count}/{len(tasks)}] ERROR {task['kind']} id={task['id']}: {exc}")

    print(f"\nГотово. Успешно: {ok}, Ошибок: {failed}")


if __name__ == "__main__":
    main()