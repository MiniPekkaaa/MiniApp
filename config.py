# Database configurations
MONGODB_CONFIG = {
    'host': '46.101.121.75',
    'port': 27017,
    'username': 'root',
    'password': 'otlehjoq543680',
    'auth_source': 'admin'
}

REDIS_CONFIG = {
    'host': '46.101.121.75',
    'port': 6379,
    'password': 'otlehjoq543680',
    'db': 0
}

# MongoDB connection string
MONGODB_URI = f"mongodb://{MONGODB_CONFIG['username']}:{MONGODB_CONFIG['password']}@{MONGODB_CONFIG['host']}:{MONGODB_CONFIG['port']}/{MONGODB_CONFIG['auth_source']}" 