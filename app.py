from flask import Flask, render_template, jsonify, request, redirect
from flask_pymongo import PyMongo
import logging
from bson import json_util, ObjectId
import json
import redis
from datetime import datetime, timedelta
import pytz
import requests
import random

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация MongoDB
app.config["MONGO_URI"] = "mongodb://root:otlehjoq543680@46.101.121.75:27017/admin?authSource=admin&directConnection=true"
mongo = PyMongo(app)

# Конфигурация Redis
redis_client = redis.Redis(
    host='46.101.121.75',
    port=6379,
    password='otlehjoq',
    decode_responses=True
)

def check_user_registration(user_id):
    try:
        # Проверяем существование пользователя в Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        logger.debug(f"Redis data for user {user_id}: {user_data}")
        
        # Проверяем наличие данных, совпадение UserChatID и статус регистрации
        registration_complete = (
            bool(user_data) and 
            user_data.get('UserChatID') == str(user_id) and
            user_data.get('current_step') == 'complete'
        )
        
        if not registration_complete:
            logger.debug(f"Registration check failed for user {user_id}. Data: {user_data}")
            
        return registration_complete
    except Exception as e:
        logger.error(f"Error checking Redis: {str(e)}")
        return False

def check_admin_access(user_id):
    try:
        # Получаем значение Admin из Redis
        admin_id = redis_client.hget('beer:setting', 'Admin')
        logger.debug(f"Admin ID from Redis: {admin_id}, User ID: {user_id}")
        
        # Добавляем более подробные логи для отладки
        if admin_id is None:
            logger.error("Admin ID not found in Redis (beer:setting:Admin is None)")
            return False
            
        # Приводим оба значения к строковому типу и сравниваем
        is_admin = str(user_id) == str(admin_id)
        logger.debug(f"Is user {user_id} admin? {is_admin}")
        
        return is_admin
    except Exception as e:
        logger.error(f"Error checking admin access: {str(e)}")
        return False

@app.route('/check-auth')
def check_auth():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"authorized": False, "error": "No user ID provided"})
        
        is_registered = check_user_registration(user_id)
        return jsonify({"authorized": is_registered})
    except Exception as e:
        logger.error(f"Error in check-auth: {str(e)}")
        return jsonify({"authorized": False, "error": str(e)})

@app.route('/')
def index():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return render_template('unauthorized.html')

        # Проверяем, является ли пользователь администратором (без проверки регистрации)
        if check_admin_access(user_id):
            logger.info(f"User {user_id} identified as admin, redirecting to admin panel")
            return redirect(f'/admin_panel?user_id={user_id}')

        # Проверяем регистрацию обычного пользователя
        if not check_user_registration(user_id):
            return render_template('unauthorized.html')

        return render_template('main_menu.html', user_id=user_id)
    
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/admin_panel')
def admin_panel():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            logger.warning("Admin panel access attempt without user_id")
            return redirect('/')

        # Проверяем права администратора (без проверки регистрации)
        is_admin = check_admin_access(user_id)
        logger.info(f"Admin panel access: user_id={user_id}, is_admin={is_admin}")
        
        if not is_admin:
            logger.warning(f"Unauthorized admin panel access attempt by user {user_id}")
            return redirect('/')

        return render_template('admin_panel.html', user_id=user_id)
    except Exception as e:
        logger.error(f"Error in admin_panel route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500