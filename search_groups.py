"""
search_groups.py

Модуль для поиска групп VK по фразе.

Содержит:
- Функции для поиска групп, загрузки и сохранения результатов в файл.

Автор: sergiomarotco, https://github.com/sergiomarotco/vk_lead_searcher
Дата: 2025-01-10
"""
import argparse
import datetime
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
from vk_api import VkApiError
import vk_api
from classes import vk_api_params as vk_p, bcolors as b, file_params as file_p


API_SLEEP = vk_p.API_SLEEP * 2  # пауза между запросами, х2 на всякий случай
BATCH_SIZE = 10  # сколько групп за один запрос
GROUPS_SEARCH_FILE = file_p.GROUPS_SEARCH_FILE

def search_groups(vk, search_query: str, group_limit: int) -> List[Dict[str, Any]]:
    """
    Выполнить поиск групп по фразе
    :param vk: объект класса vk
    :param search_query: фраза для поиска групп
    :param group_limit: количество групп в результате поиска
    :return: группы
    """
    results_groups: List[Dict[str, Any]] = []
    offset = 0
    while len(results_groups) < group_limit:
        count = min(BATCH_SIZE, group_limit - len(results_groups))
        resp = vk.groups.search(q=search_query, count=count, offset=offset)
        items = resp.get("items", [])
        if not items:
            break
        results_groups.extend(items)
        if len(items) < count:
            break
        offset += len(items)
        time.sleep(API_SLEEP)
    return results_groups


def load_groups(path: str) -> Dict[str, Any]:
    """
    Прочитать группы из файла
    :param path: имя файла для чтения
    :return: группы ранее сохранённые в файл
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_groups(path: str, search_query: str, groups: List[Dict[str, Any]]) -> None:
    """
    Сохранить группы в файл
    :param path: имя файла для сохранения
    :param search_query: поисковая фраза использованная для поиска
    :param groups: группы
    """
    out_data = {"query": search_query, "found": len(groups), "groups": groups}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)


def get_group_id(group: Dict[str, Any]) -> int:
    """
    Получить id группы из данных группы
    :param group: объект группы
    :return: id группы
    """
    for key in ("id", "gid", "group_id"):
        if key in group:
            return int(group[key])
    raise KeyError(b.RED + "Не удалось определить id группы" + b.END)


def build_post_link(group_id: int, post_id: int) -> str:
    """
    Сформировать гиперссылку на пост группы
    :param group_id: id группы
    :param post_id: id поста
    :return: uri на пост
    """
    # ссылка в формате https://vk.com/wall-{owner_id}_{post_id}, owner_id для группы — отрицательный
    return f"{vk_p.URI}/wall-{group_id}_{post_id}"


def filter_recent_groups(vk, groups: List[Dict[str, Any]], months: int = 3) -> List[Dict[str, Any]]:
    """

    :param vk: объект класса vk
    :param groups: группы
    :param months: количество месяцев для фильтра
    :return:
    """
    cutoff = datetime.now() - timedelta(days=30 * months)
    kept: List[Dict[str, Any]] = []

    for g in groups:
        try:
            gid = get_group_id(g)
        except KeyError:
            continue  # пропустить группы без id
        owner_id = -abs(gid)
        try:
            resp = vk.wall.get(owner_id=owner_id, count=1)
        except VkApiError:
            time.sleep(API_SLEEP)  # при ошибке API — пропустить (или можно логировать)
            continue
        items = resp.get("items", [])
        if not items:
            time.sleep(API_SLEEP)  # нет постов — считаем старой/неактуальной и пропускаем
            continue

        post = items[0]
        post_date = datetime.fromtimestamp(post.get("date", 0))
        if post_date < cutoff:
            time.sleep(API_SLEEP)  # последний пост старше порога — пропускаем
            continue
        last_post_info = {  # группа актуальна — добавляем информацию по последнему посту и сохраняем
            "date": post_date.isoformat(),
            "text": post.get("text", ""),
            "link": build_post_link(gid, post.get("id", 0)),
        }
        g = dict(g)  # не менять оригинал
        g["last_post"] = last_post_info
        kept.append(g)

        time.sleep(API_SLEEP)
    return kept


def main_search_groups(
        access_token: str, my_group_id: str, my_group_short_name: str,
        search_query: str = "фотограф новосибирск",
        out_file: str = GROUPS_SEARCH_FILE, group_limit: int = 10) -> None:
    """
    Найти группы по фразе и сохранить в файл
    :param my_group_short_name: Короткое имя вашей группы в VK для исключения из анализа
    :param my_group_id: Id вашей группы в VK для исключения из анализа
    :param access_token: токен доступа VK
    :param search_query: поисковая фраза групп
    :param out_file: имя файла для сохранения
    :param group_limit: количество групп для поиска
    """
    if not access_token:
        raise SystemExit("Требуется access token: передайте через --token или переменную окружения VK_TOKEN")

    # Поиск групп по заданной фразе в `--query`
    try:
        vk_session = vk_api.VkApi(token=access_token)
        vk = vk_session.get_api()
        print(f"Поиск групп по фразе: {b.BLUE}{search_query}{b.END} (limit={group_limit})")
        groups = search_groups(vk, search_query, group_limit)
        for g in groups:  # исключаем свою группу
            if my_group_id or my_group_short_name:
                if g['id'] == int(my_group_id) or g['screen_name'] == my_group_short_name:  # Сверяем по id или короткому имени
                    if my_group_short_name:
                        print(f"Группа {b.YELLOW}{vk_p.URI}/{my_group_short_name}{b.END} {b.GREEN}исключена{b.END} из результатов поиска.")
                    elif my_group_id:
                        print(f"Группа {b.YELLOW}{vk_p.URI}/club{my_group_id}{b.END} {b.GREEN}исключена{b.END} из результатов поиска.")
                    groups.remove(g)
                    break

        out_data = {"query": search_query, "found": len(groups), "groups": groups}
        useless_params  = ["photo_50", "photo_100", "photo_200", "is_closed", "type", "is_admin", "is_member", "is_advertiser"]  # Параметры, которые удалим из выгрузки так как мешаются

        for g in out_data["groups"]:
            for key in useless_params:
                g.pop(key, None)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(out_data, f, ensure_ascii=False, indent=2)
        print(b.GREEN + f"Найдены и сохранены группы: {len(groups)}{b.END} шт. в {b.BLUE}{out_file}{b.END}" + b.END)
    except VkApiError as e:
        raise SystemExit(f"VK API error: {e}")
    except Exception as e:
        raise SystemExit(f"Ошибка: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Поиск групп VK по фразе")
    parser.add_argument("--token", "-t", help="VK access token (или через VK_TOKEN env)", default=os.getenv("VK_TOKEN"))
    parser.add_argument("--query", "-q", help="Поисковая фраза", default="фотограф новосибирск")
    parser.add_argument("--out", "-o", help="Файл для сохранения (json)", default=GROUPS_SEARCH_FILE)
    parser.add_argument("--limit", "-n", type=int, help="Максимальное число групп", default=50)
    parser.add_argument("--my_vk_group_id", help="Id вашей группы в VK для исключения из анализа", default="", type=str)
    parser.add_argument("--my_vk_group_short_name", help="Короткое имя вашей группы в VK для исключения из анализа", default="", type=str)
    args = parser.parse_args()
    token = args.token
    query = args.query
    out = args.out
    my_vk_group_id = args.my_vk_group_id
    my_vk_group_short_name = args.my_vk_group_short_name
    limit: int = args.limit
    main_search_groups(token, query, my_vk_group_id, my_vk_group_short_name, out, limit)
