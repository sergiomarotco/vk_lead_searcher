"""
get_leads_from_wall.py

Модуль для выгрузки постов, комментариев и лайков стены ВКонтакте.

Содержит:
- Загрузку групп из файла.
- Получение постов из стен групп за последние N дней.
- Получение комментариев и пользователей оставивших лайк для каждого поста.
- Сохранение результатов в JSON файлы.

Автор: sergiomarotco, https://github.com/sergiomarotco/vk_lead_searcher
Дата: 2025-01-10
"""
import argparse
import os
import time
import json
from typing import List, Dict, Any
import vk_api
from tqdm import tqdm
from vk_api.exceptions import ApiError
from classes import vk_api_params as vk_p, bcolors as b, file_params as f_p
from get_leads_from_photos import get_comments

VK_TOKEN_ENV = "VK_API_TOKEN"
POSTS_FILE = f_p.WALL_POSTS
WALL_COMMENTS_FILE = f_p.WALL_COMMENTS_FILE
WALL_LIKES_FILE = f_p.WALL_LIKES_FILE
GROUPS_SEARCH_ACTUAL_FILE = f_p.GROUPS_SEARCH_ACTUAL_FILE
REQUEST_COUNT = 20


def load_groups_from_file(path: str) -> Dict[str, Any]:
    """
        Загрузить группы из файла
        :param path: Путь к файлу
        :return: Группы
        """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_int_like(x: str) -> bool:
    """
    Является ли строка целым числом
    :param x: Проверяемая строка
    :return: True если строка является целым числом, иначе False
    """
    try:
        int(x)
        return True
    except Exception:
        return False


def owner_arg_from_identifier(identifier: Any) -> Dict[str, Any]:
    """
    Построить аргумент owner_id или domain для методов API VK из идентификатора группы
    :param identifier: Идентификатор группы (число или строка)
    :return: Словарь с ключом owner_id или domain
    """
    # Если числовой — вернём owner_id = -abs(id) для группы.
    # Если строка — будем использовать domain.
    if is_int_like(identifier):
        gid = int(identifier)
        # В файле может быть id без знака; для групп используем отрицательный owner_id
        return {"owner_id": -abs(gid)}
    return {"domain": str(identifier)}


def fetch_wall_posts(vk, identifier: Any, cutoff_ts: int):
    """
    Получить посты со стены группы до cutoff_ts
    :param vk: VK API объект
    :param identifier: Идентификатор группы
    :param cutoff_ts: Пороговое время в формате unix timestamp
    :return: Список постов
    """
    wall_posts = []
    offset = 0
    while True:
        params = {"count": REQUEST_COUNT, "offset": offset, "filter": "owner", "domain": identifier['id']}
        params.update(owner_arg_from_identifier(identifier['screen_name']))
        resp: dict = {}
        try:
            resp = vk.wall.get(**params)
        except ApiError as e:
            print(f"Ошибка получения постов группы {identifier['id']}: {b.RED}{e}{b.END}")
            # if 'error' in e and 'error_code' in e['error'] and e['error']['error_code'] == 18:  # Пользователь или группа удалены, или заблокированы
            #bad_users.append(identifier['id'])
        posts_array = resp.get("items", [])
        if not posts_array:
            break
        for post_i in posts_array:
            if post_i.get("date", 0) < cutoff_ts:
                # посты идут от новых к старым — можно закончить для этой группы
                return wall_posts
            # сохраняем минимальную информацию + raw
            wall_posts.append({
                "group": identifier,
                "post_id": post_i.get("id"),
                "owner_id": post_i.get("owner_id"),
                "date": post_i.get("date"),
                "text": post_i.get("text"),
                "raw": post_i
            })
        offset += len(posts_array)
        # защитимся от бесконечного цикла
        if offset >= resp.get("count", 0):
            break
        time.sleep(0.34)  # небольшой throttle
    return wall_posts


def build_post_link(owner_id: int, post_id: int) -> str:
    """
    Сгенерировать ссылку на пост
    :param owner_id: id владельца стены
    :param post_id: id поста
    :return: ссылка на пост
    """
    # owner_id в API может быть отрицательным для групп; в ссылке используется знак: wall{owner_id}_{post_id}
    return f"{vk_p.URI}/wall{owner_id}_{post_id}"


