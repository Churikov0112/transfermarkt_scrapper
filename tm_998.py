import json
from typing import Dict, List, Any


def merge_market_values():
    # Загрузка данных из файлов
    print("Загрузка файлов...")

    with open('tm_players_profiles.json', 'r', encoding='utf-8') as f:
        players = json.load(f)

    with open('tm_players_market_values.json', 'r', encoding='utf-8') as f:
        market_values = json.load(f)

    # Создаем словарь для быстрого поиска maxMarketValue по id
    market_value_dict: Dict[str, int] = {}
    for mv in market_values:
        player_id = mv.get('id')
        max_value = mv.get('maxMarketValue')
        if player_id and max_value is not None:
            market_value_dict[player_id] = max_value

    # Добавляем maxMarketValue к каждому игроку
    print("Обработка игроков...")
    matched_count = 0
    not_found_count = 0

    for player in players:
        player_id = player.get('id')
        if player_id and player_id in market_value_dict:
            player['maxMarketValue'] = market_value_dict[player_id]
            matched_count += 1
        else:
            player['maxMarketValue'] = None  # или можно не добавлять поле
            not_found_count += 1
            print(f"Не найден maxMarketValue для игрока {player.get('name', 'Unknown')} (id: {player_id})")

    # Сохраняем результат в новый файл
    output_file = 'tm_players_profiles_with_max_value.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

    print(f"\nГотово!")
    print(f"Найдено совпадений: {matched_count}")
    print(f"Не найдено: {not_found_count}")
    print(f"Результат сохранен в файл: {output_file}")


if __name__ == "__main__":
    merge_market_values()