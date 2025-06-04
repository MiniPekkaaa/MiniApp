"""
Файл конфигурации проекта MiniApp
Содержит все настройки подключений и API-адреса
"""

# Настройки MongoDB
MONGO_URI = "mongodb://root:otlehjoq543680@46.101.121.75:27017/admin?authSource=admin&directConnection=true"
MONGO_DB_NAME = "Pivo"  # Название базы данных

# Настройки Redis
REDIS_HOST = "46.101.121.75"
REDIS_PORT = 6379
REDIS_PASSWORD = "otlehjoq"
REDIS_DECODE_RESPONSES = True

# Настройки API 1C
# Базовый URL API 1C
API_1C_BASE_URL = "http://87.225.110.142:65531/uttest/hs/int"
# Аутентификация для API 1C
API_1C_AUTH = ("int2", "pcKnE8GqXn")
# Тайм-аут для запросов к API 1C (в секундах)
API_1C_TIMEOUT = 10

# Настройки API для истории заказов
API_1C_ORDER_HISTORY_ENDPOINT = "/istorzakaz/{org_id}"

# Настройки API для статусов заказов
API_1C_ORDER_STATUS_ENDPOINT = "/statuszakaz/{uid}"

# Параметры по умолчанию
DEFAULT_ORGANIZATION_ID = "16d7a1a8-a651-11ef-895a-005056c00008"

# Настройки для тары
STANDARD_LEGAL_ENTITIES = ["2724132975", "2724163243"]

# URL для веб-хука n8n
N8N_WEBHOOK_URL = "https://n8n.stage.3r.agency/webhook/e2d92758-49a8-4d07-a28c-acf92ff8affa"

# URL для регистрации в Telegram-боте
TELEGRAM_BOT_REGISTER_URL = "https://t.me/beer_otto_bot?start=register" 