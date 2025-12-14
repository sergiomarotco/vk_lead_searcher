"""
filter_groups.py

Модуль удаления из групп тех, что не публиковали посты в течение заданного времени.

Содержит:
- функции для получения групп из файла
- функции для сохранения групп в файл

Автор: sergiomarotco, https://github.com/sergiomarotco/vk_lead_searcher
Дата: 2025-01-10
"""
import argparse
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
import vk_api
from vk_api.exceptions import VkApiError
from tqdm import tqdm
import classes.bcolors as b
import classes.vk_api_params as vk_api_params
import classes.file_params as file_params


API_SLEEP = vk_api_params.API_SLEEP  # пауза между запросами
GROUPS_SEARCH_FILE = file_params.GROUPS_SEARCH_FILE
GROUPS_SEARCH_ACTUAL_FILE = file_params.GROUPS_SEARCH_ACTUAL_FILE


def load_groups_from_file(path: str) -> Dict[str, Any]:
    """
    Загрузить группы из файла
    :param path: Путь к файлу
    :return: Группы
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_groups_to_file(path: str, query: str, groups: List[Dict[str, Any]]) -> None:
    """
    Сохранить группы в файл
    :param path: Путь к файлу
    :param query: Фраза для поиска групп
    :param groups: Сохраняемые группы
    """
    out_data = {"query": query, "found": len(groups), "groups": groups}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)


def get_group_id(group: Dict[str, Any]) -> int:
    """
    Получить id группы из данных группы
    :param group: Группа
    :return: id группы
    """
    for key in ("id", "gid", "group_id"):
        if key in group:
            return int(group[key])
    raise KeyError("Не удалось определить id группы")


def generate_post_link(group_id: int, post_id: int) -> str:
    """
    Сгенерировать ссылку на пост группы
    :param group_id: id группы
    :param post_id: id поста
    :return: Ссылка на пост
    """
    # ссылка в формате https://vk.com/wall-{owner_id}_{post_id},
    # owner_id для группы — отрицательный
    return f"{vk_api_params.URI}/wall-{group_id}_{post_id}"


def filter_recent_groups(vk, groups: List[Dict[str, Any]], months_max: int = 3) -> List[Dict[str, Any]]:
    """
    Удалить из списка группы последний пост которых старше заданного порога в месяцах
    :param vk: объект VK API
    :param groups: Фильтруемые группы
    :param months_max: Количество месяцев для порога
    :return: Группы с последним постом не старше порога
    """
    cutoff = datetime.now() - timedelta(days=30 * months_max)
    active_groups: List[Dict[str, Any]] = []  # Группы, которые прошли фильтр по дате последнего поста

    with tqdm(groups, desc="Обработка групп", unit="группа") as pbar:
        for g in pbar:
            try:
                gid = get_group_id(g)  # получить id группы
            except KeyError:  # пропустить группы без id
                continue
            owner_id = -abs(gid)  # owner_id для группы — отрицательный
            pbar.set_postfix({"id группы": b.YELLOW + g['name'] + b.END})

            try:
                resp = vk.wall.get(owner_id=owner_id, count=1)  # получить последний пост
            except VkApiError:  # при ошибке API — пропустить (или можно логировать)
                time.sleep(API_SLEEP)  #  пауза между запросами для защиты от блокировки
                continue
            items = resp.get("items", [])
            if not items:
                # нет постов — считаем старой/неактуальной и пропускаем
                time.sleep(API_SLEEP)
                continue

            post = items[0]  # последний пост
            post_date = datetime.fromtimestamp(post.get("date", 0))  # дата поста
            if post_date < cutoff:  # последний пост старше порога — пропускаем
                time.sleep(API_SLEEP)
                continue

            # группа актуальна — добавляем информацию по последнему посту и сохраняем
            last_post_info = {
                "date": post_date.isoformat(),
                "text": post.get("text", ""),
                "link": generate_post_link(gid, post.get("id", 0)),
            }
            g = dict(g)  # не менять оригинал
            g["last_post"] = last_post_info
            g["group_link"] = f"{vk_api_params.URI}/club{gid}"  # ссылка на группу для удобства открытия группы из JSON файла
            active_groups.append(g)
            time.sleep(API_SLEEP)  # пауза между запросами для защиты от блокировки
    return active_groups


def main_filter_groups(access_token: str, file: str = GROUPS_SEARCH_FILE, out_file: str = GROUPS_SEARCH_ACTUAL_FILE, months_max: int = 3) -> None:
    """
    Функция фильтрации групп по дате последнего поста
    :param access_token: VK access token
    :param file: Файл с исходным списком групп
    :param out_file: Файл для записи актуальных групп
    :param months_max: Порог в месяцах для старости постов
    :rtype: None
    """
    if not access_token:
        raise SystemExit("Требуется VK token через --token или переменную окружения VK_TOKEN")

    try:
        data = load_groups_from_file(file)
    except Exception as e:
        raise SystemExit(f"Не удалось загрузить {b.BLUE}{file}{b.END}: {b.RED}{e}{b.END}")

    groups = data.get("groups") if isinstance(data, dict) else data
    if not isinstance(groups, list):
        raise SystemExit(b.END + "Входной файл не содержит список групп в поле `groups`" + b.END)

    vk_session = vk_api.VkApi(token=access_token)
    vk = vk_session.get_api()

    actual = filter_recent_groups(vk, groups, months_max=months_max)
    query = data.get("query", "")
    save_groups_to_file(out_file, query, actual)
    print(f"\n{b.GREEN}Итог: сохранено {len(actual)} актуальных групп{b.END} в {b.BLUE}{out_file}{b.END}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Отфильтровать группы VK по дате последнего поста")
    parser.add_argument("token", "-t", help="VK access token")
    parser.add_argument("--in", dest="infile", default=GROUPS_SEARCH_FILE, help="Файл с исходным списком")
    parser.add_argument("--out", "-o", default=GROUPS_SEARCH_ACTUAL_FILE, help="Файл для записи актуальных групп")
    parser.add_argument("--months", type=int, default=3, help="Порог в месяцах для старости постов")
    args = parser.parse_args()
    token = args.token
    infile = args.infile
    out = args.out
    months = args.months
    main_filter_groups(token, infile, out, months)
