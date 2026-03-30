import json
import os
from typing import Dict, List, Any, Optional


def load_json(filepath: str) -> Any:
    """Загружает JSON из файла."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, filepath: str) -> None:
    """Сохраняет данные в JSON файл."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_player_to_team_mapping(teams_path: str) -> Dict[str, Dict[str, str]]:
    """
    Создаёт словарь для быстрого поиска команды (сборной) по id игрока.
    Возвращает {player_id: {'team_id': id, 'team_name': name}}
    """
    if not os.path.exists(teams_path):
        print(f"Файл {teams_path} не найден, пропускаем создание маппинга команд")
        return {}

    teams = load_json(teams_path)
    player_to_team = {}

    for team in teams:
        team_id = team.get('id')
        team_name = team.get('name')
        players_ids = team.get('players_ids', [])

        for player_id in players_ids:
            player_to_team[player_id] = {
                'team_id': team_id,
                'team_name': team_name
            }

    print(f"Создан маппинг для {len(player_to_team)} игроков к национальным командам")
    return player_to_team


def load_players_urls(urls_path: str) -> Dict[str, int]:
    """
    Загружает данные из tm_players_urls.json и создаёт словарь
    {player_id: team_shirt_number} (number из оригинального файла)
    """
    if not os.path.exists(urls_path):
        print(f"Файл {urls_path} не найден, пропускаем загрузку номеров сборной")
        return {}

    players_urls = load_json(urls_path)
    player_to_team_number = {}

    for player in players_urls:
        player_id = player.get('id')
        team_number = player.get('number')  # Оригинальное поле называется number
        if player_id and team_number is not None:
            player_to_team_number[player_id] = team_number

    print(f"Загружены номера сборной для {len(player_to_team_number)} игроков")
    return player_to_team_number


def add_max_market_to_market_values(market_values_path: str) -> List[Dict[str, Any]]:
    """
    Добавляет поле maxMarketValue в каждый объект tm_players_market_values.
    Возвращает обновлённый список.
    """
    market_data = load_json(market_values_path)

    for item in market_data:
        history = item.get('marketValueHistory', [])
        if history:
            max_val = max(entry.get('marketValue', 0) for entry in history)
        else:
            max_val = item.get('marketValue', 0)

        item['maxMarketValue'] = max_val

    return market_data


def add_max_market_to_profiles(profiles_path: str, max_values: Dict[str, int],
                               team_numbers: Dict[str, int]) -> List[Dict[str, Any]]:
    """
    Добавляет поле maxMarketValue и team_shirt_number в profile каждого игрока.
    Возвращает обновлённый список профилей.
    """
    profiles = load_json(profiles_path)
    for player in profiles:
        player_id = player.get('id')

        # Проверяем, что profile существует и является словарём
        if player.get('profile') is None:
            player['profile'] = {}
        elif not isinstance(player['profile'], dict):
            print(
                f"Предупреждение: profile для игрока {player_id} имеет тип {type(player['profile'])}, заменяем на словарь")
            player['profile'] = {}

        # Добавляем maxMarketValue
        if player_id and player_id in max_values:
            player['profile']['maxMarketValue'] = max_values[player_id]

        # Добавляем team_shirt_number (номер в сборной)
        if player_id and player_id in team_numbers:
            player['profile']['team_shirt_number'] = team_numbers[player_id]

    return profiles


def clean_players_profiles(profiles: List[Dict[str, Any]], player_to_team: Dict[str, Dict[str, str]]) -> List[
    Dict[str, Any]]:
    """
    Преобразует список профилей игроков:
    - удаляет поля id и name на верхнем уровне
    - переносит все поля из profile на верхний уровень
    - удаляет из полученного объекта указанные поля
    - добавляет club_id, club_name, team_id, team_name
    - сохраняет team_shirt_number (уже добавлен в profile на предыдущем этапе)
    """
    cleaned = []
    fields_to_remove = {
        'fullName', 'updatedAt', 'url', 'description', 'nameInHomeCountry',
        'imageUrl', 'placeOfBirth', 'agent', 'socialMedia',
        'trainerProfile', 'relatives'
    }

    for player in profiles:
        player_id = player.get('id')
        profile = player.get('profile', {})

        # Если profile - не словарь, используем пустой словарь
        if not isinstance(profile, dict):
            print(f"Предупреждение: profile имеет тип {type(profile)}, использую пустой словарь")
            profile = {}

        # Переносим все поля из profile на верхний уровень
        new_player = {**profile}

        # Удаляем shirtNumber, если он есть (так как мы его не используем)
        new_player.pop('shirtNumber', None)

        # Извлекаем информацию о клубе
        club_info = profile.get('club')
        if club_info and isinstance(club_info, dict):
            new_player['club_id'] = club_info.get('id')
            new_player['club_name'] = club_info.get('name')
        else:
            new_player['club_id'] = None
            new_player['club_name'] = None

        # Добавляем информацию о национальной команде из маппинга
        if player_id and player_id in player_to_team:
            new_player['team_id'] = player_to_team[player_id]['team_id']
            new_player['team_name'] = player_to_team[player_id]['team_name']
        else:
            new_player['team_id'] = None
            new_player['team_name'] = None

        # Удаляем ненужные поля
        for field in fields_to_remove:
            new_player.pop(field, None)

        # Удаляем исходное поле club, так как данные из него уже извлечены
        new_player.pop('club', None)

        cleaned.append(new_player)

    return cleaned


