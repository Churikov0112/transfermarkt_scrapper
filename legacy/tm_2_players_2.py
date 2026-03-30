# import os
# import threading
# import time
# from concurrent.futures import ThreadPoolExecutor, as_completed
#
# from tm_common import (
#     build_absolute_url,
#     create_session,
#     extract_id_from_url,
#     get_soup,
#     load_json,
#     save_json,
# )
#
# PLAYERS_URLS_FILE = "tm_players_urls.json"
# PLAYERS_FILE = "tm_players.json"
# CLUBS_FILE = "tm_clubs_url.json"
# TEAMS_FILE = "tm_teams.json"
# MAX_WORKERS = int(os.getenv("TM_PLAYERS_WORKERS", "10"))
# REQUEST_DELAY_SEC = float(os.getenv("TM_PLAYERS_REQUEST_DELAY", "0"))
#
# _thread_local = threading.local()
#
#
# def is_placeholder_photo(photo_url):
#     return (not photo_url) or ("default" in photo_url.lower())
#
#
# def save_filtered_teams(players):
#     teams = load_json(TEAMS_FILE, [])
#     if not teams:
#         return 0
#
#     players_by_team = {}
#     for player in players:
#         team_id = str(player.get("team_id") or "")
#         player_id = str(player.get("id") or "")
#         if not team_id or not player_id:
#             continue
#         players_by_team.setdefault(team_id, [])
#         players_by_team[team_id].append(player_id)
#
#     filtered_teams = []
#     for team in teams:
#         team_id = str(team.get("id") or "")
#         if not team_id or team_id not in players_by_team:
#             continue
#
#         seen_ids = set()
#         unique_player_ids = []
#         for player_id in players_by_team[team_id]:
#             if player_id in seen_ids:
#                 continue
#             seen_ids.add(player_id)
#             unique_player_ids.append(player_id)
#
#         team_copy = team.copy()
#         team_copy["players_ids"] = unique_player_ids
#         filtered_teams.append(team_copy)
#
#     save_json(TEAMS_FILE, filtered_teams)
#     return len(filtered_teams)
#
#
# def get_thread_session():
#     session = getattr(_thread_local, "session", None)
#     if session is None:
#         session = create_session()
#         _thread_local.session = session
#     return session
#
#
# def parse_player_page(player_seed):
#     player_url = player_seed.get("url")
#     session = get_thread_session()
#     soup = get_soup(session, player_url)
#
#     player_id = player_seed.get("id") or extract_id_from_url(player_url, "player")
#
#     photo_element = soup.select_one("#fotoauswahlOeffnen > img")
#     photo_url = build_absolute_url(photo_element.get("src")) if photo_element and photo_element.get("src") else None
#     if is_placeholder_photo(photo_url):
#         return None, None
#
#     club_element = soup.select_one("#tm-main > header > div.data-header__box--big > div > span.data-header__club > a")
#     club_name = club_element.text.strip() if club_element else None
#     club_url = build_absolute_url(club_element.get("href")) if club_element and club_element.get("href") else None
#     club_id = extract_id_from_url(club_url, "club")
#
#     birth_element = soup.select_one(
#         "#tm-main > header > div.data-header__info-box > div > ul:nth-child(1) > li:nth-child(1) > span"
#     )
#     birth_info = birth_element.text.strip() if birth_element else None
#
#     height_element = soup.select_one(
#         "#tm-main > header > div.data-header__info-box > div > ul:nth-child(2) > li:nth-child(1) > span"
#     )
#     height = height_element.text.strip() if height_element else None
#
#     position_element = soup.select_one(
#         "#tm-main > header > div.data-header__info-box > div > ul:nth-child(2) > li:nth-child(2) > span"
#     )
#     position = position_element.text.strip() if position_element else None
#
#     if REQUEST_DELAY_SEC > 0:
#         time.sleep(REQUEST_DELAY_SEC)
#
#     player_data = {
#         "id": player_id,
#         "name": player_seed.get("name", "Unknown"),
#         "number": player_seed.get("number", "-"),
#         "photo_url": photo_url,
#         "team_name": player_seed.get("team_name"),
#         "team_id": player_seed.get("team_id"),
#         "club_name": club_name,
#         "club_id": club_id,
#         "birth_info": birth_info,
#         "height": height,
#         "position": position,
#     }
#
#     club_data = None
#     if club_url:
#         club_data = {
#             "id": club_id,
#             "name": club_name,
#             "url": club_url,
#         }
#
#     return player_data, club_data
#
#
# def main():
#     players_urls = load_json(PLAYERS_URLS_FILE, [])
#     if not players_urls:
#         print(f"Файл {PLAYERS_URLS_FILE} пуст или не найден")
#         return
#
#     print(f"[2/3 MT] Обрабатываем игроков: {len(players_urls)}")
#     print(f"Потоков: {MAX_WORKERS}")
#
#     all_players = []
#     clubs_map = {}
#     skipped_placeholders = 0
#     futures = {}
#
#     with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
#         for index, player_seed in enumerate(players_urls, 1):
#             future = executor.submit(parse_player_page, player_seed)
#             futures[future] = (index, player_seed)
#
#         for done_count, future in enumerate(as_completed(futures), 1):
#             index, player_seed = futures[future]
#             player_id = player_seed.get("id", "?")
#             try:
#                 player_data, club_data = future.result()
#                 if not player_data:
#                     skipped_placeholders += 1
#                     print(f"[{done_count}/{len(players_urls)}] SKIP default photo id={player_id}")
#                     continue
#                 if player_data.get("id"):
#                     all_players.append((index, player_data))
#                 if club_data:
#                     club_key = club_data.get("id") or club_data.get("url")
#                     if club_key and club_key not in clubs_map:
#                         clubs_map[club_key] = club_data
#                 print(f"[{done_count}/{len(players_urls)}] OK id={player_id}")
#             except Exception as exc:
#                 print(f"[{done_count}/{len(players_urls)}] ERROR id={player_id}: {exc}")
#
#     # Сохраняем в том же порядке, что и входной список
#     all_players.sort(key=lambda x: x[0])
#     players_output = [item[1] for item in all_players]
#
#     save_json(PLAYERS_FILE, players_output)
#     save_json(CLUBS_FILE, list(clubs_map.values()))
#     teams_count = save_filtered_teams(players_output)
#     print(f"\nСохранено: {PLAYERS_FILE} ({len(players_output)} игроков)")
#     print(f"Сохранено: {CLUBS_FILE} ({len(clubs_map)} клубов)")
#     print(f"Обновлено: {TEAMS_FILE} ({teams_count} сборных, у которых есть игроки с реальными фото)")
#     print(f"Пропущено игроков с заглушками: {skipped_placeholders}")
#
#
# if __name__ == "__main__":
#     main()
