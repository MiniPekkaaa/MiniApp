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
        return str(user_id) == str(admin_id)
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

        # Сначала проверяем, является ли пользователь администратором
        if check_admin_access(user_id):
            # Если админ, сразу перенаправляем в админ-панель
            # Проверка регистрации для админа здесь не нужна
            return redirect(f'/admin_panel?user_id={user_id}')

        # Если не админ, тогда проверяем регистрацию
        if not check_user_registration(user_id):
            return render_template('unauthorized.html')

        # Если зарегистрирован и не админ, показываем главное меню
        return render_template('main_menu.html', user_id=user_id)
    
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/admin_panel')
def admin_panel():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return redirect('/')

        # Для доступа в админ-панель проверяем ТОЛЬКО права администратора
        if not check_admin_access(user_id):
            # Если не админ, перенаправляем на главную (или страницу ошибки)
            return redirect('/')

        return render_template('admin_panel.html', user_id=user_id)
    except Exception as e:
        logger.error(f"Error in admin_panel route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/api/get-coefficient')
def get_coefficient():
    try:
        coefficient = redis_client.hget('beer:setting', 'coefficient')
        last_date = redis_client.hget('beer:setting', 'coefficient_last_Date')
        logger.debug(f"API: get-coefficient - Fetched from Redis: coefficient='{coefficient}', last_date='{last_date}'")
        return jsonify({
            "success": True,
            "coefficient": coefficient if coefficient is not None else "1.0",
            "last_date": last_date if last_date is not None else ""
        })
    except Exception as e:
        logger.error(f"Error in /api/get-coefficient: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/update-coefficient', methods=['POST'])
def update_coefficient():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No data provided"})

        user_id = data.get('user_id')
        new_coefficient = data.get('coefficient')

        if not user_id or not new_coefficient:
            return jsonify({"success": False, "error": "Missing required parameters"})

        # Проверяем, имеет ли пользователь права администратора
        if not check_admin_access(user_id):
            logger.warning(f"Unauthorized coefficient update attempt by user {user_id}")
            return jsonify({"success": False, "error": "Unauthorized access"}), 403

        # Преобразуем в число и проверяем допустимость значения
        try:
            coefficient_float = float(new_coefficient)
            if coefficient_float < 0.75 or coefficient_float > 1.25:
                return jsonify({
                    "success": False,
                    "error": "Coefficient must be between 0.75 and 1.25"
                })
        except ValueError:
            return jsonify({"success": False, "error": "Invalid coefficient value"})

        # Текущая дата и время для записи в Redis
        moscow_tz = pytz.timezone('Europe/Moscow')
        current_time = datetime.now(moscow_tz).strftime('%d.%m.%Y %H:%M')

        # Обновляем данные в Redis
        redis_client.hset('beer:setting', 'coefficient', str(coefficient_float))
        redis_client.hset('beer:setting', 'coefficient_last_Date', current_time)

        logger.info(f"Coefficient updated to {coefficient_float} by admin {user_id}")

        return jsonify({
            "success": True,
            "coefficient": str(coefficient_float),
            "last_date": current_time
        })
    except Exception as e:
        logger.error(f"Error updating coefficient: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500