def build_author_link(from_id: int) -> str:
    """
    Сгенерировать ссылку на автора по from_id
    :param from_id: id автора комментария или лайка
    :return: ссылка на автора
    """
    if from_id < 0:
        return f"{vk_p.URI}/club{abs(from_id)}"
    return f"{vk_p.URI}/id{from_id}"


def fetch_comments_for_post(vk, owner_id: int, post_id: int) -> List[Dict[str, Any]]:
    """
    Получить комментарии для поста
    :param vk: VK API объект
    :param owner_id: id владельца стены
    :param post_id: id поста
    :return: Список комментариев к посту
    """
    comments = []
    offset = 0
    while True:
        try:
            resp = vk.wall.getComments(
                owner_id=owner_id,
                post_id=post_id,
                need_likes=0,
                count=REQUEST_COUNT,
                offset=offset, extended=0
            )
        except ApiError as e:
            print(f"API error while fetching comments for post {post_id} (owner {owner_id}): {e}")
            break
        items = resp.get("items", [])
        if not items:
            break
        for c in items:
            from_id = c.get("from_id", 0)
            comments.append({
                "owner_id": owner_id,
                "post_id": post_id,
                "comment_id": c.get("id"),
                "date": c.get("date"),
                "text": c.get("text"),
                "post_url": build_post_link(owner_id, post_id),
                "author_id": from_id,
                "author_url": build_author_link(from_id),
                "raw": c
            })
        offset += len(items)
        if offset >= resp.get("count", 0):
            break
        time.sleep(0.34)
    return comments


def fetch_likes_from_post(vk, owner_id: int, post_id: int) -> List[Dict[str, Any]]:
    """
    Получить пользователей, поставивших лайк посту
    :param vk: VK API объект
    :param owner_id: id владельца стены
    :param post_id: id поста
    :return: Список пользователей, поставивших лайк посту
    """
    users_liked_post = []
    offset = 0
    while True:
        try:
            resp = vk.likes.getList(type="post", owner_id=owner_id, item_id=post_id, count=REQUEST_COUNT, offset=offset)
        except ApiError as e:
            print(f"Ошибка API при получении данных о пользователях, поставивших лайк к посту {post_id} (владелец {owner_id}): {e}")
            break
        items = resp.get("items", [])
        if not items:
            break
        for uid in items:
            users_liked_post.append({
                "owner_id": owner_id,
                "post_id": post_id,
                "liker_id": uid,
                "liker_url": build_author_link(uid),
                "post_url": build_post_link(owner_id, post_id),
                "raw": uid
            })
        offset += len(items)
        if offset >= resp.get("count", 0):
            break
        time.sleep(0.35)
    return users_liked_post


def get_posts(groups: list, vk, cutoff):
    all_posts: list = []
    with tqdm(groups, desc="Обработка групп", unit=" группа ") as pbar:
        for g in pbar:
            pbar.set_postfix({"id группы": b.YELLOW + g['group_link'] + " " + g['name'] + b.END})
            try:
                posts = fetch_wall_posts(vk, g, cutoff)
                if len(posts) > 0:
                    all_posts.extend(posts)
                    print(f"  найдено постов: {b.GREEN}{len(posts)}{b.END} шт. к группе {g['group_link']}")
            except Exception as e:
                print(f"\nОшибка для группы {g['group_link']}: {e}")
    return all_posts


def get_wall_comments(all_posts, vk):
    all_comments: list = []
    with tqdm(all_posts, desc="Получение комментариев постам", unit=" пост ") as pbar:
        for p in pbar:
            comments: int = p['raw']["comments"]["count"]
            if comments > 0:
                owner_id = p["owner_id"]
                post_id = p["post_id"]
                pbar.set_postfix(
                    {
                        "пост": b.YELLOW + f"{vk_p.URI}/{p['group']['screen_name']}?w=wall{owner_id}_{post_id}" + b.END
                    })
                try:
                    comments: list = fetch_comments_for_post(vk, owner_id, post_id)
                    if len(comments) > 0:
                        all_comments.extend(comments)
                        print(f"  комментариев: {b.GREEN}{len(comments)}{b.END} шт.")
                except Exception as e:
                    print(f"Ошибка при получении комментариев для поста {post_id}: {b.RED}{e}{b.END}")
    return all_comments


