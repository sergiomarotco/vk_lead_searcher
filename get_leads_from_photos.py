"""
get_leads_from_photos.py

Модуль для выгрузки лидов из фото групп VK за последние дни.

Содержит:
- Функции для получения альбомов, фото, комментариев и лайков.
- Основную функцию для обработки групп и сохранения результатов в файлы.

Автор: sergiomarotco, https://github.com/sergiomarotco/vk_lead_searcher
Дата: 2025-01-10
"""
import os
import classes.bcolors as b
import classes.vk_api_params as vk_p
import classes.file_params as file_params
import vk_api
import json
import argparse
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from tqdm import tqdm

from classes.vk_api_params import API_VERSION

PHOTOS_COMMENTS_FILE: str = file_params.FileParams.PHOTOS_COMMENTS_FILE
PHOTOS_LIKES_FILE: str = file_params.FileParams.PHOTOS_LIKES_FILE
GROUPS_SEARCH_ACTUAL_FILE: str = file_params.GROUPS_SEARCH_ACTUAL_FILE


def load_groups_from_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def unix_days_ago(days):
    return int((datetime.now() - timedelta(days=days)).timestamp())


def get_all_albums(vk, owner_id, since_ts):
    albums = []
    offset = 0
    while True:
        response = vk.photos.getAlbums(
            owner_id=owner_id,
            offset=offset#,
            #count=100
        )
        alb_good: list = []
        for alb in response["items"]:
            if alb['size'] > 0 and alb["updated"] >= since_ts:
                alb_good.append(
                    {
                        "id": alb["id"],
                        "title": alb["title"],
                        "size": alb["size"],
                        "link": f"{vk_p.URI}/album{owner_id}_{alb['id']}",
                        "created_norm": datetime.fromtimestamp(alb["created"]).isoformat(),
                        "created": alb["created"],
                        "updated_norm": datetime.fromtimestamp(alb["updated"]).isoformat(),
                        "updated": alb["updated"]
                    }
                )
        if len(alb_good) > 0:
            albums.extend(alb_good)

        if offset + 100 >= response["count"]:
            break
        offset += 100
        time.sleep(0.34)
    return albums


def get_photos_from_album(vk, owner_id, album_id, since_ts):
    photos = []
    offset = 0
    while True:
        response = vk.photos.get(
            owner_id=owner_id,
            album_id=album_id,
            offset=offset,
            count=10,
            extended=1,
            photo_sizes=0,
            rev=1
        )
        for photo in response["items"]:
            if photo["date"] >= since_ts:
                photos.append(photo)  # собираем фото, если дата подходит
        if offset + 100 >= response["count"]:
            break
        offset += 100
        time.sleep(0.34)
    return photos


def get_comments(vk, owner_id, photo_id, since_ts):
    comments = []
    offset = 0
    while True:
        response = vk.photos.getComments(
            owner_id=owner_id,
            photo_id=photo_id,
            offset=offset,
            count=100,
            sort='desc'
        )
        for c in response["items"]:
            if c["date"] >= since_ts:  # собираем комментарии, если дата подходит
                comments.append({
                    "comment_id": c["id"],
                    "text": c["text"],
                    "author_id": c["from_id"],
                    "author_link": f"{vk_p.URI}/id{c['from_id']}",
                    "date": c["date"]
                })
        if offset + 100 >= response["count"]:
            break
        offset += 100
        time.sleep(0.34)
    return comments


def get_likes(vk, owner_id, photo_id):
    likes = []
    offset = 0
    while True:
        response = vk.likes.getList(
            type="photo",
            owner_id=owner_id,
            item_id=photo_id,
            offset=offset,
            count=100,
            skip_own=True
        )
        for uid in response["items"]:
            likes.append({
                "user_id": uid,
                "user_link": f"{vk_p.URI}/id{uid}"
            })
        if offset + 100 >= response["count"]:
            break
        offset += 100
        time.sleep(0.34)
    return likes


