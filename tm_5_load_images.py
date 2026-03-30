import os
from io import BytesIO

from PIL import Image

from tm_common import create_session, load_json, request_with_retries

TEAMS_FILE = "tm_teams.json"
PLAYERS_FILE = "tm_players_urls.json"
CLUBS_FILE = "tm_clubs.json"

FLAGS_DIR = "flags"
FACES_DIR = "faces"
LOGOS_DIR = "logos"
MAX_RETRIES = int(os.getenv("TM_IMAGES_MAX_RETRIES", "4"))


def ensure_dirs():
    os.makedirs(FLAGS_DIR, exist_ok=True)
    os.makedirs(FACES_DIR, exist_ok=True)
    os.makedirs(LOGOS_DIR, exist_ok=True)


def to_high_res_player_url(url):
    if not url:
        return None
    return url.replace("/header/", "/big/")


def download_as_png(session, url, output_path, timeout=30, max_retries=MAX_RETRIES):
    if not url:
        return False
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


def collect_tasks():
    tasks = []

    teams = load_json(TEAMS_FILE, [])
    for team in teams:
        team_id = team.get("id")
        logo_url = team.get("logo_url")
        if team_id and logo_url:
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
        if player_id and photo_url:
            tasks.append({
                "kind": "player",
                "id": str(player_id),
                "url": photo_url,
                "path": os.path.join(FACES_DIR, f"{player_id}.png"),
            })

    clubs = load_json(CLUBS_FILE, [])
    for club in clubs:
        club_id = club.get("id")
        profile = club.get("profile") or {}
        image_url = profile.get("image")
        if club_id and image_url:
            tasks.append({
                "kind": "club",
                "id": str(club_id),
                "url": image_url,
                "path": os.path.join(LOGOS_DIR, f"{club_id}.png"),
            })

    return tasks


def main():
    ensure_dirs()
    tasks = collect_tasks()

    if not tasks:
        print("Нет задач на скачивание (проверьте tm_teams.json, tm_players.json, tm_clubs.json)")
        return

    print(f"[5/5] Скачиваем изображений: {len(tasks)}")

    session = create_session()
    ok = 0
    failed = 0

    for index, task in enumerate(tasks, 1):
        try:
            download_as_png(session, task["url"], task["path"])
            ok += 1
            print(f"[{index}/{len(tasks)}] OK {task['kind']} id={task['id']} -> {task['path']}")
        except Exception as exc:
            failed += 1
            print(f"[{index}/{len(tasks)}] ERROR {task['kind']} id={task['id']}: {exc}")

    print(f"\nГотово. Успешно: {ok}, Ошибок: {failed}")


if __name__ == "__main__":
    main()
