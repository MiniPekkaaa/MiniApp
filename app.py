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
import config
import platform
import time

# Глобальная переменная для отслеживания времени запуска приложения
APP_START_TIME = time.time()

# Функция для форматирования времени работы
def format_uptime(seconds):
    """Форматирует время работы в человекочитаемый формат."""
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{int(days)}д {int(hours)}ч {int(minutes)}м {int(seconds)}с"
    elif hours > 0:
        return f"{int(hours)}ч {int(minutes)}м {int(seconds)}с"
    elif minutes > 0:
        return f"{int(minutes)}м {int(seconds)}с"
    else:
        return f"{int(seconds)}с"

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация MongoDB
app.config["MONGO_URI"] = config.MONGO_URI
mongo = PyMongo(app)

# Конфигурация Redis
redis_client = redis.Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    password=config.REDIS_PASSWORD,
    decode_responses=config.REDIS_DECODE_RESPONSES
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
            return redirect(f'/admin_panel?user_id={user_id}')

        # Если не админ, тогда проверяем регистрацию
        if not check_user_registration(user_id):
            return render_template('unauthorized.html')

        return render_template('main_menu.html', user_id=user_id)
    
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/main_menu')
def main_menu():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return redirect('/')
        return render_template('main_menu.html', user_id=user_id)
    except Exception as e:
        logger.error(f"Error in main_menu route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/order_type')
def order_type():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return redirect('/')
        return render_template('order_type.html', user_id=user_id)
    except Exception as e:
        logger.error(f"Error in order_type route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/products')
def products():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return redirect('/')
        
        logger.debug("Attempting to connect to MongoDB...")
        products = list(mongo.cx.Pivo.catalog.find())
        logger.debug(f"Found {len(products)} products")
        
        if len(products) > 0:
            logger.debug(f"Sample product: {products[0]}")

        # Форматируем данные для шаблона
        formatted_products = []
        for product in products:
            formatted_product = {
                'id': product.get('id', ''),
                '_id': str(product.get('_id', '')),
                'name': product.get('name', ''),
                'fullName': product.get('fullName', ''),
                'volume': float(product.get('volume', 0) or 0),
                'legalEntity': int(product.get('legalEntity', 1) or 1),
                'TARA': bool(product.get('TARA', False))
            }
            formatted_products.append(formatted_product)
            logger.debug(f"Formatted product: {formatted_product}")

        logger.debug(f"Total formatted products: {len(formatted_products)}")
        return render_template('index.html', products=formatted_products, user_id=user_id)
    
    except Exception as e:
        logger.error(f"Error in products route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/cart')
def cart():
    user_id = request.args.get('user_id')
    if not user_id or not check_user_registration(user_id):
        return redirect('/')
    return render_template('cart.html', user_id=user_id)

@app.route('/add_product')
def add_product():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return redirect('/')

        products = list(mongo.cx.Pivo.catalog.find())
        
        # Форматируем данные для шаблона
        formatted_products = []
        for product in products:
            formatted_product = {
                'id': product.get('id', ''),
                '_id': str(product.get('_id', '')),
                'name': product.get('name', ''),
                'fullName': product.get('fullName', ''),
                'volume': float(product.get('volume', 0) or 0),
                'legalEntity': int(product.get('legalEntity', 1) or 1),
                'TARA': bool(product.get('TARA', False))
            }
            formatted_products.append(formatted_product)

        return render_template('add_product.html', products=formatted_products, user_id=user_id)
    
    except Exception as e:
        logger.error(f"Error in add_product route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/api/products')
def get_products():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return jsonify({"error": "Unauthorized"}), 401

        products = list(mongo.cx.Pivo.catalog.find())
        formatted_products = []
        for product in products:
            formatted_product = {
                'id': product.get('id', ''),
                '_id': str(product.get('_id', '')),
                'name': product.get('name', ''),
                'fullName': product.get('fullName', ''),
                'volume': float(product.get('volume', 0) or 0),
                'legalEntity': int(product.get('legalEntity', 1) or 1),
                'TARA': bool(product.get('TARA', False))
            }
            formatted_products.append(formatted_product)
        
        return jsonify(formatted_products)
    except Exception as e:
        logger.error(f"Error in get_products route: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/create-order', methods=['POST'])
def create_order():
    try:
        logger.debug("Получен запрос на создание заказа")
        data = request.json
        user_id = data.get('userId')
        
        if not user_id or not check_user_registration(user_id):
            return jsonify({"error": "Unauthorized"}), 401

        logger.debug(f"Данные заказа: {data}")

        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        
        # Формируем позиции заказа
        positions = {}
        for index, item in enumerate(data.get('items', []), 1):
            position_key = f"Position_{index}"
            beer_id = item.get('id')
            legal_entity = item.get('legalEntity')
            quantity = item.get('quantity')
            price = item.get('price')
            
            positions[position_key] = {
                'Beer_ID': int(beer_id) if beer_id is not None else 0,
                'Beer_Name': item.get('name', ''),
                'Legal_Entity': int(legal_entity) if legal_entity is not None else 1,
                'Beer_Count': int(quantity) if quantity is not None else 0,
                'Price': float(price) if price is not None else 0
            }

        # Создаем заказ
        timezone = pytz.timezone('Asia/Vladivostok')  # UTC+10
        current_time = datetime.now(timezone)
        order_data = {
            'status': "Новый",
            'date': current_time.strftime("%d.%m.%y %H:%M"),
            'userid': str(user_id),
            'username': user_data.get('organization', 'ООО Пивной мир'),
            'org_ID': user_data.get('org_ID'),
            'Positions': positions,
            'nextOrderDate': data.get('nextOrderDate')  # Добавляем дату следующего заказа
        }

        logger.debug(f"Подготовленный заказ: {order_data}")
        
        result = mongo.cx.Pivo.Orders.insert_one(order_data)
        logger.debug(f"Заказ создан, ID: {result.inserted_id}")

        return jsonify({"success": True, "orderId": str(result.inserted_id)})
    except Exception as e:
        logger.error(f"Ошибка при создании заказа: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/order_menu')
def order_menu():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return redirect('/')
            
        products = list(mongo.cx.Pivo.catalog.find())
        formatted_products = []
        for product in products:
            formatted_product = {
                'id': product.get('id', ''),
                '_id': str(product.get('_id', '')),
                'name': product.get('name', ''),
                'fullName': product.get('fullName', ''),
                'volume': float(product.get('volume', 0) or 0),
                'legalEntity': int(product.get('legalEntity', 1) or 1),
                'TARA': bool(product.get('TARA', False))
            }
            formatted_products.append(formatted_product)
            
        return render_template('index.html', products=formatted_products, user_id=user_id)
    except Exception as e:
        logger.error(f"Error in order_menu route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/api/get-last-orders')
def get_last_orders():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return jsonify({"error": "Unauthorized"}), 401

        # Получаем данные пользователя из Redis для получения org_ID
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        org_id = user_data.get('org_ID')
        
        if not org_id:
            return jsonify({"error": "Organization ID not found"}), 400

        logger.debug(f"Получение последних заказов для организации {org_id}")

        # Получаем последние 10 заказов организации, отсортированные по дате создания
        orders = list(mongo.cx.Pivo.Orders.find(
            {"org_ID": org_id},
            {"Positions": 1, "_id": 1, "date": 1, "createdAt": 1, "ordersUID": 1, "status": 1}
        ).sort([("createdAt", -1), ("date", -1)]).limit(10))
        
        logger.debug(f"Найдено {len(orders)} последних заказов")

        # Собираем все ID и UID заказов для проверки статусов
        order_requests = []
        for order in orders:
            order_id = str(order.get('_id', ''))
            if order_id:
                order_requests.append({"mongo_id": order_id})
        
        # Если нет заказов для проверки статусов, возвращаем пустой результат
        if not order_requests:
            logger.debug("Нет заказов для проверки статусов")
            return jsonify({"success": True, "positions": [], "org_ID": org_id})

        # Запрашиваем статусы всех заказов
        logger.debug(f"Запрашиваем статусы для {len(order_requests)} заказов")
        try:
            # Отправляем batch-запрос для получения статусов
            response = requests.post(
                f'http://{request.host}/api/get-batch-order-statuses',
                json={"orders": order_requests},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Ошибка при получении статусов: {response.status_code}, {response.text}")
                # Продолжаем выполнение с имеющимися статусами
            else:
                status_data = response.json()
                if status_data.get('success') and status_data.get('statuses'):
                    # Обновляем статусы заказов
                    statuses = status_data['statuses']
                    for order in orders:
                        order_id = str(order.get('_id', ''))
                        if order_id in statuses:
                            # Обновляем статус в объекте заказа
                            order['status'] = statuses[order_id]['status']
                            logger.debug(f"Обновлен статус заказа {order_id}: {order['status']}")
        except Exception as e:
            logger.error(f"Ошибка при получении batch-статусов: {str(e)}")
            # Продолжаем выполнение с имеющимися статусами
        
        # Фильтруем только заказы со статусом "Отгружен" и подобными
        shipped_orders = []
        for order in orders:
            status = str(order.get('status', '')).lower()
            # Расширяем список возможных вариантов статуса "отгружен"
            if (status == "отгружен" or status == "отгружено" or 
                "отгруж" in status or "выполнен" in status or 
                "доставлен" in status or "выдан" in status):
                logger.debug(f"Добавляем отгруженный заказ {order.get('_id')} в список, статус: {status}")
                shipped_orders.append(order)
            else:
                logger.debug(f"Пропускаем заказ {order.get('_id')} со статусом: {status}")
        
        # Берем только 5 последних отгруженных заказов
        shipped_orders = shipped_orders[:5]
        logger.debug(f"Отфильтровано {len(shipped_orders)} отгруженных заказов")

        # Если не нашли отгруженных заказов, возвращаем пустой результат
        if not shipped_orders:
            logger.debug("Не найдено отгруженных заказов")
            return jsonify({"success": True, "positions": [], "org_ID": org_id})

        # Создаем словарь для отслеживания позиций из заказов
        seen_positions = {}
        result = []

        # Обрабатываем каждый отгруженный заказ
        for order_index, order in enumerate(shipped_orders):
            positions = order.get('Positions', {})
            logger.debug(f"Заказ #{order_index+1} содержит {len(positions)} позиций")
            
            # Для каждой позиции в текущем заказе
            for position_key, position in positions.items():
                beer_id = position.get('Beer_ID')
                legal_entity = position.get('Legal_Entity')
                beer_name = position.get('Beer_Name', '')
                
                if beer_id is None or legal_entity is None:
                    logger.warning(f"Пропускаем позицию с отсутствующими данными: Beer_ID={beer_id}, Legal_Entity={legal_entity}")
                    continue
                
                # Создаем уникальный ключ для этой позиции
                unique_key = f"{beer_id}_{legal_entity}"
                
                # Если эта позиция не была добавлена ранее, добавляем ее в результат
                if unique_key not in seen_positions:
                    seen_positions[unique_key] = True
                    
                    # Преобразуем Beer_ID в строку, если нужно
                    beer_id_str = str(beer_id) if beer_id is not None else ''
                    
                    # Получаем Beer_Count, обрабатывая случай None
                    beer_count = position.get('Beer_Count')
                    beer_count_int = int(beer_count) if beer_count is not None else 0
                    
                    result_position = {
                        'Beer_ID': beer_id_str,
                        'Beer_Name': beer_name,
                        'Legal_Entity': legal_entity,
                        'Beer_Count': beer_count_int
                    }
                    
                    result.append(result_position)
                    logger.debug(f"Добавлена позиция в результат: {result_position}")
        
        logger.debug(f"Собрано {len(result)} уникальных позиций из отгруженных заказов")
        
        # Если не нашли ни одной позиции, пробуем поискать в каталоге
        if not result:
            logger.debug("Не найдено ни одной позиции в отгруженных заказах, ищем в каталоге")
            
            # Получаем популярные позиции из каталога (до 10 позиций)
            catalog_items = list(mongo.cx.Pivo.catalog.find(
                {"TARA": {"$ne": True}},  # Исключаем тару
                {"id": 1, "name": 1, "legalEntity": 1}
            ).limit(10))
            
            for item in catalog_items:
                beer_id = item.get('id')
                beer_name = item.get('name', '')
                legal_entity = item.get('legalEntity', 1)
                
                if beer_id:
                    result.append({
                        'Beer_ID': str(beer_id),
                        'Beer_Name': beer_name,
                        'Legal_Entity': legal_entity,
                        'Beer_Count': 0  # По умолчанию 0
                    })
                    logger.debug(f"Добавлена позиция из каталога: ID={beer_id}, Name={beer_name}")
        
        # Добавляем org_ID в ответ для n8n
        response_data = {
            "success": True,
            "positions": result,
            "org_ID": org_id
        }
        
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Ошибка при получении последних заказов: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/my_orders')
def my_orders():
    user_id = request.args.get('user_id')
    if not user_id:
        return 'User ID is required', 400
    return render_template('my_orders.html', user_id=user_id)

@app.route('/api/get-orders')
def get_orders():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID is required'}), 400

    try:
        start_time = datetime.now()
        logger.debug(f'Начало получения заказов для пользователя {user_id}: {start_time.strftime("%H:%M:%S.%f")[:-3]}')
        
        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        if not user_data:
            return jsonify({'success': False, 'error': 'User not found in Redis'}), 404

        redis_time = datetime.now()
        logger.debug(f'Получены данные из Redis: {(redis_time - start_time).total_seconds():.3f} сек')

        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({'success': False, 'error': 'Organization ID not found'}), 404

        # Получаем 5 последних заказов из MongoDB по org_ID, сортированных по дате
        # Указываем только нужные поля для ускорения запроса
        query_time_start = datetime.now()
        logger.debug(f'Начало запроса к MongoDB: {(query_time_start - start_time).total_seconds():.3f} сек')
        
        # Убираем любое кеширование, всегда запрашиваем актуальные данные
        orders = list(mongo.cx.Pivo.Orders.find(
            {'org_ID': org_id},
            {
                'date': 1, 
                'status': 1, 
                'Positions': 1, 
                'ordersUID': 1, 
                '_id': 1,
                'createdAt': 1  # Добавляем поле createdAt для более точной сортировки
            }
        ).sort([('createdAt', -1), ('date', -1)]).limit(10))  # Увеличиваем лимит до 10 и добавляем двойную сортировку
        
        query_time_end = datetime.now()
        logger.debug(f'Запрос к MongoDB выполнен за: {(query_time_end - query_time_start).total_seconds():.3f} сек, получено {len(orders)} заказов')
        
        # Логируем даты для отладки
        if orders:
            logger.debug("Даты заказов из MongoDB:")
            for idx, order in enumerate(orders):
                created_at = order.get('createdAt')
                date_str = order.get('date', '')
                logger.debug(f"  Заказ {idx+1}: _id={order.get('_id')}, createdAt={created_at}, date={date_str}")
        
        # Преобразуем заказы в нужный формат
        formatted_orders = []
        for order in orders:
            # Преобразуем позиции из словаря в список
            positions = []
            
            for pos_key, pos_data in order.get('Positions', {}).items():
                beer_id = str(pos_data.get('Beer_ID', ''))
                quantity = pos_data.get('Beer_Count', 0) or 0
                price = pos_data.get('Price', 0) or 0

                positions.append({
                    'name': pos_data.get('Beer_Name', ''),
                    'quantity': quantity,
                    'id': beer_id,
                    'legal_entity': pos_data.get('Legal_Entity', 1) or 1,
                    'price': price
                })

            # Проверяем наличие поля ordersUID и добавляем его, если оно есть
            orders_uid = None
            if 'ordersUID' in order:
                orders_uid = order.get('ordersUID')

            # Преобразуем ObjectId в строку
            order_id = str(order.get('_id'))
            
            # Используем оригинальную дату из MongoDB, без преобразований
            created_at = order.get('date', '')
            if not created_at and 'createdAt' in order and order['createdAt']:
                try:
                    # Преобразуем datetime в строку в нужном формате
                    created_at = order['createdAt'].strftime("%d.%m.%y %H:%M")
                except:
                    pass

            formatted_order = {
                'created_at': created_at,
                'status': order.get('status', 'in work'),
                'positions': positions,
                'ordersUID': orders_uid,
                'order_ID': order_id
            }
            formatted_orders.append(formatted_order)

        format_time_end = datetime.now()
        logger.debug(f'Форматирование заказов выполнено за: {(format_time_end - query_time_end).total_seconds():.3f} сек')
        
        end_time = datetime.now()
        logger.debug(f'Общее время выполнения get_orders: {(end_time - start_time).total_seconds():.3f} сек')

        return jsonify({
            'success': True,
            'orders': formatted_orders
        })
    except Exception as e:
        logger.error(f'Error getting orders: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to get orders'
        }), 500

@app.route('/api/get-order')
def get_order():
    order_id = request.args.get('order_id')
    if not order_id:
        return jsonify({'success': False, 'error': 'Order ID is required'}), 400

    try:
        # Получаем заказ из MongoDB по _id
        order = mongo.cx.Pivo.Orders.find_one({'_id': ObjectId(order_id)})
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        # Преобразуем позиции из словаря в список
        positions = []
        
        for pos_key, pos_data in order.get('Positions', {}).items():
            beer_id = str(pos_data.get('Beer_ID', ''))
            quantity = pos_data.get('Beer_Count', 0) or 0
            price = pos_data.get('Price', 0) or 0

            positions.append({
                'name': pos_data.get('Beer_Name', ''),
                'quantity': quantity,
                'id': beer_id,
                'legal_entity': pos_data.get('Legal_Entity', 1) or 1,
                'price': price
            })
            
        # Форматируем дату
        date_str = order.get('date', '')
        try:
            # Парсим дату
            date_parts = date_str.split(' ')
            if len(date_parts) == 2:
                date_part = date_parts[0].split('.')
                time_part = date_parts[1].split(':')
                if len(date_part) == 3 and len(time_part) == 2:
                    # Преобразуем в полный формат даты
                    year = f"20{date_part[2]}"  # Добавляем "20" к году
                    formatted_date = f"{date_part[0]}.{date_part[1]}.{year} {time_part[0]}:{time_part[1]}"
                else:
                    formatted_date = date_str
            else:
                formatted_date = date_str
        except:
            formatted_date = date_str

        # Проверяем наличие поля ordersUID и добавляем его, если оно есть
        orders_uid = None
        if 'ordersUID' in order:
            orders_uid = order.get('ordersUID')

        formatted_order = {
            'order_ID': str(order.get('_id')),
            'created_at': formatted_date,
            'status': order.get('status', 'in work'),
            'positions': positions,
            'ordersUID': orders_uid
        }

        return jsonify({
            'success': True,
            'order': formatted_order
        })
    except Exception as e:
        app.logger.error(f'Error getting order: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to get order'
        }), 500

@app.route('/api/cancel-order', methods=['POST'])
def cancel_order():
    try:
        # Получаем последний заказ со статусом "Новый"
        latest_order = mongo.cx.Pivo.Orders.find_one(
            {'status': 'Новый'},
            sort=[('date', -1)]  # сортируем по дате по убыванию
        )

        if not latest_order:
            return jsonify({"success": False, "error": "Новый заказ не найден"}), 404

        # Обновляем статус найденного заказа
        result = mongo.cx.Pivo.Orders.update_one(
            {
                '_id': latest_order['_id'],
                'status': 'Новый',
                'org_ID': latest_order['org_ID']  # дополнительная проверка org_ID
            },
            {'$set': {'status': 'Отменен'}}
        )

        if result.modified_count == 0:
            return jsonify({"success": False, "error": "Не удалось отменить заказ"}), 500

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Ошибка при отмене заказа: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

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
        return jsonify({
            "success": True,
            "coefficient": coefficient or "1.0",
            "last_date": last_date
        })
    except Exception as e:
        logger.error(f"Error getting coefficient: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/update-coefficient', methods=['POST'])
def update_coefficient():
    try:
        coefficient = request.json.get('coefficient')
        user_id = request.json.get('user_id')
        
        # Проверяем права администратора
        if not check_admin_access(user_id):
            return jsonify({"success": False, "error": "Unauthorized"}), 401
            
        # Проверяем валидность коэффициента
        try:
            coef_float = float(coefficient)
            if not (0.75 <= coef_float <= 1.25):
                return jsonify({"success": False, "error": "Коэффициент должен быть от 0.75 до 1.25"}), 400
        except ValueError:
            return jsonify({"success": False, "error": "Некорректное значение коэффициента"}), 400
            
        # Обновляем коэффициент в Redis
        redis_client.hset('beer:setting', 'coefficient', str(coefficient))
        # Обновляем дату последнего изменения с учетом часового пояса UTC+10
        timezone = pytz.timezone('Asia/Vladivostok')  # UTC+10
        current_time = datetime.now(timezone).strftime("%d.%m.%Y %H:%M")
        redis_client.hset('beer:setting', 'coefficient_last_Date', current_time)
        
        return jsonify({
            "success": True,
            "last_date": current_time
        })
    except Exception as e:
        logger.error(f"Error updating coefficient: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/get-user-org-data')
def get_user_org_data():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400

        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        if not user_data:
            return jsonify({'success': False, 'error': 'User not found in Redis'}), 404

        org_id = user_data.get('org_ID')
        
        if not org_id:
            return jsonify({'success': False, 'error': 'Organization ID not found'}), 404
        
        # Получаем информацию об организации из MongoDB для получения organizationId
        org_info = mongo.cx.Pivo.organizations.find_one({'_id': org_id})
        
        if not org_info:
            logger.warning(f"Организация с ID {org_id} не найдена в MongoDB")
            organization_id = ""
        else:
            organization_id = org_info.get('organizationId', '')
            logger.debug(f"Найден organizationId: {organization_id} для org_ID: {org_id}")
        
        # Если нет organization_id, используем значение по умолчанию
        if not organization_id:
            organization_id = '16d7a1a8-a651-11ef-895a-005056c00008'  # Значение по умолчанию
            
        # Получаем информацию о товарах для получения UID и legalEntity
        catalog_items = list(mongo.cx.Pivo.catalog.find({}, {'id': 1, 'name': 1, 'UID': 1, 'legalEntity': 1}))
        logger.debug(f"Получено {len(catalog_items)} товаров из каталога")
        
        # Создаем словарь сопоставления id -> UID для товаров
        uid_map = {}
        
        # Устанавливаем фиксированное значение legalEntity для всех запросов
        legal_entity = "2724132975"  # Фиксированное значение ИНН
        
        # Подробное логирование товаров без UID
        items_without_uid = []
        
        for item in catalog_items:
            item_id = str(item.get('id', ''))
            item_uid = item.get('UID')
            
            if 'id' in item and item_id and 'UID' in item and item_uid:
                uid_map[item_id] = item_uid
            else:
                items_without_uid.append({
                    'id': item_id,
                    'name': item.get('name', 'Неизвестно'),
                    'UID': item_uid
                })
        
        if items_without_uid:
            logger.warning(f"Найдено {len(items_without_uid)} товаров без UID: {json.dumps(items_without_uid, ensure_ascii=False)}")
        
        # Подробное логирование полученных UID
        logger.debug(f"Сформирована карта соответствий ID -> UID для {len(uid_map)} товаров")
        
        # Проверяем, все ли товары имеют UID
        total_items = len(catalog_items)
        mapped_items = len(uid_map)
        if mapped_items < total_items:
            logger.warning(f"Не все товары имеют UID: {mapped_items} из {total_items}")
            
        # Выборочно выводим некоторые соответствия для отладки
        sample_entries = list(uid_map.items())[:5]
        logger.debug(f"Примеры соответствия ID -> UID: {sample_entries}")

        # Возвращаем данные организации и карту UID
        return jsonify({
            'success': True,
            'data': {
                'org_ID': org_id,
                'organization': user_data.get('organization', ''),
                'customer_id': organization_id,  # Для обратной совместимости
                'organization_id': organization_id,
                'legal_entity': legal_entity,
                'uid_map': uid_map
            }
        })
    except Exception as e:
        logger.error(f'Error getting user organization data: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to get user organization data'
        }), 500

@app.route('/api/calculate-prices', methods=['POST'])
def calculate_prices():
    try:
        logger.debug("Получен запрос на расчет цен")
        data = request.json
        
        # Подробное логирование входящих данных
        logger.debug("Входящие данные (ID_customer): %s", data.get('ID_customer', ''))
        logger.debug("Входящие данные (INN_legal_entity): %s", data.get('INN_legal_entity', ''))
        logger.debug("Входящие данные (количество позиций): %s", len(data.get('positions', [])))
        
        # Форматируем данные для передачи в API
        request_body = {
            'DATE': data.get('DATE', str(int(datetime.now().timestamp()))),
            'ID_customer': data.get('ID_customer', ''),
            'INN_legal_entity': data.get('INN_legal_entity', ''),
            'positions': data.get('positions', [])
        }
        
        try:
            response = requests.post(
                f"{config.API_BASE_URL}{config.API_ENDPOINTS['calculate_checkout']}",
                json=request_body,
                auth=(config.API_USERNAME, config.API_PASSWORD),
                headers={'Content-Type': 'application/json'},
                timeout=10  # Добавляем тайм-аут
            )
            
            logger.debug(f"Статус ответа от API: {response.status_code}")
            logger.debug(f"Текст ответа от API: {response.text[:200]}...")
            
            # Проверяем ответ
            if response.status_code != 200:
                logger.error(f"Ошибка API: {response.status_code}, {response.text}")
                return jsonify({"error": f"API error: {response.status_code}"}), 500
                
            # Проверяем, является ли ответ сообщением об ошибке
            if response.text.strip().startswith('"') and response.text.strip().endswith('"'):
                # Это сообщение об ошибке в формате строки
                error_message = response.text.strip(' "\t\n\r')
                logger.debug(f"Ответ API: {error_message}")
                return jsonify(error_message)
                
            # Преобразуем ответ в JSON
            try:
                api_response = response.json()
                logger.debug(f"Ответ API: {api_response}")
                return jsonify(api_response)
            except Exception as e:
                logger.error(f"Ошибка при обработке JSON ответа: {str(e)}")
                # Если JSON не работает, вернем хотя бы текст
                return jsonify(response.text)
        except Exception as e:
            logger.error(f"Ошибка при запросе к API: {str(e)}")
            return jsonify({"error": f"API request error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Общая ошибка при расчете цен: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/create-1c-order', methods=['POST'])
def create_1c_order():
    try:
        logger.debug("Получен запрос на создание заказа в 1С")
        data = request.json
        user_id = data.get('userId')
        
        if not user_id or not check_user_registration(user_id):
            return jsonify({"error": "Unauthorized"}), 401

        # Подробное логирование входящих данных
        logger.debug("Входящие данные (userId): %s", user_id)
        logger.debug("Входящие данные (items): %s", json.dumps(data.get('items', []), ensure_ascii=False))
        
        # Проверка валидности товаров
        items = data.get('items', [])
        if not items:
            logger.warning("Пустой список товаров")
            return jsonify({"success": False, "error": "Пустой список товаров"}), 400
            
        # Проверка наличия UID у товаров
        items_without_uid = [item for item in items if item.get('uid') is None]
        if items_without_uid:
            logger.warning("Товары без UID: %s", json.dumps(items_without_uid, ensure_ascii=False))
            
        # Проверка наличия legalEntity у товаров
        items_without_legal = [item for item in items if item.get('legalEntity') is None]
        if items_without_legal:
            logger.warning("Товары без legalEntity: %s", json.dumps(items_without_legal, ensure_ascii=False))
            # Устанавливаем значение по умолчанию
            for item in items_without_legal:
                item['legalEntity'] = "2724132975"

        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        
        # Получаем информацию об организации из MongoDB для получения organizationId
        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({"error": "Organization ID not found"}), 404
            
        org_info = mongo.cx.Pivo.organizations.find_one({'_id': org_id})
        if not org_info:
            logger.warning(f"Организация с ID {org_id} не найдена в MongoDB")
            organization_id = ""
        else:
            organization_id = org_info.get('organizationId', '')
            logger.debug(f"Найден organizationId: {organization_id} для org_ID: {org_id}")
            
        # Если нет organization_id, используем значение по умолчанию
        if not organization_id:
            organization_id = '16d7a1a8-a651-11ef-895a-005056c00008'  # Значение по умолчанию
            
        # Получаем информацию о каталоге товаров
        catalog_items = list(mongo.cx.Pivo.catalog.find({}, {'id': 1, 'name': 1, 'UID': 1}))
        
        # Создаем словари сопоставлений для поиска UID
        catalog_uid_by_id = {}      # ID -> UID
        catalog_uid_by_name = {}    # name -> UID
        
        for item in catalog_items:
            if 'UID' in item and item.get('UID'):
                # Сопоставление по ID
                if 'id' in item and item.get('id') is not None:
                    catalog_uid_by_id[str(item.get('id', ''))] = item.get('UID')
                
                # Сопоставление по имени
                if 'name' in item and item.get('name'):
                    catalog_uid_by_name[item.get('name')] = item.get('UID')
        
        logger.debug(f"Создано {len(catalog_uid_by_id)} сопоставлений ID->UID")
        logger.debug(f"Создано {len(catalog_uid_by_name)} сопоставлений name->UID")
            
        # Группируем товары по legalEntity
        items_by_legal_entity = {}
        
        # Сначала собираем все legalEntity из позиций, которые не являются тарой
        non_tara_legal_entities = []
        for item in data.get('items', []):
            is_tara = item.get('TARA', False)
            legal_entity = item.get('legalEntity')
            if not is_tara and legal_entity is not None and legal_entity != 1:
                # Проверяем, что legalEntity не равен 1
                if str(legal_entity) not in non_tara_legal_entities:
                    non_tara_legal_entities.append(str(legal_entity))
        
        logger.debug(f"Найдены legalEntity из позиций не-тара: {non_tara_legal_entities}")
        
        # Определяем, какой legalEntity использовать для тары
        tara_legal_entity = None
        if non_tara_legal_entities:
            # Если есть legalEntity от не-тары, используем первый
            tara_legal_entity = non_tara_legal_entities[0]
            logger.debug(f"Для тары будет использован legalEntity из других позиций: {tara_legal_entity}")
        else:
            # Если нет, используем одно из стандартных значений
            standard_legal_entities = ["2724132975", "2724163243"]
            tara_legal_entity = random.choice(standard_legal_entities)
            logger.debug(f"Для тары будет использован случайно выбранный legalEntity: {tara_legal_entity}")
        
        # Теперь группируем товары, обрабатывая тару специальным образом
        for item in data.get('items', []):
            is_tara = item.get('TARA', False)
            legal_entity = item.get('legalEntity')
            
            # Если это тара или legalEntity некорректный, используем tara_legal_entity
            if is_tara or legal_entity == 1 or legal_entity is None or not str(legal_entity).strip():
                legal_entity = tara_legal_entity
                # Создаем копию товара с обновленным legalEntity
                item_copy = dict(item)
                item_copy['legalEntity'] = legal_entity
                
                if is_tara:
                    logger.debug(f"Для тары '{item.get('name')}' установлен legalEntity: {legal_entity}")
                
                if legal_entity not in items_by_legal_entity:
                    items_by_legal_entity[legal_entity] = []
                
                items_by_legal_entity[legal_entity].append(item_copy)
            else:
                # Для обычных товаров с корректным legalEntity
                if legal_entity not in items_by_legal_entity:
                    items_by_legal_entity[legal_entity] = []
                
                items_by_legal_entity[legal_entity].append(item)
        
        logger.debug(f"Товары сгруппированы по legalEntity: {len(items_by_legal_entity)} групп")
        # Логируем группировку
        for legal_entity, items in items_by_legal_entity.items():
            logger.debug(f"Группа legalEntity={legal_entity}: {len(items)} товаров")
            for item in items:
                logger.debug(f"- Товар: {item.get('name')}, ID: {item.get('id')}, UID: {item.get('uid')}")
        
        # Создаем заказы для каждой группы товаров
        orders_results = []
        
        for legal_entity, items in items_by_legal_entity.items():
            # Формируем запрос к API 1С
            positions = []
            valid_items = []
            for item in items:
                # Получаем UID товара
                uid = item.get('uid')
                item_id = item.get('id')
                item_name = item.get('name')
                
                # Если UID отсутствует, пытаемся найти его в каталоге
                if uid is None or not str(uid).strip():
                    # Сначала ищем по ID
                    if item_id and str(item_id) in catalog_uid_by_id:
                        uid = catalog_uid_by_id[str(item_id)]
                        logger.info(f"Найден UID по ID в каталоге для товара {item_name}: {uid}")
                    # Если не нашли по ID, ищем по имени
                    elif item_name and item_name in catalog_uid_by_name:
                        uid = catalog_uid_by_name[item_name]
                        logger.info(f"Найден UID по имени в каталоге для товара {item_name}: {uid}")
                    # Если не нашли ни по ID, ни по имени, делаем прямой запрос в MongoDB
                    elif item_name:
                        # Ищем товар в MongoDB по имени
                        catalog_item = mongo.cx.Pivo.catalog.find_one({'name': item_name})
                        if catalog_item and 'UID' in catalog_item and catalog_item['UID']:
                            uid = catalog_item['UID']
                            logger.info(f"Найден UID через прямой запрос в MongoDB для товара {item_name}: {uid}")
                        else:
                            # Если все еще не нашли, используем ID в качестве запасного варианта
                            uid = item_id
                            logger.warning(f"Используем ID в качестве UID для товара {item_name}: {uid}")
                
                # Если всё еще нет UID или ID, пропускаем товар
                if uid is None or not str(uid).strip():
                    logger.warning(f"Товар без UID и ID не будет добавлен в заказ: {item.get('name', 'Неизвестный товар')}")
                    continue
                    
                positions.append({
                    "ID_product": str(uid),
                    "Amount": int(item.get('quantity', 0))
                })
                valid_items.append(item)
            
            # Проверяем, есть ли товары с действительными UID или ID
            if not positions:
                logger.warning(f"Нет товаров с действительными UID или ID для legalEntity {legal_entity}")
                # Добавляем информацию о заказе, даже если не смогли его создать
                orders_results.append({
                    "legalEntity": legal_entity,
                    "items": items,
                    "order": {"error": "Нет товаров с действительными UID или ID"},
                    "success": False
                })
                continue
                
            # Формируем запрос
            request_body = {
                "DATE": str(int(datetime.now().timestamp())),
                "ID_customer": organization_id,
                "INN_legal_entity": str(legal_entity),
                "positions": positions
            }
            
            logger.debug(f"Запрос на создание заказа в 1С: {request_body}")
            logger.info(f"Отправка заказа в 1С с INN_legal_entity: {legal_entity} для {len(positions)} позиций")
            logger.info(f"Полные данные запроса в 1С: DATE={request_body['DATE']}, ID_customer={request_body['ID_customer']}, INN_legal_entity={request_body['INN_legal_entity']}, positions={positions}")
            
            # Отправляем запрос
            try:
                response = requests.post(
                    f"{config.API_BASE_URL}{config.API_ENDPOINTS['new_order']}",
                    json=request_body,
                    auth=(config.API_USERNAME, config.API_PASSWORD),
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                logger.debug(f"Ответ от API 1С: Статус {response.status_code}, Тело: {response.text}")
                
                if response.status_code != 200:
                    logger.error(f"Ошибка API 1С: {response.status_code}, {response.text}")
                    orders_results.append({
                        "legalEntity": legal_entity,
                        "items": items,
                        "order": {"error": f"API error: {response.status_code}"},
                        "success": False
                    })
                    continue
                    
                # Проверяем, является ли ответ сообщением об ошибке
                response_text = response.text.strip()
                if response_text.startswith('"') and response_text.endswith('"'):
                    # Это сообщение об ошибке в формате строки
                    error_message = response_text.strip(' "\t\n\r')
                    logger.error(f"Ошибка API 1С: {error_message}")
                    orders_results.append({
                        "legalEntity": legal_entity,
                        "items": items,
                        "order": {"error": error_message},
                        "success": False
                    })
                    continue
                
                if response_text.startswith('\n'):
                    # Это сообщение об ошибке
                    error_message = response_text.strip()
                    logger.error(f"Ошибка API 1С: {error_message}")
                    orders_results.append({
                        "legalEntity": legal_entity,
                        "items": items,
                        "order": {"error": error_message},
                        "success": False
                    })
                    continue
                    
                # Парсим ответ
                try:
                    order_response = response.json()
                    logger.debug(f"Ответ API 1С (JSON): {order_response}")
                    
                    # Проверяем корректность ответа
                    if not isinstance(order_response, dict) or "Nomer" not in order_response or "UID" not in order_response:
                        error_message = "Некорректный ответ от API 1С"
                        logger.error(f"{error_message}: {order_response}")
                        orders_results.append({
                            "legalEntity": legal_entity,
                            "items": items,
                            "order": {"error": error_message},
                            "success": False
                        })
                        continue
                    
                    # Сохраняем результат
                    orders_results.append({
                        "legalEntity": legal_entity,
                        "items": valid_items,
                        "order": order_response,
                        "success": True
                    })
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке JSON ответа: {str(e)}")
                    orders_results.append({
                        "legalEntity": legal_entity,
                        "items": items,
                        "order": {"error": f"JSON parsing error: {str(e)}"},
                        "success": False
                    })
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка при отправке запроса в 1С: {str(e)}")
                orders_results.append({
                    "legalEntity": legal_entity,
                    "items": items,
                    "order": {"error": f"Request error: {str(e)}"},
                    "success": False
                })
        
        # Формируем окончательный ответ
        response_data = {
            "success": any(order.get("success", False) for order in orders_results),
            "orders": orders_results
        }
        
        logger.debug(f"Результаты создания заказов: {response_data}")
        
        return jsonify(response_data)
                
    except Exception as e:
        logger.error(f"Ошибка при создании заказа в 1С: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/save-order', methods=['POST'])
def save_order():
    try:
        logger.debug("Получен запрос на сохранение заказа в MongoDB")
        data = request.json
        
        # Проверяем наличие необходимых полей
        if not data.get('userid'):
            return jsonify({"error": "Отсутствует идентификатор пользователя"}), 400
            
        # Сохраняем заказ в MongoDB
        result = mongo.cx.Pivo.Orders.insert_one(data)
        logger.debug(f"Заказ сохранен в MongoDB, ID: {result.inserted_id}")
        
        return jsonify({"success": True, "orderId": str(result.inserted_id)})
    except Exception as e:
        logger.error(f"Ошибка при сохранении заказа: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-order-history', methods=['GET'])
def get_order_history():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        if not user_data:
            return jsonify({"error": "User not found"}), 404
            
        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({"error": "Organization ID not found"}), 404
            
        # Получаем историю заказов из 1С
        try:
            api_url = f"{config.API_BASE_URL}{config.API_ENDPOINTS['order_history']}{org_id}"
            logger.debug(f"Отправка запроса к API 1C: GET {api_url}")
            
            api_request_start = datetime.now()
            logger.debug(f'Начало запроса к API 1C: {(api_request_start - start_time).total_seconds():.3f} сек')
            
            response = requests.get(
                api_url,
                auth=(config.API_USERNAME, config.API_PASSWORD),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            logger.debug(f"Статус ответа от API истории заказов: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Ошибка API истории заказов: {response.status_code}, {response.text}")
                return jsonify({"error": f"API error: {response.status_code}"}), 500
                
            # Преобразуем ответ в JSON
            try:
                orders_data = response.json()
                logger.debug(f"Ответ API истории заказов: {orders_data}")
                return jsonify({"success": True, "orders": orders_data})
            except Exception as e:
                logger.error(f"Ошибка при обработке JSON ответа: {str(e)}")
                return jsonify({"error": f"JSON parsing error: {str(e)}"}), 500
        except Exception as e:
            logger.error(f"Ошибка при запросе к API истории заказов: {str(e)}")
            return jsonify({"error": f"API request error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Общая ошибка при получении истории заказов: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-orders-from-1c')
def get_orders_from_1c():
    try:
        start_time = datetime.now()
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"success": False, "error": "User ID is required"}), 400
            
        logger.debug(f"Получен запрос на получение заказов из 1С для пользователя {user_id}")
        
        # Получаем данные пользователя из Redis
        user_data_start = datetime.now()
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        logger.debug(f'Получение данных пользователя из Redis: {(datetime.now() - user_data_start).total_seconds():.3f} сек')
        
        if not user_data:
            logger.warning(f"Пользователь {user_id} не найден в Redis")
            return jsonify({"success": False, "error": "User not found"}), 404
            
        org_id = user_data.get('org_ID')
        
        if not org_id:
            logger.warning(f"Для пользователя {user_id} не найден ID организации")
            return jsonify({"success": False, "error": "Organization ID not found"}), 404
            
        # Получаем историю заказов из 1С
        try:
            api_url = f"{config.API_BASE_URL}{config.API_ENDPOINTS['order_history']}{org_id}"
            logger.debug(f"Отправка запроса к API 1C: GET {api_url}")
            
            api_request_start = datetime.now()
            logger.debug(f'Начало запроса к API 1C: {(api_request_start - start_time).total_seconds():.3f} сек')
            
            response = requests.get(
                api_url,
                auth=(config.API_USERNAME, config.API_PASSWORD),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            api_request_end = datetime.now()
            logger.debug(f"Ответ получен от API 1C за: {(api_request_end - api_request_start).total_seconds():.3f} сек, статус: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Ошибка API истории заказов: {response.status_code}, {response.text}")
                return jsonify({"error": f"API error: {response.status_code}"}), 500
                
            # Обработка ответа
            process_start = datetime.now()
            try:
                # Проверяем содержимое ответа
                response_text = response.text.strip()
                
                # Если ответ пустой
                if not response_text:
                    logger.warning("Получен пустой ответ от API")
                    return jsonify({"success": True, "orders": []})
                
                # Если ответ начинается с "[{\n"
                if response_text.startswith('[{\\n'):
                    logger.debug("Ответ содержит экранированный JSON. Выполняем специальную обработку")
                    
                    # Заменяем экранированные символы
                    clean_text = response_text.replace('\\n', ' ').replace('\\', '')
                    
                    # Преобразуем в JSON
                    try:
                        orders_data = json.loads(clean_text)
                        logger.debug(f"Успешно обработан экранированный JSON. Найдено заказов: {len(orders_data)}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка декодирования JSON после очистки: {str(e)}")
                        
                        # Альтернативный подход - использовать ast.literal_eval
                        try:
                            import ast
                            # Заменяем одинарные кавычки на двойные
                            cleaned_for_ast = clean_text.replace("'", '"')
                            orders_data = ast.literal_eval(cleaned_for_ast)
                            logger.debug(f"Успешно обработан с помощью ast.literal_eval. Найдено заказов: {len(orders_data)}")
                        except Exception as ast_error:
                            logger.error(f"Ошибка обработки с помощью ast: {str(ast_error)}")
                            return jsonify({"error": f"Не удалось обработать ответ: {str(e)}, {str(ast_error)}"}), 500
                else:
                    # Обычный JSON
                    try:
                        json_data = response.json()
                        logger.debug(f"Успешно обработан стандартный JSON. Тип данных: {type(json_data)}")
                        
                        # Проверяем, является ли ответ словарем с ключом "orders"
                        if isinstance(json_data, dict) and 'orders' in json_data:
                            orders_data = json_data['orders']
                            logger.debug(f"Извлечены заказы из ключа 'orders'. Найдено заказов: {len(orders_data)}")
                        else:
                            orders_data = json_data
                            logger.debug(f"Используем данные как есть. Найдено заказов: {len(orders_data) if isinstance(orders_data, list) else 1}")
                    except Exception as e:
                        logger.error(f"Ошибка декодирования стандартного JSON: {str(e)}")
                        return jsonify({"error": f"Не удалось обработать ответ: {str(e)}"}), 500
                
                # Проверяем, что данные правильно обработаны
                if not isinstance(orders_data, list):
                    logger.error(f"Ответ не является списком: {type(orders_data)}")
                    # Преобразуем в список, если это не список
                    if isinstance(orders_data, dict):
                        orders_data = [orders_data]
                        logger.debug(f"Преобразовали словарь в список из одного элемента")
                    else:
                        return jsonify({"error": "Неверный формат данных (ожидался список)"}), 500
                
                process_end = datetime.now()
                logger.debug(f"Обработка ответа API 1C выполнена за: {(process_end - process_start).total_seconds():.3f} сек")
                
                end_time = datetime.now()
                logger.debug(f'Общее время выполнения get_orders_from_1c: {(end_time - start_time).total_seconds():.3f} сек')
                
                # Отдаем данные клиенту
                return jsonify({"success": True, "orders": orders_data})
                
            except Exception as e:
                logger.error(f"Общая ошибка при обработке ответа API: {str(e)}", exc_info=True)
                return jsonify({"error": f"JSON parsing error: {str(e)}"}), 500
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке запроса истории заказов: {str(e)}")
            return jsonify({"error": f"Request error: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Ошибка при получении истории заказов из 1С: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/save-combined-order', methods=['POST'])
def save_combined_order():
    try:
        logger.debug("Получен запрос на сохранение объединенного заказа в MongoDB")
        data = request.json
        
        # Проверяем наличие необходимых полей
        if not data.get('userId'):
            return jsonify({"error": "Отсутствует идентификатор пользователя"}), 400
            
        if not data.get('items') or len(data.get('items')) == 0:
            return jsonify({"error": "Отсутствуют товары в заказе"}), 400
            
        if not data.get('orders') or len(data.get('orders')) == 0:
            return jsonify({"error": "Отсутствуют данные о заказах в 1С"}), 400
            
        # Сохраняем все товары из корзины пользователя
        all_positions = {}
        
        # Перебираем все товары из корзины
        for index, item in enumerate(data.get('items', []), 1):
            position_key = f"Position_{index}"
            # Используем тот же UID, что и при запросе цен
            uid = item.get('uid') or None
            
            # Если UID все еще null, попробуем найти его в каталоге
            if uid is None:
                # Найдем товар в каталоге по id
                beer_id = item.get('id')
                if beer_id is not None:
                    catalog_item = mongo.cx.Pivo.catalog.find_one({'id': str(beer_id)})
                    if catalog_item and 'UID' in catalog_item and catalog_item['UID']:
                        uid = catalog_item['UID']
                        logger.debug(f"Найден UID в каталоге для товара с ID {beer_id}: {uid}")
            
            # Преобразуем UID в строку, если он есть
            if uid is not None:
                uid = str(uid)
            
            beer_id = item.get('id')
            # Преобразуем Beer_ID в строку, если он есть
            if beer_id is not None:
                beer_id = str(beer_id)
            
            all_positions[position_key] = {
                'Beer_ID': beer_id,
                'Beer_Name': item.get('name', ''),
                'Legal_Entity': item.get('legalEntity'),
                'Beer_Count': int(item.get('quantity', 0)),
                'Price': float(item.get('price', 0)),
                'UID': uid
            }
        
        # Формируем словарь ordersUID из успешно созданных заказов в 1С
        orders_uid = {}
        order_index = 1
        
        for order_data in data.get('orders', []):
            if order_data.get('success'):
                # Добавляем UID заказа в словарь ordersUID
                order_uid = order_data.get('order', {}).get('UID', '')
                if order_uid:
                    orders_uid[str(order_index)] = str(order_uid)
                    order_index += 1
        
        # Общая информация о заказе
        user_id = data.get('userId')
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        timezone = pytz.timezone('Asia/Vladivostok')  # UTC+10
        current_time = datetime.now(timezone)
        formatted_date = current_time.strftime("%d.%m.%y %H:%M")
        
        # Создаем единый заказ (без поля status)
        combined_order = {
            'date': formatted_date,
            'userid': str(user_id),
            'username': user_data.get('organization', 'ООО Пивной мир'),
            'org_ID': user_data.get('org_ID'),
            'Positions': all_positions,
            'ordersUID': orders_uid,
            'createdAt': current_time
        }
        
        # Если были успешно созданные заказы в 1С
        if orders_uid:
            # Записываем номер первого заказа для отображения
            first_order = data.get('orders', [])[0]
            if first_order.get('success'):
                combined_order['orderNomer'] = first_order.get('order', {}).get('Nomer', '')
        
        logger.debug(f"Сохраняем объединенный заказ: {combined_order}")
        
        # Сохраняем заказ в MongoDB
        result = mongo.cx.Pivo.Orders.insert_one(combined_order)
        logger.debug(f"Объединенный заказ сохранен в MongoDB, ID: {result.inserted_id}")
        
        return jsonify({"success": True, "orderId": str(result.inserted_id)})
    except Exception as e:
        logger.error(f"Ошибка при сохранении объединенного заказа: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-order-status')
def get_order_status():
    try:
        order_uid = request.args.get('order_uid')
        if not order_uid:
            return jsonify({"error": "Order UID is required"}), 400
            
        logger.debug(f"Запрос статуса заказа с UID: {order_uid}")
        
        # Отправляем запрос к API 1С для получения статуса заказа
        try:
            api_url = f"{config.API_BASE_URL}{config.API_ENDPOINTS['order_status']}{order_uid}"
            logger.debug(f"Отправка запроса: GET {api_url}")
            
            response = requests.get(
                api_url,
                auth=(config.API_USERNAME, config.API_PASSWORD),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            logger.debug(f"Статус ответа от API статуса заказа: {response.status_code}")
            logger.debug(f"Ответ от API статуса заказа: {response.text}")
            
            if response.status_code != 200:
                logger.error(f"Ошибка API статуса заказа: {response.status_code}, {response.text}")
                return jsonify({"error": f"API error: {response.status_code}"}), 500
                
            # Обработка ответа
            try:
                status_data = response.json()
                logger.debug(f"Успешно получен статус заказа: {status_data}")
                return jsonify({"success": True, "status": status_data})
            except Exception as e:
                logger.error(f"Ошибка при обработке ответа статуса заказа: {str(e)}")
                return jsonify({"error": f"JSON parsing error: {str(e)}"}), 500
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке запроса статуса заказа: {str(e)}")
            return jsonify({"error": f"Request error: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Общая ошибка при получении статуса заказа: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Новый маршрут для проксирования запросов статуса заказа
@app.route('/api/proxy-order-status')
def proxy_order_status():
    try:
        uid = request.args.get('uid')
        if not uid:
            return jsonify({"success": False, "error": "Order UID is required"}), 400
            
        logger.debug(f"Запрос статуса заказа через прокси для UID: {uid}")
        
        # Отправляем запрос к API 1С для получения статуса заказа
        api_url = f"{config.API_BASE_URL}{config.API_ENDPOINTS['order_status']}{uid}"
        logger.debug(f"Отправка запроса: GET {api_url}")
        
        response = requests.get(
            api_url,
            auth=(config.API_USERNAME, config.API_PASSWORD),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        logger.debug(f"Статус ответа от API статуса заказа: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Ошибка API статуса заказа: {response.status_code}, {response.text}")
            return jsonify({"success": False, "error": f"API error: {response.status_code}"}), 500
            
        # Обработка ответа
        try:
            response_text = response.text.strip()
            
            # Если ответ пустой, возвращаем статус по умолчанию
            if not response_text:
                logger.warning(f"Пустой ответ от API статуса заказа для UID: {uid}")
                return jsonify({"success": True, "status": "in work"})
                
            # Пробуем обработать JSON
            status_data = response.json()
            logger.debug(f"Успешно получен статус заказа: {status_data}")
            
            # Возвращаем статус в нужном формате
            return jsonify({"success": True, "status": status_data})
            
        except Exception as e:
            logger.error(f"Ошибка при обработке ответа статуса заказа: {str(e)}")
            # В случае ошибки парсинга JSON, возвращаем сам текст как статус
            return jsonify({"success": True, "status": response_text.strip()})
            
    except Exception as e:
        logger.error(f"Общая ошибка при проксировании статуса заказа: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/get-combined-order-status')
def get_combined_order_status():
    try:
        mongo_id = request.args.get('id')
        if not mongo_id:
            return jsonify({"success": False, "error": "Order ID is required"}), 400
            
        # Получаем данные заказа из MongoDB
        try:
            order = mongo.cx.Pivo.Orders.find_one({'_id': ObjectId(mongo_id)})
            if not order:
                return jsonify({"success": False, "error": "Order not found"}), 404
                
            # Собираем все статусы заказов из 1С
            statuses = []
            
            for uid_key, order_uid in order.get('ordersUID', {}).items():
                try:
                    # Запрашиваем статус каждого заказа
                    api_url = f"{config.API_BASE_URL}{config.API_ENDPOINTS['order_status']}{order_uid}"
                    response = requests.get(
                        api_url,
                        auth=(config.API_USERNAME, config.API_PASSWORD),
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        try:
                            status_data = response.json()
                            if isinstance(status_data, dict) and 'STATUS' in status_data:
                                statuses.append(status_data.get('STATUS'))
                            elif isinstance(status_data, str):
                                statuses.append(status_data)
                        except:
                            logger.warning(f"Не удалось обработать ответ статуса для заказа {order_uid}")
                except:
                    logger.warning(f"Не удалось получить статус для заказа {order_uid}")
            
            logger.debug(f"Получены статусы заказов: {statuses}")
            
            # Определяем наивысший статус
            final_status = determine_highest_status(statuses)
            
            return jsonify({
                "success": True,
                "status": final_status,
                "original_statuses": statuses
            })
                
        except Exception as e:
            logger.error(f"Ошибка при получении данных заказа: {str(e)}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Ошибка при получении комбинированного статуса заказа: {str(e)}")
        return jsonify({"error": str(e)}), 500

def determine_highest_status(statuses):
    """
    Определяет наивысший приоритет статуса из списка статусов.
    Приоритет (от низкого к высокому): Новый -> В работе -> Выполнен -> Отменен
    """
    if not statuses:
        return "В обработке"
        
    # Приоритеты статусов (чем выше число, тем выше приоритет)
    status_priority = {
        "Новый": 1,
        "В работе": 2,
        "В обработке": 2,  # Альтернативное название
        "Выполнен": 3,
        "Доставлен": 3,    # Альтернативное название
        "Отменен": 4
    }
    
    # Преобразуем все статусы к нижнему регистру для унификации
    normalized_statuses = [s.strip().lower() if isinstance(s, str) else "" for s in statuses]
    
    # Сопоставление нормализованных статусов с приоритетами
    normalized_priority = {
        "новый": 1,
        "в работе": 2,
        "в обработке": 2,
        "выполнен": 3,
        "доставлен": 3,
        "отменен": 4
    }
    
    # Находим наивысший приоритет статуса
    highest_priority = 0
    highest_status = "В обработке"  # Статус по умолчанию
    
    for status in normalized_statuses:
        if status in normalized_priority:
            priority = normalized_priority[status]
            if priority > highest_priority:
                highest_priority = priority
                # Возвращаем статус в оригинальном написании
                if status == "новый":
                    highest_status = "Новый"
                elif status in ["в работе", "в обработке"]:
                    highest_status = "В работе"
                elif status in ["выполнен", "доставлен"]:
                    highest_status = "Выполнен"
                elif status == "отменен":
                    highest_status = "Отменен"
    
    return highest_status

@app.route('/api/get-batch-order-statuses', methods=['POST'])
def get_batch_order_statuses():
    try:
        start_time = datetime.now()
        data = request.json
        
        # Проверяем наличие необходимых полей
        if not data or not isinstance(data, dict) or 'orders' not in data:
            return jsonify({"error": "Отсутствуют данные о заказах"}), 400
            
        orders = data.get('orders', [])
        if not orders or not isinstance(orders, list):
            return jsonify({"error": "Некорректный формат списка заказов"}), 400
            
        logger.debug(f"Получен запрос на получение статусов для {len(orders)} заказов напрямую из 1С")
        
        # Подготавливаем результаты
        results = {}
        mongo_ids = []
        order_uids = []
        
        # Собираем все order_uid и mongo_id
        for order in orders:
            if 'mongo_id' in order:
                mongo_id = order['mongo_id']
                mongo_ids.append(mongo_id)
                
                # Находим соответствующие UID из MongoDB, но НЕ обновляем статусы
                try:
                    mongo_order = mongo.cx.Pivo.Orders.find_one(
                        {'_id': ObjectId(mongo_id)},
                        {'ordersUID': 1}
                    )
                    
                    if mongo_order and 'ordersUID' in mongo_order and mongo_order['ordersUID']:
                        for uid_key, uid in mongo_order['ordersUID'].items():
                            if uid and uid not in order_uids:
                                order_uids.append(uid)
                                # Сохраняем соответствие mongo_id -> uid
                                if mongo_id not in results:
                                    results[mongo_id] = {
                                        'linked_uids': []
                                    }
                                results[mongo_id]['linked_uids'].append(uid)
                except Exception as e:
                    logger.error(f"Ошибка при получении UID для MongoDB ID {mongo_id}: {str(e)}")
            
            # Добавляем UID из прямых запросов
            elif 'order_uid' in order:
                order_uid = order['order_uid']
                if order_uid not in order_uids:
                    order_uids.append(order_uid)
        
        logger.debug(f"Найдено {len(mongo_ids)} MongoDB ID и {len(order_uids)} 1С UID для запроса статусов")
        
        # Получаем статусы только из 1C - всегда делаем запросы без использования кеша
        c1_start = datetime.now()
        
        # Создаем словарь для хранения статусов
        statuses = {}
        
        # Запрашиваем статусы для всех UID параллельно
        async_requests = []
        
        for uid in order_uids:
            try:
                # Создаем запрос, но не выполняем его сразу
                api_url = f"{config.API_BASE_URL}{config.API_ENDPOINTS['order_status']}{uid}"
                request_obj = {
                    'uid': uid,
                    'url': api_url
                }
                async_requests.append(request_obj)
            except Exception as e:
                logger.error(f"Ошибка при подготовке запроса для UID {uid}: {str(e)}")
        
        # Выполняем запросы параллельно с ограничением в 5 одновременных запросов
        chunk_size = 5
        for i in range(0, len(async_requests), chunk_size):
            chunk = async_requests[i:i+chunk_size]
            chunk_tasks = []
            
            for req in chunk:
                uid = req['uid']
                api_url = req['url']
                
                try:
                    # Запрашиваем статус в 1C
                    response = requests.get(
                        api_url,
                        auth=(config.API_USERNAME, config.API_PASSWORD),
                        headers={'Content-Type': 'application/json'},
                        timeout=5  # Уменьшаем тайм-аут для ускорения
                    )
                    
                    if response.status_code == 200:
                        try:
                            response_text = response.text.strip()
                            
                            # Если ответ пустой, используем статус по умолчанию
                            if not response_text:
                                logger.warning(f"Пустой ответ от API статуса заказа для UID: {uid}")
                                statuses[uid] = "В обработке"
                                continue
                                
                            # Пробуем обработать JSON или текстовый ответ
                            try:
                                status_data = response.json()
                                
                                if isinstance(status_data, str):
                                    status = status_data
                                elif isinstance(status_data, dict) and 'STATUS' in status_data:
                                    status = status_data['STATUS']
                                else:
                                    status = "В обработке"
                            except:
                                # Если не удалось распарсить JSON, используем текст как статус
                                status = response_text
                                
                            # Добавляем статус в словарь
                            statuses[uid] = status
                            logger.debug(f"Статус для заказа UID {uid} из 1C: {status}")
                            
                        except Exception as parse_error:
                            logger.warning(f"Ошибка при обработке ответа статуса для UID {uid}: {str(parse_error)}")
                            statuses[uid] = "Ошибка данных"
                    else:
                        logger.warning(f"Ошибка API при получении статуса для UID {uid}: {response.status_code}")
                        statuses[uid] = "Ошибка API"
                except Exception as req_error:
                    logger.error(f"Ошибка при запросе статуса для UID {uid}: {str(req_error)}")
                    statuses[uid] = "Ошибка запроса"
        
        c1_end = datetime.now()
        logger.debug(f"Запросы к 1C выполнены за: {(c1_end - c1_start).total_seconds():.3f} сек")
        
        # Формируем результаты для возврата клиенту
        final_results = {}
        
        # Обрабатываем MongoDB ID с использованием UID
        for mongo_id in mongo_ids:
            if mongo_id in results and 'linked_uids' in results[mongo_id]:
                # Получаем статусы всех связанных UID
                linked_statuses = []
                for uid in results[mongo_id]['linked_uids']:
                    if uid in statuses:
                        linked_statuses.append(statuses[uid])
                
                # Определяем итоговый статус
                if linked_statuses:
                    final_status = determine_highest_priority_status(linked_statuses)
                else:
                    final_status = "В обработке"
                
                # Добавляем статус в результаты
                final_results[mongo_id] = {
                    'status': final_status,
                    'source': '1c'
                }
            else:
                # Если нет связанных UID, используем статус по умолчанию
                final_results[mongo_id] = {
                    'status': "В обработке",
                    'source': 'default'
                }
        
        # Добавляем статусы для прямых UID
        for uid in order_uids:
            if uid in statuses:
                final_results[uid] = {
                    'status': statuses[uid],
                    'source': '1c'
                }
        
        end_time = datetime.now()
        logger.debug(f"Общее время выполнения batch-статусов: {(end_time - start_time).total_seconds():.3f} сек")
        
        return jsonify({
            'success': True,
            'statuses': final_results
        })
        
    except Exception as e:
        logger.error(f"Ошибка при получении batch-статусов: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def determine_highest_priority_status(statuses):
    """
    Определяет статус с наивысшим приоритетом из списка статусов.
    Приоритет: Новый < В работе/В обработке < Выполнен/Доставлен < Отменен
    """
    if not statuses:
        return "В обработке"
    
    # Словарь приоритетов (чем выше число, тем выше приоритет)
    priority_map = {
        "новый": 1,
        "в работе": 2, 
        "в обработке": 2,
        "выполнен": 3,
        "доставлен": 3,
        "отменен": 4
    }
    
    highest_priority = 0
    highest_status = "В обработке"
    
    for status in statuses:
        if not status:
            continue
            
        status_lower = status.lower()
        
        # Ищем наивысший приоритет
        for key, priority in priority_map.items():
            if key in status_lower and priority > highest_priority:
                highest_priority = priority
                
                # Возвращаем статус в оригинальном написании
                if "новый" in status_lower:
                    highest_status = "Новый"
                elif "в работе" in status_lower or "в обработке" in status_lower:
                    highest_status = "В работе"
                elif "выполнен" in status_lower or "доставлен" in status_lower:
                    highest_status = "Выполнен"
                elif "отменен" in status_lower:
                    highest_status = "Отменен"
                else:
                    highest_status = status  # Сохраняем оригинальное написание
    
    return highest_status

@app.route('/api/check-tara', methods=['POST'])
def check_tara():
    try:
        data = request.json
        uids = data.get('uids', [])
        
        logger.debug(f"Получен запрос на проверку TARA для UID: {uids}")
        
        # Результаты проверки TARA
        tara_data = {}
        
        # Подключаемся к MongoDB
        catalog = mongo.cx.Pivo.catalog
        
        # Поиск документов по UID
        for uid in uids:
            # Ищем документ по полю UID
            document = catalog.find_one({"UID": uid})
            
            if document:
                logger.debug(f"Найден документ в MongoDB для UID {uid}: TARA={document.get('TARA', False)}")
                tara_data[uid] = bool(document.get('TARA', False))
            else:
                logger.debug(f"Документ для UID {uid} не найден в MongoDB")
                tara_data[uid] = False
        
        logger.debug(f"Результаты проверки TARA: {tara_data}")
        
        return jsonify({
            'success': True,
            'tara_data': tara_data
        })
    except Exception as e:
        logger.error(f"Ошибка при проверке TARA: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/get-shipped-orders-positions')
def get_shipped_orders_positions():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "User ID is required"}), 400
            
        logger.debug(f"Получение позиций из отгруженных заказов для пользователя {user_id}")
        
        # Получаем данные пользователя из Redis для получения org_ID
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        org_id = user_data.get('org_ID')
        
        if not org_id:
            return jsonify({"success": False, "error": "Organization ID not found"}), 400
            
        logger.debug(f"Получение заказов для организации {org_id}")
        
        # Получаем последние 10 заказов организации, отсортированные по дате создания
        orders = list(mongo.cx.Pivo.Orders.find(
            {"org_ID": org_id},
            {"Positions": 1, "_id": 1, "date": 1, "createdAt": 1, "ordersUID": 1, "status": 1}
        ).sort([("createdAt", -1), ("date", -1)]).limit(10))
        
        logger.debug(f"Найдено {len(orders)} последних заказов")
        
        # Запрашиваем статусы заказов через ordersUID напрямую из 1С
        shipped_orders = []
        
        for order in orders:
            # Если у заказа есть ordersUID, проверяем статус каждого UID
            if 'ordersUID' in order and order['ordersUID'] and isinstance(order['ordersUID'], dict):
                for uid_key, order_uid in order['ordersUID'].items():
                    if order_uid:
                        try:
                            # Запрашиваем статус заказа в 1С
                            api_url = f"{config.API_BASE_URL}{config.API_ENDPOINTS['order_status']}{order_uid}"
                            logger.debug(f"Запрос статуса для заказа с UID {order_uid}")
                            
                            response = requests.get(
                                api_url,
                                auth=(config.API_USERNAME, config.API_PASSWORD),
                                headers={'Content-Type': 'application/json'},
                                timeout=5
                            )
                            
                            if response.status_code == 200:
                                status_text = response.text.strip()
                                logger.debug(f"Статус для заказа UID {order_uid} из 1C: {status_text}")
                                
                                # Проверяем, является ли статус "Отгружен" или подобным
                                status_lower = status_text.lower()
                                if 'отгруж' in status_lower or 'выполнен' in status_lower or 'доставлен' in status_lower or 'выдан' in status_lower:
                                    # Добавляем заказ в список отгруженных
                                    order['status_from_1c'] = status_text
                                    shipped_orders.append(order)
                                    logger.debug(f"Добавлен отгруженный заказ: {order.get('_id')}")
                                    break  # Если нашли хотя бы один UID со статусом "Отгружен", выходим из цикла
                        except Exception as e:
                            logger.error(f"Ошибка при получении статуса для UID {order_uid}: {str(e)}")
        
        logger.debug(f"Найдено {len(shipped_orders)} отгруженных заказов")
        
        # Собираем все уникальные позиции из отгруженных заказов
        unique_positions = {}
        
        for order in shipped_orders:
            positions = order.get('Positions', {})
            logger.debug(f"В заказе {order.get('_id')} найдено {len(positions)} позиций")
            
            for pos_key, position in positions.items():
                beer_id = position.get('Beer_ID')
                beer_name = position.get('Beer_Name')
                legal_entity = position.get('Legal_Entity', 1)
                
                if beer_id is not None and beer_name:
                    # Создаем уникальный ключ
                    key = f"{beer_id}_{legal_entity}"
                    
                    # Если позиция еще не добавлена, добавляем ее
                    if key not in unique_positions:
                        unique_positions[key] = {
                            'Beer_ID': str(beer_id),
                            'Beer_Name': beer_name,
                            'Legal_Entity': legal_entity,
                            'Beer_Count': position.get('Beer_Count', 1)
                        }
                        logger.debug(f"Добавлена уникальная позиция: {beer_name}")
        
        positions_list = list(unique_positions.values())
        logger.debug(f"Всего собрано {len(positions_list)} уникальных позиций из отгруженных заказов")
        
        return jsonify({
            "success": True,
            "positions": positions_list
        })
        
    except Exception as e:
        logger.error(f"Ошибка при получении позиций из отгруженных заказов: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/get-shipped-orders-for-input')
def get_shipped_orders_for_input():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "User ID is required"}), 400
            
        logger.debug(f"Получение отгруженных заказов для ввода остатков (пользователь {user_id})")
        
        # Получаем данные пользователя из Redis для получения org_ID
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        org_id = user_data.get('org_ID')
        
        if not org_id:
            return jsonify({"success": False, "error": "Organization ID not found"}), 400
            
        logger.debug(f"Получение заказов для организации {org_id}")
        
        # Получаем последние 10 заказов организации, отсортированные по дате создания
        orders = list(mongo.cx.Pivo.Orders.find(
            {"org_ID": org_id},
            {"Positions": 1, "_id": 1, "date": 1, "createdAt": 1, "ordersUID": 1, "status": 1}
        ).sort([("createdAt", -1), ("date", -1)]).limit(10))
        
        logger.debug(f"Найдено {len(orders)} последних заказов")
        
        # Фильтруем заказы со статусом "Отгружен" и ограничиваем до 3
        shipped_orders = []
        
        for order in orders:
            # Проверяем статус заказа (если статус не указан, считаем его "Новый")
            status = order.get('status', 'Новый')
            
            # Проверяем, является ли статус "Отгружен" или подобным
            status_lower = status.lower()
            if 'отгруж' in status_lower or 'выполнен' in status_lower or 'доставлен' in status_lower:
                # Форматируем заказ для ответа API
                formatted_order = {
                    'order_ID': str(order.get('_id')),
                    'date': order.get('date', ''),
                    'status': status,
                    'positions': []
                }
                
                # Преобразуем позиции из словаря в список
                positions = order.get('Positions', {})
                for pos_key, position in positions.items():
                    beer_id = position.get('Beer_ID')
                    beer_name = position.get('Beer_Name')
                    legal_entity = position.get('Legal_Entity', 1)
                    quantity = position.get('Beer_Count', 0)
                    price = position.get('Price', 0)
                    
                    if beer_id is not None and beer_name:
                        formatted_order['positions'].append({
                            'id': str(beer_id),
                            'name': beer_name,
                            'legal_entity': legal_entity,
                            'quantity': quantity,
                            'price': price
                        })
                
                shipped_orders.append(formatted_order)
                logger.debug(f"Добавлен отгруженный заказ: {order.get('_id')}")
                
                # Если уже нашли 3 заказа, выходим из цикла
                if len(shipped_orders) >= 3:
                    break
        
        logger.debug(f"Найдено {len(shipped_orders)} отгруженных заказов для ввода остатков")
        
        return jsonify({
            "success": True,
            "orders": shipped_orders
        })
        
    except Exception as e:
        logger.error(f"Ошибка при получении отгруженных заказов для ввода остатков: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/health-check')
def health_check():
    try:
        start_time = datetime.now()
        status = {
            "status": "ok",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "services": {
                "app": "running",
                "mongodb": "unknown",
                "redis": "unknown"
            },
            "response_time_ms": 0
        }
        
        # Проверяем подключение к MongoDB
        try:
            # Простой запрос для проверки соединения
            mongo.cx.admin.command('ping')
            status["services"]["mongodb"] = "connected"
        except Exception as e:
            logger.error(f"MongoDB health check failed: {str(e)}")
            status["services"]["mongodb"] = "error"
            status["status"] = "degraded"
            
        # Проверяем подключение к Redis
        try:
            redis_ping = redis_client.ping()
            if redis_ping:
                status["services"]["redis"] = "connected"
            else:
                status["services"]["redis"] = "error"
                status["status"] = "degraded"
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            status["services"]["redis"] = "error"
            status["status"] = "degraded"
            
        # Рассчитываем время ответа
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000
        status["response_time_ms"] = round(response_time, 2)
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@app.route('/api/system-stats')
def system_stats():
    try:
        # Рассчитываем время работы приложения
        uptime_seconds = int(time.time() - APP_START_TIME)
        
        # Базовая информация о системе
        stats = {
            "status": "ok",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system_info": {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": platform.python_version()
            },
            "database_stats": {
                "mongodb": {},
                "redis": {}
            },
            "app_stats": {
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": format_uptime(uptime_seconds),
                "start_time": datetime.fromtimestamp(APP_START_TIME).strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        # Получаем статистику MongoDB
        try:
            # Получаем количество заказов
            order_count = mongo.cx.Pivo.Orders.count_documents({})
            stats["database_stats"]["mongodb"]["orders_count"] = order_count
            
            # Получаем количество товаров в каталоге
            catalog_count = mongo.cx.Pivo.catalog.count_documents({})
            stats["database_stats"]["mongodb"]["catalog_items_count"] = catalog_count
            
            # Получаем количество организаций
            org_count = mongo.cx.Pivo.organizations.count_documents({})
            stats["database_stats"]["mongodb"]["organizations_count"] = org_count
            
            # Проверяем размер коллекций
            db_stats = mongo.cx.Pivo.command("dbStats")
            stats["database_stats"]["mongodb"]["storage_size_mb"] = round(db_stats.get("storageSize", 0) / (1024 * 1024), 2)
            stats["database_stats"]["mongodb"]["data_size_mb"] = round(db_stats.get("dataSize", 0) / (1024 * 1024), 2)
            
        except Exception as e:
            logger.error(f"Error getting MongoDB stats: {str(e)}")
            stats["database_stats"]["mongodb"]["error"] = str(e)
            stats["status"] = "degraded"
        
        # Получаем статистику Redis
        try:
            # Получаем информацию о Redis
            redis_info = redis_client.info()
            
            # Извлекаем полезные метрики
            stats["database_stats"]["redis"]["connected_clients"] = redis_info.get("connected_clients", 0)
            stats["database_stats"]["redis"]["used_memory_human"] = redis_info.get("used_memory_human", "0")
            stats["database_stats"]["redis"]["uptime_in_seconds"] = redis_info.get("uptime_in_seconds", 0)
            
            # Получаем количество ключей пользователей
            user_keys_count = len(redis_client.keys("beer:user:*"))
            stats["database_stats"]["redis"]["user_keys_count"] = user_keys_count
            
        except Exception as e:
            logger.error(f"Error getting Redis stats: {str(e)}")
            stats["database_stats"]["redis"]["error"] = str(e)
            stats["status"] = "degraded"
            
        return jsonify(stats)
    except Exception as e:
        logger.error(f"System stats check failed: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@app.route('/api/ping')
def ping():
    """Простой эндпоинт для проверки доступности приложения."""
    return jsonify({
        "status": "ok",
        "message": "pong",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)