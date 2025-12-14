"""
generate_report.py

Модуль для генерации отчета по лайкам и комментариям.

Содержит:
- Функцию для чтения JSON файлов.
- Основную функцию для генерации и сохранения отчета в текстовый файл.

Автор: sergiomarotco, https://github.com/sergiomarotco/vk_lead_searcher
Дата: 2025-01-10
"""
import json
import classes.bcolors as b
import classes.file_params as file_params


def read_json(path: str) -> dict:
    """
    Прочитать json файл
    :param path: Путь к файлу
    :return: Содержимое файла в виде словаря
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

photos_likes_array = read_json(file_params.PHOTOS_LIKES_FILE)
photos_comments_array = read_json(file_params.PHOTOS_COMMENTS_FILE)
wall_comments_array = read_json(file_params.WALL_COMMENTS_FILE)
wall_likes_array = read_json(file_params.WALL_LIKES_FILE)

def main_generate_report() -> None:
    """
    Сохранить отчет по лайкам и комментариям в файл
    :rtype: None
    :return: Файл с отчетом
    """
    report = []
    unic_leads = []
    for photos_like in photos_likes_array:
        photos_likes = photos_like['likes']
        photo_url = photos_like['photo_url']
        for like in photos_likes:
            report.append(f"{like['user_link']} поставил лайк к фото {photo_url}")
            unic_leads.append(like['user_link'])
    for photos_comment in photos_comments_array:
        photos_comments = photos_comment['comments']
        photo_url = photos_comment['photo_url']
        for comment in photos_comments:
            report.append(f"{comment['author_link']} оставил комментарий '{comment['text']}' к фото {photo_url}")
            unic_leads.append(comment['author_link'])
    for wall_like in wall_likes_array:
        report.append(f"{wall_like['liker_url']} лайкнул пост {wall_like['post_url']}")
        unic_leads.append(wall_like['liker_url'])
    for wall_comment in wall_comments_array:
        report.append(f"{wall_comment['author_url']} оставил комментарий к посту на стене {wall_comment['post_url']}")
        unic_leads.append(wall_comment['author_url'])

    # Записываем в файл активность лидов в группах
    result = list(dict.fromkeys(report))  # Удаление дубликатов
    result = sorted(result)
    with open(file_params.REPORT_FILE, "w", encoding="utf-8") as f:
        for item in result:
            f.write(f"{item}\n")
        print(f"{b.GREEN}Отчет сохранен в файл:{b.END} {b.BLUE}{file_params.REPORT_FILE}{b.END}")

    # Записываем в файл уникальных пользователей
    unic_users = list(dict.fromkeys(unic_leads))  # Удаление дубликатов
    unic_users = sorted(unic_users)
    with open(file_params.REPORT_UNIC_USERS, "w", encoding="utf-8") as f:
        for unic_user in unic_users:
            f.write(f"{unic_user}\n")
        print(f"{b.GREEN}Уникальные лиды сохранены в :{b.END} {b.BLUE}{file_params.REPORT_UNIC_USERS}{b.END}")

if __name__ == "__main__":
    main_generate_report()
