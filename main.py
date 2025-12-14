"""
main.py

Основная программа.

Содержит:
- Парсер аргументов командной строки.
- Запуск основных функций в зависимости от переданных аргументов.

Автор: sergiomarotco, https://github.com/sergiomarotco/vk_lead_searcher
Дата: 2025-01-10
"""
import argparse
import os
import sys
from classes import vk_api_params
from classes import file_params
import classes.bcolors as b
import generate_report
import get_leads_from_wall
import get_leads_from_photos
import filter_groups
import search_groups


COMMANDS: list = ["search", "remove_old", "inspect_wall", "inspect_photos", "report"]
GROUPS_SEARCH_FILE: str = file_params.GROUPS_SEARCH_FILE
OAUTH_URI: str = vk_api_params.OAUTH_URI
API_SCOPES: str = vk_api_params.API_SCOPES
API_SLEEP: float = vk_api_params.API_SLEEP
CLIENT_ID: str = vk_api_params.CLIENT_ID
LINK: str = f"{OAUTH_URI}/authorize?client_id={CLIENT_ID}&display=page&redirect_uri={OAUTH_URI}/blank.html&scope={API_SCOPES}&response_type=token&v={API_SLEEP}"
MY_VK_GROUP_ID: str = ""
MY_VK_GROUP_SHORT_NAME: str = ""

def main_py(args_):
    """
    Основная функция программы
    """
    if args_.RUN_FULL:
        print(f"{b.BLUE}Запущен полный цикл программы.{b.END}")
        print(f"\n{b.BLUE}Шаг 1: Поиск групп по запросу{b.END} {b.YELLOW}{args_.search}{b.END} и не более {b.YELLOW}{args_.groups_limit}{b.END} штук.")
        search_groups.main_search_groups(args_.token, search_query=args_.search, group_limit=args_.groups_limit, my_group_id=MY_VK_GROUP_ID, my_group_short_name=MY_VK_GROUP_SHORT_NAME)
        print(f"\n{b.BLUE}Шаг 2: Удаление групп не публиковавших посты более{b.END} {b.YELLOW}{args_.months}{b.END} мес.")
        filter_groups.main_filter_groups(args_.token, months_max=args_.months)
        print(f"\n{b.BLUE}Шаг 3: Сбор лидов со стен групп за последние{b.END} {b.YELLOW}{args_.days_wall}{b.END} дней.")
        get_leads_from_wall.main_get_leads_from_wall(args_.token, days_wall_max=args_.days_wall)
        print(f"\n{b.BLUE}Шаг 4: Сбор лидов с фотографий групп за последние{b.END} {b.YELLOW}{args_.days_photos}{b.END} дней.")
        get_leads_from_photos.main_get_leads_from_photos(args_.token, days=args_.days_photos)
        print(f"\n{b.BLUE}Шаг 5: Генерация отчета по собранным лидам.{b.END}")
        generate_report.main_generate_report()
    else:
        print(f"{b.BLUE}Передана команда{b.END}: {args_.command}")
        if args_.command == "report":
            print(f"{b.BLUE}Формирование отчета.")
            generate_report.main_generate_report()
        elif args_.command == "search":
            print(f"{b.BLUE}Запущен поиск групп по запросу{b.END} {b.YELLOW}{args_.search}{b.END} и не более {b.YELLOW}{args_.groups_limit}{b.END} штук.")
            search_groups.main_search_groups(args_.token, search_query=args_.search, group_limit=args_.groups_limit, my_group_id=MY_VK_GROUP_ID, my_group_short_name=MY_VK_GROUP_SHORT_NAME)
        elif args_.command == "remove_old":
            print(f"{b.BLUE}Запущено удаление групп не публиковавших посты более{b.END} {b.YELLOW}{args_.months}{b.END} мес.")
            filter_groups.main_filter_groups(args_.token, months_max=args_.months)
        elif args_.command == "inspect_wall":
            print(f"{b.BLUE}Запущен сбор лидов со стен групп за {b.END} {b.YELLOW}{args_.days_wall}{b.END} дней.")
            get_leads_from_wall.main_get_leads_from_wall(access_token=args_.token, days_wall_max=args_.days_wall)
        elif args_.command == "inspect_photos":
            print(f"{b.BLUE}Запущен сбор лидов с фотографий групп за {b.END} {b.YELLOW}{args_.days_photos}{b.END} дней.")
            get_leads_from_photos.main_get_leads_from_photos(args_.token, days=args_.days_photos)
        else:
            print(f"{b.RED}Неизвестная команда: {args_.command}{b.END}")
            print(f"{b.RED}Допустимые команды запуска (переменная {b.END}{b.YELLOW}--command{b.END}{b.BLUE}):{b.END}")
            print(COMMANDS)
            sys.exit(1)


def func(**kwargs):
    if "my_vk_group_id" in kwargs:
        print("Аргумент x передан:", kwargs["x"])
    else:
        print("Аргумента x нет")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Поисковик лидов в VK")
    parser.add_argument("--token", help="VK access token (или через VK_TOKEN env)", default=os.getenv("VK_TOKEN"), type=str)
    parser.add_argument("--command", help="Что необходимо выполнить", default="report", type=str, choices=COMMANDS)
    parser.add_argument("--search", help="Поисковый запрос для поиска групп", default="фотограф новосибирск", type=str)
    parser.add_argument("--days_wall", help="Количество дней для анализа стен", default=15, type=int)
    parser.add_argument("--days_photos", help="Количество дней для анализа фотографий групп ", default=15, type=int)
    parser.add_argument("--months", help="Количество месяцев при котором группу считать неактивной", default=3, type=int)
    parser.add_argument("--groups_limit", help="Максимальное количество групп для поиска", default=20, type=int)
    parser.add_argument("--RUN_FULL", help="Запускает полный цикл программы", default=False, type=bool)
    parser.add_argument("--report", help="Генерирует отчет по собранным лидам", default=False, type=bool)
    parser.add_argument("--my_vk_group_id", help="Id вашей группы в VK для исключения из анализа", type=str)
    parser.add_argument("--my_vk_group_short_name", help="Короткое имя вашей группы в VK для исключения из анализа", type=str)
    args = parser.parse_args()
    if hasattr(args, "my_vk_group_id"):
        MY_VK_GROUP_ID = args.my_vk_group_id
    if hasattr(args, "my_vk_group_short_name"):
        MY_VK_GROUP_SHORT_NAME = args.my_vk_group_short_name
    print(f"{b.GREEN}Информация о программе:{b.END}")
    parser.print_help()
    print(f"{b.BLUE}Как получить токен (`--token`)?{b.END}: перейти по ссылке {b.YELLOW}{LINK}{b.END}")
    print(f"авторизоваться, скопировать токен из адресной строки браузера после {b.YELLOW}access_token={b.END}")
    print("Он очень длинный")
    print(f"{b.RED}Токен конфиденциален, не храните его в открытом где-либо!!!{b.END}")
    print("https://github.com/sergiomarotco/vk_lead_searcher")
    print(f"{b.GREEN}------------------------------------------------{b.END}")
    main_py(args)