def main_get_leads_from_photos(token: str, infile=GROUPS_SEARCH_ACTUAL_FILE, days: int = 2):
    vk_session = vk_api.VkApi(token=token, api_version=API_VERSION)
    vk = vk_session.get_api()

    try:
        groups_actual = load_groups_from_file(infile)
    except Exception as e:
        raise SystemExit(f"Не удалось загрузить {b.BLUE}{infile}{b.END}: {b.RED}{e}{b.END}")

    groups = groups_actual.get("groups") if isinstance(groups_actual, dict) else groups_actual
    if not isinstance(groups, list):
        raise SystemExit(b.END + "Входной файл не содержит список групп в поле `groups`" + b.END)
    since_ts = unix_days_ago(days)

    all_comments = []
    all_likes = []

    with tqdm(groups, desc="Обработка групп", unit=" группа ") as pbar_groups:
        for group in pbar_groups:
            try:
                pbar_groups.set_postfix({"группа": b.YELLOW + group['group_link'] + b.END})
                owner_id = -group['id']
                albums = get_all_albums(vk, owner_id, since_ts)
                #albums.append({"id": 0, "title": "Фотографии со стены"})  # альбом со стены
                with tqdm(albums, desc="  Обработка альбомов", unit=" альбом ") as pbar_albums:
                    for album in pbar_albums:
                        album['link'] = f"{vk_p.URI}/album{owner_id}_{album['id']}"
                        pbar_albums.set_postfix({"альбом": b.YELLOW + album['link'] + b.END})
                        photos = get_photos_from_album(vk, owner_id, album["id"], since_ts)
                        if len(photos) > 0:
                            print(f"    найдено фото: {b.GREEN}{len(photos)}{b.END} шт.")
                        with tqdm(photos, desc="    Обработка фото", unit=" фото ") as pbar_photo:
                            for photo in pbar_photo:
                                photo_url = f"{vk_p.URI}/photo{owner_id}_{photo['id']}"

                                comments = get_comments(vk, owner_id, photo["id"], since_ts)
                                for comment in comments:
                                    if 'date' in comment:
                                        comment['date'] = datetime.fromtimestamp(comment['date']).isoformat()
                                if len(comments) > 0:
                                    print(f"      найдено комментариев: {b.GREEN}{len(comments)}{b.END} шт.")
                                if comments:
                                    all_comments.append({
                                        "photo_url": photo_url,
                                        "comments": comments
                                    })

                                likes = get_likes(vk, owner_id, photo["id"])
                                if len(likes) > 0:
                                    print(f"      найдено лайков: {b.GREEN}{len(likes)}{b.END} шт.")
                                if likes:
                                    all_likes.append({
                                        "photo_url": photo_url,
                                        "likes": likes
                                    })

            except Exception as e:
                print(f"    Ошибка в группе {group['group_link']}: {b.RED}{e}{b.END}")
                continue
    if len(all_comments) > 0:
        with open(PHOTOS_COMMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_comments, f, ensure_ascii=False, indent=2)
            print(f"{b.GREEN}Итого: Комментарии к фото сохранены{b.END} в {b.BLUE}{PHOTOS_COMMENTS_FILE}{b.END}")
    else:
        print(f"Комментарии к фото {b.RED}не сохранены{b.END} в {b.BLUE}{PHOTOS_COMMENTS_FILE}{b.END} так как {b.RED}не были найдены{b.END}.")

    if len(all_likes) > 0:
        with open(PHOTOS_LIKES_FILE, "w", encoding="utf-8") as f:
            json.dump(all_likes, f, ensure_ascii=False, indent=2)
            print(f"{b.GREEN}Лайки фото сохранены{b.END} в {b.BLUE}{PHOTOS_LIKES_FILE}{b.END}")
    else:
        print(f"Лайки к фото {b.RED}не сохранены{b.END} в {b.BLUE}{PHOTOS_LIKES_FILE}{b.END} так как {b.RED}не были найдены{b.END}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Выгрузить фото и комментарии из групп VK за последние дни")
    parser.add_argument("--token", "-t", help="VK access token (или через VK_TOKEN env)", default=os.getenv("VK_TOKEN"))
    parser.add_argument("--days", "-d", type=int, help="Количество дней для сбора лайков и комментариев", default=2)
    parser.add_argument("--in", "-in", dest="infile", help="Файл с группами", default=GROUPS_SEARCH_ACTUAL_FILE)
    args = parser.parse_args()
    token = args.token
    days = args.days
    infile = args.infile
    main_get_leads_from_photos(token, infile, days)
