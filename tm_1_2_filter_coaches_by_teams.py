import json
from pathlib import Path
from collections import Counter


def filter_coaches_by_teams(teams_file='tm_teams.json',
                            coaches_file='tm_coach_profiles.json',
                            output_file='tm_coach_profiles_filtered.json'):
    """
    Фильтрует тренеров, оставляя только тех, чей id встречается в coach_id у команд

    Args:
        teams_file: путь к файлу с командами
        coaches_file: путь к файлу с профилями тренеров
        output_file: путь для сохранения отфильтрованных тренеров
    """

    # Проверяем существование файлов
    if not Path(teams_file).exists():
        print(f"❌ Ошибка: Файл {teams_file} не найден!")
        return

    if not Path(coaches_file).exists():
        print(f"❌ Ошибка: Файл {coaches_file} не найден!")
        return

    # Загружаем данные о командах
    print(f"📖 Загрузка команд из {teams_file}...")
    with open(teams_file, 'r', encoding='utf-8') as f:
        teams = json.load(f)

    # Загружаем данные о тренерах
    print(f"📖 Загрузка тренеров из {coaches_file}...")
    with open(coaches_file, 'r', encoding='utf-8') as f:
        coaches = json.load(f)

    # Собираем множество уникальных ID тренеров из команд
    coach_ids_from_teams = set()
    teams_without_coach = 0
    invalid_coach_ids = 0

    for team in teams:
        if not team or not isinstance(team, dict):
            continue

        coach_id = team.get('coach_id')

        if coach_id:
            # Преобразуем в строку для единообразия
            coach_id_str = str(coach_id)

            # Проверяем, что coach_id не пустая строка
            if coach_id_str and coach_id_str.strip():
                coach_ids_from_teams.add(coach_id_str)
            else:
                invalid_coach_ids += 1
        else:
            teams_without_coach += 1

    # Фильтруем тренеров
    filtered_coaches = []
    missing_coach_ids = []
    coaches_without_id = 0

    for coach in coaches:
        if not coach or not isinstance(coach, dict):
            continue

        coach_id = coach.get('id')

        if not coach_id:
            coaches_without_id += 1
            continue

        coach_id_str = str(coach_id)

        if coach_id_str in coach_ids_from_teams:
            filtered_coaches.append(coach)
        else:
            missing_coach_ids.append(coach_id_str)

    # Сохраняем результат
    print(f"💾 Сохранение результата в {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_coaches, f, ensure_ascii=False, indent=2)

    # Выводим статистику
    print(f"\n{'=' * 60}")
    print(f"Статистика фильтрации тренеров:")
    print(f"{'=' * 60}")
    print(f"📊 Всего команд:                      {len(teams):>10,}")
    print(f"📊 Команд без coach_id:               {teams_without_coach:>10,}")
    print(f"📊 Команд с невалидным coach_id:      {invalid_coach_ids:>10,}")
    print(f"📊 Уникальных тренеров в командах:    {len(coach_ids_from_teams):>10,}")
    print(f"📊 Всего тренеров в файле:            {len(coaches):>10,}")
    print(f"📊 Тренеров без id:                   {coaches_without_id:>10,}")
    print(f"📊 Оставлено тренеров:                {len(filtered_coaches):>10,}")
    print(f"📊 Удалено тренеров:                  {len(missing_coach_ids):>10,}")

    if missing_coach_ids:
        match_rate = (len(filtered_coaches) / len(coaches)) * 100 if coaches else 0
        print(f"\n📈 Процент совпадения: {match_rate:.2f}%")

        # Показываем несколько примеров
        if len(missing_coach_ids) <= 10:
            print(f"\n❌ Тренеры не найденные в командах (ID): {', '.join(missing_coach_ids)}")
        else:
            print(f"\n❌ Примеры тренеров не найденных в командах (первые 10 из {len(missing_coach_ids)}):")
            for coach_id in missing_coach_ids[:10]:
                coach_name = next((c.get('name', 'Unknown') for c in coaches if str(c.get('id', '')) == coach_id),
                                  'Unknown')
                print(f"   - ID {coach_id}: {coach_name}")

    # Показываем команды, у которых есть тренеры (дополнительная статистика)
    print(f"\n{'=' * 60}")
    print(f"Топ-10 стран/команд с указанными тренерами:")
    print(f"{'=' * 60}")

    team_coach_counter = Counter()
    for team in teams:
        if not team or not isinstance(team, dict):
            continue

        coach_id = team.get('coach_id')
        if coach_id:
            coach_id_str = str(coach_id)
            if coach_id_str in coach_ids_from_teams:
                team_name = team.get('name', 'Unknown')
                team_coach_counter[team_name] += 1

    for team_name, count in team_coach_counter.most_common(10):
        print(f"   {team_name:<30} - тренер указан (1 команда)")

    # Показываем информацию о найденных тренерах
    print(f"\n{'=' * 60}")
    print(f"Найденные тренеры в командах (первые 10):")
    print(f"{'=' * 60}")

    found_coaches = []
    for coach_id in list(coach_ids_from_teams)[:10]:
        coach_info = next((c for c in coaches if str(c.get('id', '')) == coach_id), None)
        if coach_info:
            coach_name = coach_info.get('name', 'Unknown')
            current_club = coach_info.get('current_club', {})
            club_name = current_club.get('name', 'No club') if current_club else 'No club'
            found_coaches.append((coach_id, coach_name, club_name))

    for coach_id, coach_name, club_name in found_coaches:
        print(f"   ID {coach_id}: {coach_name:<25} - тренирует {club_name}")

    print(f"\n✅ Результат сохранен в: {output_file}")
    print(f"📁 Исходный файл не изменен: {coaches_file}")


if __name__ == "__main__":
    filter_coaches_by_teams()