def clean_clubs(clubs_path: str) -> List[Dict[str, Any]]:
    """
    Преобразует список клубов:
    - удаляет поля id, name, url на верхнем уровне
    - переносит все поля из profile на верхний уровень
    - удаляет из полученного объекта указанные поля
    """
    clubs = load_json(clubs_path)
    cleaned = []
    fields_to_remove = {
        'url', 'officialName', 'image', 'addressLine1', 'addressLine2',
        'addressLine3', 'tel', 'fax', 'website', 'members',
        'membersDate', 'squad', 'historicalCrests', 'otherSports',
        'currentTransferRecord'
    }
    for club in clubs:
        profile = club.get('profile', {})
        # Если profile - не словарь, используем пустой словарь
        if not isinstance(profile, dict):
            print(
                f"Предупреждение: profile для клуба {club.get('id')} имеет тип {type(profile)}, использую пустой словарь")
            profile = {}

        new_club = {**profile}
        for field in fields_to_remove:
            new_club.pop(field, None)
        cleaned.append(new_club)
    return cleaned


def clean_teams(teams_path: str) -> List[Dict[str, Any]]:
    """
    Преобразует список команд (национальных сборных):
    - удаляет поля players_ids и logo_url
    """
    teams = load_json(teams_path)
    cleaned = []
    for team in teams:
        # Создаём копию и удаляем ненужные поля
        new_team = {k: v for k, v in team.items() if k not in ('players_ids', 'logo_url')}
        cleaned.append(new_team)
    return cleaned


def main():
    # Пути к исходным файлам
    market_values_file = "tm_players_market_values.json"
    players_profiles_file = "tm_players_profiles.json"
    players_urls_file = "tm_players_urls.json"
    clubs_file = "tm_clubs.json"
    teams_file = "tm_teams.json"

    # 0. Создаём маппинг игроков к национальным командам
    player_to_team = build_player_to_team_mapping(teams_file)

    # 0.1. Загружаем номера сборной из tm_players_urls
    team_numbers = load_players_urls(players_urls_file)

    # 1. Добавляем maxMarketValue в market values и сохраняем
    if os.path.exists(market_values_file):
        print(f"Обработка {market_values_file}...")
        market_with_max = add_max_market_to_market_values(market_values_file)
        save_json(market_with_max, "prepared_tm_players_market_values.json")
        print(f"Создан prepared_tm_players_market_values.json с {len(market_with_max)} записями")

        # Вычисляем max_values для добавления в профили
        max_values = {item['id']: item['maxMarketValue'] for item in market_with_max}
    else:
        print(f"Файл {market_values_file} не найден. Пропускаем.")
        max_values = {}

    # 2. Добавляем maxMarketValue и team_shirt_number в профили игроков
    profiles_with_max = []
    if os.path.exists(players_profiles_file):
        print(f"Обработка {players_profiles_file}...")
        profiles_with_max = add_max_market_to_profiles(players_profiles_file, max_values, team_numbers)
        print(f"Обработано {len(profiles_with_max)} профилей игроков")
    else:
        print(f"Файл {players_profiles_file} не найден. Пропускаем.")

    # 3. Очищаем профили игроков и сохраняем
    if profiles_with_max:
        print("Создание prepared_tm_players_profiles.json...")
        cleaned_profiles = clean_players_profiles(profiles_with_max, player_to_team)
        save_json(cleaned_profiles, "prepared_tm_players_profiles.json")
        print(f"Сохранено {len(cleaned_profiles)} записей")

        # Выводим статистику по заполненным командам
        teams_filled = sum(1 for p in cleaned_profiles if p.get('team_id') is not None)
        print(f"Из них {teams_filled} игроков имеют информацию о национальной команде")

        # Выводим статистику по номерам сборной
        team_numbers_filled = sum(1 for p in cleaned_profiles if p.get('team_shirt_number') is not None)
        print(f"Из них {team_numbers_filled} игроков имеют номер в сборной")

    # 4. Очищаем клубы и сохраняем
    if os.path.exists(clubs_file):
        print(f"Обработка {clubs_file}...")
        cleaned_clubs = clean_clubs(clubs_file)
        save_json(cleaned_clubs, "prepared_tm_clubs.json")
        print(f"Сохранено {len(cleaned_clubs)} записей")
    else:
        print(f"Файл {clubs_file} не найден. Пропускаем.")

    # 5. Очищаем команды и сохраняем
    if os.path.exists(teams_file):
        print(f"Обработка {teams_file}...")
        cleaned_teams = clean_teams(teams_file)
        save_json(cleaned_teams, "prepared_tm_teams.json")
        print(f"Сохранено {len(cleaned_teams)} записей")
    else:
        print(f"Файл {teams_file} не найден. Пропускаем.")

    print("Готово!")


if __name__ == "__main__":
    main()