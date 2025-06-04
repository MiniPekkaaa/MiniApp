#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Конфигурация MongoDB
MONGO_URI = "mongodb://root:otlehjoq543680@46.101.121.75:27017/admin?authSource=admin&directConnection=true"
MONGO_HOST = "46.101.121.75"
MONGO_PORT = 27017
MONGO_USER = "root"
MONGO_PASSWORD = "otlehjoq543680"
MONGO_DB = "admin"

# Конфигурация Redis
REDIS_HOST = "46.101.121.75"
REDIS_PORT = 6379
REDIS_PASSWORD = "otlehjoq"
REDIS_DECODE_RESPONSES = True

# Конфигурация 1C API
API_BASE_URL = "http://87.225.110.142:65531/uttest/hs/int"
API_ENDPOINTS = {
    "calculate_checkout": "/calculate_checkout",
    "order_history": "/istorzakaz/",
    "order_status": "/zakaz-status/",
    "new_order": "/novzakaz"
}
API_USERNAME = "int2"
API_PASSWORD = "pcKnE8GqXn"

# Значения по умолчанию
DEFAULT_ORGANIZATION_ID = "16d7a1a8-a651-11ef-895a-005056c00008"
DEFAULT_LEGAL_ENTITY = "2724132975" 