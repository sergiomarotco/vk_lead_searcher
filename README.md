# VK lead searcher

# About

The program allows you to:
- find groups using a single search phrase, for example, `florist`, as if you were searching on the page [https://vk.com/search/communities?q=florist](https://vk.com/search/communities?q=florist)
- remove from the found groups those that haven't published a wall post for a specified number of months
- export to a file those who liked and commented on a wall post if the post was published no later than a specified number of days
- export to a file those who liked and commented on a photo if the photo was published no later than a specified number of days
- export to a separate file line-by-line list of leads

# Access Token

To use the program, you will need a VK access token. To obtain it, follow this link:
- follow the link 
- authorize
- approve access scopes:
  - `groups` - basic access to work with groups
  - `wall` - permission to read group walls
  - `photos` - permission to read group photos
  - `offline` - unlimited access token lifespan
- after completing the provision of access scopes, you will be redirected to a special page, in the address bar you need to copy the access token from the `access_token=` variable and use it as the `--token` parameter when running `main.py`

# Usage

```
usage: main.py [-h] [--token TOKEN]
               [--command {search,remove_old,inspect_wall,inspect_photos,report}]
               [--search SEARCH] [--days_wall DAYS_WALL]
               [--days_photos DAYS_PHOTOS] [--months MONTHS]
               [--groups_limit GROUPS_LIMIT] [--RUN_FULL RUN_FULL]
               [--report REPORT] [--my_vk_group_id MY_VK_GROUP_ID]
               [--my_vk_group_short_name MY_VK_GROUP_SHORT_NAME]

Поисковик лидов в VK

options:
  -h, --help            show this help message and exit
  --token TOKEN         VK access token (или через VK_TOKEN env)
  --command {search,remove_old,inspect_wall,inspect_photos,report}
                        Что необходимо выполнить
  --search SEARCH       Поисковый запрос для поиска групп
  --days_wall DAYS_WALL
                        Количество дней для анализа стен
  --days_photos DAYS_PHOTOS
                        Количество дней для анализа фотографий групп
  --months MONTHS       Количество месяцев при котором группу считать
                        неактивной
  --groups_limit GROUPS_LIMIT
                        Максимальное количество групп для поиска
  --RUN_FULL RUN_FULL   Запускает полный цикл программы
  --report REPORT       Генерирует отчет по собранным лидам
  --my_vk_group_id MY_VK_GROUP_ID
                        Id вашей группы в VK для исключения из анализа
  --my_vk_group_short_name MY_VK_GROUP_SHORT_NAME
                        Короткое имя вашей группы в VK для исключения из
                        анализа
```

