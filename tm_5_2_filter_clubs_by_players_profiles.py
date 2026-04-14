import json
from pathlib import Path


def filter_clubs_by_players(players_file='tm_players_profiles.json',
                            clubs_file='tm_clubs.json',
                            output_file='tm_clubs_filtered.json'):
    """
    Фильтрует клубы, оставляя только те, у которых id есть у какого-либо игрока в club['id']

    Args:
        players_file: путь к файлу с профилями игроков
        clubs_file: путь к файлу с клубами
        output_file: путь для сохранения отфильтрованных клубов
    """

    # Проверяем существование файлов
    if not Path(players_file).exists():
        print(f"❌ Ошибка: Файл {players_file} не найден!")
        return

    if not Path(clubs_file).exists():
        print(f"❌ Ошибка: Файл {clubs_file} не найден!")
        return

    # Загружаем профили игроков
    print(f"📖 Загрузка профилей игроков из {players_file}...")
    with open(players_file, 'r', encoding='utf-8') as f:
        players = json.load(f)

    # Загружаем данные о клубах
    print(f"📖 Загрузка клубов из {clubs_file}...")
    with open(clubs_file, 'r', encoding='utf-8') as f:
        clubs = json.load(f)

    # Собираем множество уникальных ID клубов, в которых играют игроки
    player_club_ids = set()
    clubs_without_club_info = 0
    players_without_profile = 0

    for player in players:
        # Проверяем, что player не None и является словарем
        if not player or not isinstance(player, dict):
            players_without_profile += 1
            continue

        # Проверяем наличие profile и что он не None
        if 'profile' in player and player['profile'] and isinstance(player['profile'], dict):
            # Проверяем наличие club в profile
            if 'club' in player['profile'] and player['profile']['club'] and isinstance(player['profile']['club'],
                                                                                        dict):
                if 'id' in player['profile']['club'] and player['profile']['club']['id']:
                    club_id = str(player['profile']['club']['id'])
                    player_club_ids.add(club_id)
                else:
                    clubs_without_club_info += 1
            else:
                clubs_without_club_info += 1
        else:
            # Если нет profile, проверяем наличие club напрямую в player
            if 'club' in player and player['club'] and isinstance(player['club'], dict):
                if 'id' in player['club'] and player['club']['id']:
                    club_id = str(player['club']['id'])
                    player_club_ids.add(club_id)
                else:
                    clubs_without_club_info += 1
            else:
                clubs_without_club_info += 1

    # Фильтруем клубы
    filtered_clubs = []
    missing_club_ids = []

    for club in clubs:
        if not club or not isinstance(club, dict):
            continue

        club_id = str(club.get('id', ''))
        if club_id and club_id in player_club_ids:
            filtered_clubs.append(club)
        else:
            if club_id:
                missing_club_ids.append(club_id)

    # Сохраняем результат
    print(f"💾 Сохранение результата в {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_clubs, f, ensure_ascii=False, indent=2)

    # Выводим статистику
    print(f"\n{'=' * 60}")
    print(f"Статистика фильтрации клубов:")
    print(f"{'=' * 60}")
    print(f"📊 Всего игроков:                    {len(players):>10,}")
    print(f"📊 Игроков без profile или club:     {players_without_profile:>10,}")
    print(f"📊 Игроков без информации о клубе:   {clubs_without_club_info:>10,}")
    print(f"📊 Уникальных клубов у игроков:      {len(player_club_ids):>10,}")
    print(f"📊 Всего клубов в файле:             {len(clubs):>10,}")
    print(f"📊 Оставлено клубов:                 {len(filtered_clubs):>10,}")
    print(f"📊 Удалено клубов:                   {len(missing_club_ids):>10,}")

    if missing_club_ids:
        match_rate = (len(filtered_clubs) / len(clubs)) * 100 if clubs else 0
        print(f"\n📈 Процент совпадения: {match_rate:.2f}%")

        # Показываем несколько примеров удаленных клубов
        if len(missing_club_ids) <= 10:
            print(f"\n❌ Удаленные ID клубов: {', '.join(missing_club_ids)}")
        else:
            print(f"\n❌ Примеры удаленных ID клубов (первые 10 из {len(missing_club_ids)}):")
            for club_id in missing_club_ids[:10]:
                club_name = next((c.get('name', 'Unknown') for c in clubs if str(c.get('id', '')) == club_id),
                                 'Unknown')
                print(f"   - {club_id}: {club_name}")

    # Показываем топ клубов по количеству игроков (дополнительная статистика)
    print(f"\n{'=' * 60}")
    print(f"Топ-10 клубов по количеству игроков:")
    print(f"{'=' * 60}")

    from collections import Counter
    club_counter = Counter()

    for player in players:
        if not player or not isinstance(player, dict):
            continue

        if 'profile' in player and player['profile'] and isinstance(player['profile'], dict):
            if 'club' in player['profile'] and player['profile']['club'] and isinstance(player['profile']['club'],
                                                                                        dict):
                if 'id' in player['profile']['club'] and player['profile']['club']['id']:
                    club_id = str(player['profile']['club']['id'])
                    club_counter[club_id] += 1
        elif 'club' in player and player['club'] and isinstance(player['club'], dict):
            if 'id' in player['club'] and player['club']['id']:
                club_id = str(player['club']['id'])
                club_counter[club_id] += 1

    for club_id, count in club_counter.most_common(10):
        club_name = next((c.get('name', 'Unknown') for c in clubs if str(c.get('id', '')) == club_id), 'Unknown')
        print(f"   {club_id}: {club_name:<30} - {count} игроков")

    print(f"\n✅ Результат сохранен в: {output_file}")
    print(f"📁 Исходный файл не изменен: {clubs_file}")


if __name__ == "__main__":
    filter_clubs_by_players()