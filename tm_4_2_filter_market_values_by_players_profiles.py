import json
import argparse
from pathlib import Path


def filter_market_values_to_new_file(profiles_file='tm_players_profiles.json',
                                     market_values_file='tm_players_market_values.json',
                                     output_file='prepared_tm_players_market_values_filtered.json'):
    """
    Фильтрует данные о рыночной стоимости, оставляя только игроков из profiles_file

    Args:
        profiles_file: путь к файлу с профилями игроков
        market_values_file: путь к файлу с рыночной стоимостью
        output_file: путь для сохранения отфильтрованных данных
    """

    # Проверяем существование файлов
    if not Path(profiles_file).exists():
        print(f"❌ Ошибка: Файл {profiles_file} не найден!")
        return

    if not Path(market_values_file).exists():
        print(f"❌ Ошибка: Файл {market_values_file} не найден!")
        return

    # Загружаем профили игроков
    print(f"📖 Загрузка профилей из {profiles_file}...")
    with open(profiles_file, 'r', encoding='utf-8') as f:
        profiles = json.load(f)

    # Загружаем данные о рыночной стоимости
    print(f"📖 Загрузка рыночной стоимости из {market_values_file}...")
    with open(market_values_file, 'r', encoding='utf-8') as f:
        market_values = json.load(f)

    # Создаем множество ID из профилей
    profile_ids = {profile['id'] for profile in profiles}

    # Фильтруем market_values
    filtered_market_values = []
    missing_ids = []

    for mv in market_values:
        if mv['id'] in profile_ids:
            filtered_market_values.append(mv)
        else:
            missing_ids.append(mv['id'])

    # Сохраняем в новый файл
    print(f"💾 Сохранение результата в {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_market_values, f, ensure_ascii=False, indent=2)

    # Выводим статистику
    print(f"\n{'=' * 60}")
    print(f"Статистика фильтрации:")
    print(f"{'=' * 60}")
    print(f"📊 Профилей игроков:          {len(profile_ids):>10,}")
    print(f"📊 Исходных записей стоимости: {len(market_values):>10,}")
    print(f"📊 Отфильтровано записей:     {len(filtered_market_values):>10,}")
    print(f"📊 Удалено записей:           {len(missing_ids):>10,}")

    if missing_ids:
        match_rate = (len(filtered_market_values) / len(market_values)) * 100
        print(f"\n📈 Процент совпадения: {match_rate:.2f}%")

        if len(missing_ids) <= 10:
            print(f"\n❌ Удаленные ID: {', '.join(missing_ids)}")
        elif len(missing_ids) <= 30:
            print(f"\n❌ Удаленные ID (первые 10 из {len(missing_ids)}): {', '.join(missing_ids[:10])}")

    print(f"\n✅ Результат сохранен в: {output_file}")
    print(f"📁 Исходный файл не изменен: {market_values_file}")


if __name__ == "__main__":
    # Простой запуск с настройками по умолчанию
    filter_market_values_to_new_file()

    # Если нужен расширенный вариант с аргументами командной строки:
    # parser = argparse.ArgumentParser(description='Фильтрация рыночной стоимости игроков')
    # parser.add_argument('--profiles', default='tm_players_profiles.json', help='Файл с профилями')
    # parser.add_argument('--market', default='tm_players_market_values.json', help='Файл с рыночной стоимостью')
    # parser.add_argument('--output', default='tm_players_market_values_filtered.json', help='Выходной файл')
    # args = parser.parse_args()
    # filter_market_values_to_new_file(args.profiles, args.market, args.output)