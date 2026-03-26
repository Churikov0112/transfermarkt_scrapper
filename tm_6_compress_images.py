import os
from PIL import Image

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp')
SKIP_DIRS = {'.git', '__pycache__'}


def has_images(folder_path):
    for filename in os.listdir(folder_path):
        full_path = os.path.join(folder_path, filename)
        if os.path.isfile(full_path) and filename.lower().endswith(IMAGE_EXTENSIONS):
            return True
    return False


def find_image_folders(root='.'):
    folders = []
    for name in sorted(os.listdir(root)):
        folder_path = os.path.join(root, name)
        if not os.path.isdir(folder_path):
            continue
        if name in SKIP_DIRS:
            continue
        if name.endswith('_compressed'):
            continue
        if has_images(folder_path):
            folders.append(folder_path)
    return folders


def convert_image_to_jpg(input_path, output_path):
    img = Image.open(input_path)

    if img.mode == 'RGBA':
        white_bg = Image.new('RGB', img.size, (255, 255, 255))
        white_bg.paste(img, (0, 0), img)
        img = white_bg
    elif img.mode == 'P' and 'transparency' in img.info:
        img = img.convert('RGBA')
        white_bg = Image.new('RGB', img.size, (255, 255, 255))
        white_bg.paste(img, (0, 0), img)
        img = white_bg
    else:
        img = img.convert('RGB')

    img.save(output_path, 'JPEG', quality=90, optimize=True)


def process_folder(input_folder):
    output_folder = f'{input_folder}_compressed'
    os.makedirs(output_folder, exist_ok=True)

    processed = 0
    errors = 0

    for filename in sorted(os.listdir(input_folder)):
        if not filename.lower().endswith(IMAGE_EXTENSIONS):
            continue

        input_path = os.path.join(input_folder, filename)
        if not os.path.isfile(input_path):
            continue

        output_filename = os.path.splitext(filename)[0] + '.jpg'
        output_path = os.path.join(output_folder, output_filename)

        try:
            convert_image_to_jpg(input_path, output_path)
            processed += 1
            print(f'[{input_folder}] Обработано: {filename} -> {output_filename}')
        except Exception as e:
            errors += 1
            print(f'[{input_folder}] Ошибка при обработке {filename}: {str(e)}')

    return processed, errors


def main():
    image_folders = find_image_folders('.')
    if not image_folders:
        print('Папки с изображениями не найдены.')
        return

    total_processed = 0
    total_errors = 0

    for folder_path in image_folders:
        folder_name = os.path.basename(folder_path)
        print(f'\nОбработка папки: {folder_name}')
        processed, errors = process_folder(folder_name)
        total_processed += processed
        total_errors += errors

    print('\nОбработка завершена! Все изображения сохранены с белым фоном.')
    print(f'Успешно: {total_processed}, ошибок: {total_errors}')


if __name__ == '__main__':
    main()
