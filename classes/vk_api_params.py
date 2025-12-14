class VKParams:
    """Класс с параметрами VK API.
    Описание:

    - объявляет основные константы.
    """
    API_SLEEP = 0.34
    API_VERSION = "5.199"
    API_SCOPES = "wall,groups,offline,photos"
    OAUTH_URI = "https://oauth.vk.com"
    CLIENT_ID = "5446787"  # ID приложения ВКонтакте Поиска лидов
    URI = "https://vk.com"

API_SLEEP = VKParams.API_SLEEP  # пауза между запросами
API_VERSION = VKParams.API_VERSION  # версия API ВКонтакте
API_SCOPES = VKParams.API_SCOPES  # права доступа
OAUTH_URI = VKParams.OAUTH_URI  # URI для авторизации
CLIENT_ID = VKParams.CLIENT_ID  # ID приложения ВКонтакте
URI = VKParams.URI  # базовый URI ВКонтакте