def get_wall_likes(all_posts, vk):
    all_users_liked_wall_post = []
    with tqdm(all_posts, desc="Получение пользователей оставивших лайк к постам", unit=" пост ") as pbar:
        for p in pbar:
            likes: int = p['raw']["likes"]["count"]
            if likes > 0:
                owner_id = p["owner_id"]
                post_id = p["post_id"]
                pbar.set_postfix(
                    {
                        "пост": b.YELLOW + f"{vk_p.URI}/{p['group']['screen_name']}?w=wall{owner_id}_{post_id}" + b.END
                    }
                )
                try:
                    likes_data = fetch_likes_from_post(vk, owner_id, post_id)
                    if len(likes_data) > 0:
                        all_users_liked_wall_post.extend(likes_data)
                        print(f"  лайкнули: {b.GREEN}{len(likes_data)}{b.END} шт.: {b.YELLOW}{likes_data[0]['post_url']}{b.END}")
                except Exception as e:
                    print(f"Ошибка при получении пользователей оставивших лайк к посту {post_id}: {b.RED}{e}{b.END}")
    return all_users_liked_wall_post


def main_get_leads_from_wall(access_token: str, file=GROUPS_SEARCH_ACTUAL_FILE, days_wall_max: int = 15) -> None:
    """
    Основная функция для выгрузки постов, комментариев и лайков стены ВКонтакте.
    :param access_token: VK access token
    :param file: Файл с группами
    :param days_wall_max: Количество дней для сбора постов
    :rtype: None
    """
    session = vk_api.VkApi(token=access_token)  # инициализация сессии VK
    vk = session.get_api()  # объект для вызова методов API

    try:
        groups_actual = load_groups_from_file(file)
    except Exception as e:
        raise SystemExit(f"Не удалось загрузить {b.BLUE}{file}{b.END}: {b.RED}{e}{b.END}")

    groups = groups_actual.get("groups") if isinstance(groups_actual, dict) else groups_actual
    if not isinstance(groups, list):
        raise SystemExit(b.END + "Входной файл не содержит список групп в поле `groups`" + b.END)
    now_ts = int(time.time())  # текущее время в секундах с эпохи
    seconds = days_wall_max * 24 * 60 * 60  # дни в секунды
    cutoff = now_ts - seconds  # пороговое время

    # Собираем посты со стен групп
    all_posts = get_posts(groups, vk, cutoff)

    # Сохраняем посты
    if len(all_posts) > 0:
        with open(POSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2)
            print(f"{b.GREEN}Итого: Посты сохранены{b.END} в {b.BLUE}{POSTS_FILE}{b.END}\n")
    else:
        print(f"Посты {b.RED}не сохранены{b.END} в {b.BLUE}{POSTS_FILE}{b.END} так как {b.RED}не были найдены{b.END}.")

    # Собираем комментарии ко всем постам
    all_comments = get_wall_comments(all_posts, vk)

    if len(all_comments) > 0:
        with open(WALL_COMMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_comments, f, ensure_ascii=False, indent=2)
            print(f"{b.GREEN}Итого: Комментарии к постам на стене сохранены{b.END} в {b.BLUE}{WALL_COMMENTS_FILE}{b.END}\n")
    else:
        print(f"Комментарии {b.RED}не сохранены{b.END} в {b.BLUE}{WALL_COMMENTS_FILE}{b.END} так как {b.RED}не были найдены{b.END}.")

    # Собираем пользователей оставивших лайк на пост на стене группы
    all_users_liked_wall_post = get_wall_likes(all_posts, vk)

    if len(all_users_liked_wall_post) > 0:
        with open(WALL_LIKES_FILE, "w", encoding="utf-8") as f:
            json.dump(all_users_liked_wall_post, f, ensure_ascii=False, indent=2)
            print(f"{b.GREEN}Итого: Лайки постов на стене сохранены{b.END} в {b.BLUE}{WALL_LIKES_FILE}{b.END}")
    else:
        print(f"Лайки пользователей {b.RED}не сохранены{b.END} в {b.BLUE}{WALL_LIKES_FILE}{b.END} так как {b.RED}не были найдены{b.END}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Выгрузить посты и комментарии из групп VK за последние дни")
    parser.add_argument("--token", "-t", help="VK access token (или через VK_TOKEN env)", default=os.getenv("VK_TOKEN"))
    parser.add_argument("--days", "-d", type=int, help="Количество дней для сбора постов", default=2)
    parser.add_argument("--in", "-in", dest="infile", help="Файл с группами", default=GROUPS_SEARCH_ACTUAL_FILE)
    args = parser.parse_args()
    token = args.token
    days = args.days
    infile = args.infile
    main_get_leads_from_wall(token, infile, days)
