import json


def extract_unique_citizenships(input_file, output_file):
    """
    Извлекает уникальные значения citizenship из JSON-файла
    и сохраняет их в новый JSON-файл.
    """
    # Чтение исходного JSON-файла
    with open(input_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Сбор уникальных стран
    unique_countries = set()

    for item in data:
        # citizenship может быть списком строк
        if 'citizenship' in item and isinstance(item['citizenship'], list):
            for country in item['citizenship']:
                unique_countries.add(country)

    # Преобразование set в отсортированный список
    unique_countries_list = sorted(list(unique_countries))

    # Сохранение результата в новый JSON-файл
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(unique_countries_list, file, ensure_ascii=False, indent=2)

    print(f"Найдено уникальных стран: {len(unique_countries_list)}")
    print(f"Результат сохранён в файл: {output_file}")

    return unique_countries_list


# Использование скрипта
if __name__ == "__main__":
    input_filename = "tm_players_profiles.json"  # Имя вашего исходного файла
    output_filename = "unique_citizenships.json"  # Имя выходного файла

    try:
        countries = extract_unique_citizenships(input_filename, output_filename)
        print("\nСписок стран:")
        for country in countries:
            print(f"  - {country}")
    except FileNotFoundError:
        print(f"Ошибка: Файл '{input_filename}' не найден!")
    except json.JSONDecodeError:
        print(f"Ошибка: Файл '{input_filename}' содержит некорректный JSON!")
    except KeyError as e:
        print(f"Ошибка: В данных отсутствует поле {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")