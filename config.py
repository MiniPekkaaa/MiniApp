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
API_BASE_URL = "https://proxy.3r.agency/api/pridebeer"
API_ENDPOINTS = {
    "calculate_checkout": "/calculate_checkout",
    "order_history": "/order_history/",
    "order_status": "/order_status/",
    "new_order": "/order_create"
}
API_USERNAME = "int2"
API_PASSWORD = "pcKnE8GqXn"

# Конфигурация Supabase
SUPABASE_URL = "https://lirlyqxkhoxkerpxsbwy.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxpcmx5cXhraG94a2VycHhzYnd5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEwMjg4NjEsImV4cCI6MjA2NjYwNDg2MX0.Coh9ssTudttft8RdKG14kL3nSpc2sndN7zzTGL79m0Y"
SUPABASE_TABLE_PRIDE_BEER_TARA = "pride_beer_tara"

# Значения по умолчанию
#DEFAULT_ORGANIZATION_ID = "16d7a1a8-a651-11ef-895a-005056c00008"
#DEFAULT_LEGAL_ENTITY = "2724132975" 