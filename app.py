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
# Импортируем настройки из файла конфигурации
import config

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация MongoDB из файла настроек
app.config["MONGO_URI"] = config.MONGO_URI
mongo = PyMongo(app)

# Конфигурация Redis из файла настроек
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
            return render_template('unauthorized.html', telegram_bot_url=config.TELEGRAM_BOT_REGISTER_URL)

        # Сначала проверяем, является ли пользователь администратором
        if check_admin_access(user_id):
            return redirect(f'/admin_panel?user_id={user_id}')

        # Если не админ, тогда проверяем регистрацию
        if not check_user_registration(user_id):
            return render_template('unauthorized.html', telegram_bot_url=config.TELEGRAM_BOT_REGISTER_URL)

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
        products = list(mongo.cx[config.MONGO_DB_NAME].catalog.find())
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

        products = list(mongo.cx[config.MONGO_DB_NAME].catalog.find())
        
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

        products = list(mongo.cx[config.MONGO_DB_NAME].catalog.find())
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
        data = request.json
        logger.debug(f"Получены данные: {data}")
        
        # Сохраняем заказ в базу данных
        order_data = {
            'userId': data.get('userId'),
            'items': data.get('items'),
            'total': data.get('total'),
            'createdAt': datetime.now(),
            'status': 'pending'
        }
        
        result = mongo.cx[config.MONGO_DB_NAME].Orders.insert_one(order_data)
        order_id = str(result.inserted_id)
        
        return jsonify({"success": True, "orderId": order_id})
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/order_menu')
def order_menu():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return redirect('/')
            
        products = list(mongo.cx[config.MONGO_DB_NAME].catalog.find())
        
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
            
        return render_template('order_menu.html', products=formatted_products, user_id=user_id)
    except Exception as e:
        logger.error(f"Error in order_menu route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/api/get-last-orders')
def get_last_orders():
    try:
        # Получаем параметры запроса
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 5))
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        if not check_user_registration(user_id):
            return jsonify({"error": "Unauthorized"}), 401
            
        # Получаем данные пользователя из Redis для получения org_ID
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        if not user_data or 'org_ID' not in user_data:
            return jsonify({"error": "Organization ID not found"}), 404
            
        org_id = user_data.get('org_ID')
        
        # Получаем заказы из MongoDB по org_ID
        orders = list(mongo.cx[config.MONGO_DB_NAME].Orders.find(
            {"org_ID": org_id}, 
            {"positions": 1, "createdAt": 1, "status": 1, "order_uids": 1}
        ).sort("createdAt", -1).limit(limit))
        
        # Преобразуем _id в строку для JSON-сериализации
        for order in orders:
            order['_id'] = str(order['_id'])
            
            # Добавляем информацию о заказе из 1С, если есть
            order_requests = []
            if 'order_uids' in order and order['order_uids']:
                for uid in order['order_uids'].values():
                    order_requests.append({"order_uid": uid})
            elif '_id' in order:
                order_id = str(order['_id'])
                order_requests.append({"mongo_id": order_id})
        
        # Сериализуем ObjectId в строки
        serialized_orders = json.loads(json_util.dumps(orders))
        
        return jsonify({
            "success": True,
            "orders": serialized_orders
        })
        
    except Exception as e:
        logger.error(f"Error getting last orders: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-orders')
def get_orders():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        if not check_user_registration(user_id):
            return jsonify({"error": "Unauthorized"}), 401
            
        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        if not user_data:
            return jsonify({'success': False, 'error': 'User not found in Redis'}), 404
        
        redis_time = datetime.now()
        start_time = datetime.now()
        logger.debug(f'Получены данные из Redis: {(redis_time - start_time).total_seconds():.3f} сек')
            
        # Получаем org_ID из данных пользователя
        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({'success': False, 'error': 'Organization ID not found'}), 404
            
        query_time_start = datetime.now()
            
        # Получаем 5 последних заказов из MongoDB по org_ID, сортированных по дате
        # Исключаем поле positions, так как оно большое и может замедлить запрос
        logger.debug(f'Начало запроса к MongoDB: {(query_time_start - start_time).total_seconds():.3f} сек')
        
        orders = list(mongo.cx[config.MONGO_DB_NAME].Orders.find(
            {"org_ID": org_id}, 
            {
                "positions": 0,  # Исключаем поле positions
                "createdAt": 1, 
                "status": 1, 
                "order_uids": 1,
                "status_from_1c": 1,
                "order_number": 1,
                "total": 1
            }
        ).sort("createdAt", -1).limit(5))
        
        query_time_end = datetime.now()
        logger.debug(f'Запрос к MongoDB выполнен за: {(query_time_end - query_time_start).total_seconds():.3f} сек, получено {len(orders)} заказов')
        
        # Преобразуем даты в строки и _id в строку для JSON-сериализации
        for order in orders:
            if 'createdAt' in order:
                created_at = order['createdAt']
                
                # Если это datetime, форматируем его
                if isinstance(created_at, datetime):
                    # Используем оригинальную дату из MongoDB, без преобразований
                    order['createdAt_formatted'] = created_at.strftime("%d.%m.%Y %H:%M:%S")
                    order['createdAt_unix'] = int(created_at.timestamp())
            
            order['_id'] = str(order['_id'])
        
        # Сериализуем заказы в JSON
        serialized_orders = json.loads(json_util.dumps(orders))
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        logger.debug(f'Общее время выполнения get_orders: {total_time:.3f} сек')
        
        return jsonify({
            "success": True,
            "orders": serialized_orders
        })
        
    except Exception as e:
        logger.error(f"Error getting orders: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-order')
def get_order():
    try:
        order_id = request.args.get('id')
        if not order_id:
            return jsonify({"error": "Order ID is required"}), 400
            
        # Получаем заказ из MongoDB по _id
        order = mongo.cx[config.MONGO_DB_NAME].Orders.find_one({'_id': ObjectId(order_id)})
        if not order:
            return jsonify({"error": "Order not found"}), 404
            
        # Преобразуем _id в строку для JSON-сериализации
        order['_id'] = str(order['_id'])
        
        # Сериализуем даты
        if 'createdAt' in order:
            order['createdAt'] = order['createdAt'].strftime("%d.%m.%Y %H:%M:%S")
            
        # Сериализуем ObjectId в строки
        serialized_order = json.loads(json_util.dumps(order))
        
        return jsonify({
            "success": True,
            "order": serialized_order
        })
        
    except Exception as e:
        logger.error(f"Error getting order: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cancel-order', methods=['POST'])
def cancel_order():
    try:
        data = request.json
        order_id = data.get('orderId')
        
        if not order_id:
            return jsonify({"error": "Order ID is required"}), 400
            
        # Находим последний заказ по ID
        latest_order = mongo.cx[config.MONGO_DB_NAME].Orders.find_one(
            {'_id': ObjectId(order_id)},
            sort=[('createdAt', -1)]
        )
        
        if not latest_order:
            return jsonify({"error": "Order not found"}), 404
            
        # Обновляем статус заказа
        result = mongo.cx[config.MONGO_DB_NAME].Orders.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'status': 'cancelled'}}
        )
        
        if result.modified_count == 0:
            return jsonify({"error": "Failed to update order status"}), 500
            
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
            return jsonify({"error": "User ID is required"}), 400
            
        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        
        if not user_data:
            return jsonify({"error": "User not found in Redis"}), 404
            
        # Получаем информацию об организации из MongoDB для получения organizationId
        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({"error": "Organization ID not found"}), 404
            
        org_info = mongo.cx[config.MONGO_DB_NAME].organizations.find_one({'_id': org_id})
        if not org_info:
            logger.warning(f"Организация с ID {org_id} не найдена в MongoDB")
            return jsonify({"error": "Organization not found in MongoDB"}), 404
        
        # Получаем информацию о каталоге товаров для legalEntity
        catalog_items = list(mongo.cx[config.MONGO_DB_NAME].catalog.find({}, {'id': 1, 'name': 1, 'UID': 1, 'legalEntity': 1}))
        
        # Создаем словарь legalEntity по ID товара
        legal_entities = {}
        for item in catalog_items:
            if 'id' in item and 'legalEntity' in item:
                legal_entities[str(item['id'])] = item['legalEntity']
        
        # Преобразуем _id в строку для JSON-сериализации
        org_info['_id'] = str(org_info['_id'])
        
        # Добавляем информацию о legalEntity
        org_info['legal_entities'] = legal_entities
        
        # Сериализуем ObjectId в строки
        serialized_org = json.loads(json_util.dumps(org_info))
        
        return jsonify({
            "success": True,
            "org_data": serialized_org,
            "user_data": user_data
        })
        
    except Exception as e:
        logger.error(f"Error getting user organization data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/save-order', methods=['POST'])
def save_order():
    try:
        logger.debug("Получен запрос на сохранение заказа в MongoDB")
        data = request.json
        
        # Сохраняем заказ в MongoDB
        result = mongo.cx[config.MONGO_DB_NAME].Orders.insert_one(data)
        logger.debug(f"Заказ сохранен в MongoDB, ID: {result.inserted_id}")
        
        return jsonify({
            "success": True,
            "orderId": str(result.inserted_id)
        })
    except Exception as e:
        logger.error(f"Ошибка при сохранении заказа: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

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
                    catalog_item = mongo.cx[config.MONGO_DB_NAME].catalog.find_one({'id': str(beer_id)})
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
        result = mongo.cx[config.MONGO_DB_NAME].Orders.insert_one(combined_order)
        logger.debug(f"Объединенный заказ сохранен в MongoDB, ID: {result.inserted_id}")
        
        return jsonify({
            "success": True,
            "orderId": str(result.inserted_id)
        })
    except Exception as e:
        logger.error(f"Ошибка при сохранении объединенного заказа: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/get-order-status')
def get_order_status():
    try:
        order_uid = request.args.get('order_uid')
        if not order_uid:
            return jsonify({"error": "Order UID is required"}), 400
            
        logger.debug(f"Запрос статуса заказа с UID: {order_uid}")
        
        # Отправляем запрос к API 1С для получения статуса заказа
        try:
            api_url = f'{config.API_1C_BASE_URL}{config.API_1C_ORDER_STATUS_ENDPOINT.format(uid=order_uid)}'
            logger.debug(f"Отправка запроса: GET {api_url}")
            
            response = requests.get(
                api_url,
                auth=config.API_1C_AUTH,
                headers={'Content-Type': 'application/json'},
                timeout=config.API_1C_TIMEOUT
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
        api_url = f'{config.API_1C_BASE_URL}{config.API_1C_ORDER_STATUS_ENDPOINT.format(uid=uid)}'
        logger.debug(f"Отправка запроса: GET {api_url}")
        
        response = requests.get(
            api_url,
            auth=config.API_1C_AUTH,
            headers={'Content-Type': 'application/json'},
            timeout=config.API_1C_TIMEOUT
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
        # Получаем MongoDB ID заказа
        order_id = request.args.get('order_id')
        if not order_id:
            return jsonify({"error": "Order ID is required"}), 400
            
        # Получаем заказ из MongoDB
        try:
            order = mongo.cx[config.MONGO_DB_NAME].Orders.find_one({'_id': ObjectId(order_id)})
            if not order:
                return jsonify({"error": "Order not found"}), 404
        except Exception as e:
            logger.error(f"Ошибка при получении заказа из MongoDB: {str(e)}")
            return jsonify({"error": f"Error: {str(e)}"}), 500
            
        # Проверяем наличие ordersUID
        if not order.get('ordersUID') or not isinstance(order.get('ordersUID'), dict):
            return jsonify({"success": True, "status": "В обработке", "original": None})
            
        # Получаем статусы всех заказов в 1С
        statuses = []
        try:
            for uid_key, order_uid in order.get('ordersUID', {}).items():
                try:
                    # Запрашиваем статус каждого заказа
                    api_url = f'{config.API_1C_BASE_URL}{config.API_1C_ORDER_STATUS_ENDPOINT.format(uid=order_uid)}'
                    response = requests.get(
                        api_url,
                        auth=config.API_1C_AUTH,
                        headers={'Content-Type': 'application/json'},
                        timeout=config.API_1C_TIMEOUT
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
        
        # Получаем список идентификаторов заказов
        mongo_ids = data.get('mongo_ids', [])
        order_uids = data.get('order_uids', [])
        
        # Проверяем, есть ли идентификаторы для запроса
        if not mongo_ids and not order_uids:
            return jsonify({
                'success': False,
                'error': 'Требуется хотя бы один идентификатор заказа'
            }), 400
            
        logger.debug(f"Запрос статусов для {len(mongo_ids)} MongoDB ID и {len(order_uids)} UID")
        
        # Данные о соответствии MongoDB ID и UID
        results = {}
        
        # Запросы к API 1C для получения статусов
        api_requests = []
        
        # Собираем все order_uid и mongo_id
        for order_uid in order_uids:
            api_requests.append({
                'uid': order_uid,
                'url': f"{config.API_1C_BASE_URL}{config.API_1C_ORDER_STATUS_ENDPOINT.format(uid=order_uid)}"
            })
            
        # Находим соответствующие UID из MongoDB, но НЕ обновляем статусы
        for mongo_id in mongo_ids:
            try:
                mongo_order = mongo.cx[config.MONGO_DB_NAME].Orders.find_one(
                    {'_id': ObjectId(mongo_id)},
                    {'ordersUID': 1}
                )
                
                if mongo_order and 'ordersUID' in mongo_order and mongo_order['ordersUID']:
                    for uid_key, uid in mongo_order['ordersUID'].items():
                        api_requests.append({
                            'uid': uid,
                            'url': f"{config.API_1C_BASE_URL}{config.API_1C_ORDER_STATUS_ENDPOINT.format(uid=uid)}"
                        })
                    
                    # Сохраняем соответствие mongo_id -> uid
                    if mongo_id not in results:
                        results[mongo_id] = {
                            'linked_uids': []
                        }
                    results[mongo_id]['linked_uids'].append(uid)
            except Exception as e:
                logger.error(f"Ошибка при получении UID для MongoDB ID {mongo_id}: {str(e)}")
        
        # Запрашиваем статусы всех заказов в 1C
        logger.debug(f"Найдено {len(mongo_ids)} MongoDB ID и {len(order_uids)} 1С UID для запроса статусов")
        logger.debug(f"Всего будет отправлено {len(api_requests)} запросов к API 1C")
        
        # Статусы заказов
        statuses = {}
        
        # Получаем статусы только из 1C - всегда делаем запросы без использования кеша
        c1_start = datetime.now()
        
        for req in api_requests:
            uid = req['uid']
            api_url = req['url']
            
            try:
                # Запрашиваем статус в 1C
                response = requests.get(
                    api_url,
                    auth=config.API_1C_AUTH,
                    headers={'Content-Type': 'application/json'},
                    timeout=config.API_1C_TIMEOUT
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
        catalog = mongo.cx[config.MONGO_DB_NAME].catalog
        
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
        if not user_data:
            return jsonify({"success": False, "error": "User not found"}), 404
            
        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({"success": False, "error": "Organization ID not found"}), 404
            
        # Получаем отгруженные заказы (со статусом "Выполнен" или "Доставлен")
        orders = list(mongo.cx[config.MONGO_DB_NAME].Orders.find(
            {
                "org_ID": org_id,
                "$or": [
                    {"status_from_1c": {"$regex": "выполнен", "$options": "i"}},
                    {"status_from_1c": {"$regex": "доставлен", "$options": "i"}}
                ]
            },
            {
                "positions": 1,
                "createdAt": 1,
                "order_number": 1
            }
        ).sort("createdAt", -1).limit(10))
        
        # Обработка результатов
        return jsonify({
            "success": True,
            "orders": json.loads(json_util.dumps(orders))
        })
    
    except Exception as e:
        logger.error(f"Ошибка при получении позиций отгруженных заказов: {str(e)}")
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
            
        # Получаем данные пользователя из Redis для получения org_ID
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        if not user_data:
            return jsonify({"success": False, "error": "User not found"}), 404
            
        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({"success": False, "error": "Organization ID not found"}), 404
            
        # Получаем отгруженные заказы (со статусом "Выполнен" или "Доставлен")
        orders = list(mongo.cx[config.MONGO_DB_NAME].Orders.find(
            {
                "org_ID": org_id,
                "$or": [
                    {"status_from_1c": {"$regex": "выполнен", "$options": "i"}},
                    {"status_from_1c": {"$regex": "доставлен", "$options": "i"}}
                ]
            },
            {
                "positions": 1,
                "createdAt": 1,
                "order_number": 1
            }
        ).sort("createdAt", -1).limit(50))
        
        # Обработка результатов
        return jsonify({
            "success": True,
            "orders": json.loads(json_util.dumps(orders))
        })
    
    except Exception as e:
        logger.error(f"Ошибка при получении отгруженных заказов: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/my_orders')
def my_orders():
    user_id = request.args.get('user_id')
    if not user_id:
        return 'User ID is required', 400
    return render_template('my_orders.html', user_id=user_id)

@app.route('/api/get-n8n-webhook-url')
def get_n8n_webhook_url():
    try:
        # Возвращаем URL webhook из конфигурации
        return jsonify({
            "success": True,
            "url": config.N8N_WEBHOOK_URL
        })
    except Exception as e:
        logger.error(f"Ошибка при получении URL webhook: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/get-orders-from-1c')
def get_orders_from_1c():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "User ID is required"}), 400
            
        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        if not user_data:
            return jsonify({"success": False, "error": "User not found"}), 404
            
        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({"success": False, "error": "Organization ID not found"}), 404
            
        logger.debug(f"Запрос истории заказов из 1C для пользователя {user_id} (org_ID: {org_id})")
        
        # Формируем URL запроса
        api_url = f"{config.API_1C_BASE_URL}{config.API_1C_ORDER_HISTORY_ENDPOINT.format(org_id=org_id)}"
        logger.debug(f"URL запроса истории заказов: {api_url}")
        
        # Отправляем запрос к API 1C
        response = requests.get(
            api_url,
            auth=config.API_1C_AUTH,
            headers={'Content-Type': 'application/json'},
            timeout=config.API_1C_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.error(f"Ошибка API истории заказов: {response.status_code}, {response.text}")
            return jsonify({"success": False, "error": f"API error: {response.status_code}"}), 500
            
        # Обрабатываем ответ
        try:
            orders_data = response.json()
            logger.debug(f"Получено {len(orders_data)} заказов из 1C")
            
            return jsonify({
                "success": True,
                "orders": orders_data
            })
        except Exception as e:
            logger.error(f"Ошибка при обработке ответа истории заказов: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
            
    except Exception as e:
        logger.error(f"Общая ошибка при получении истории заказов из 1C: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/create-1c-order', methods=['POST'])
def create_1c_order():
    try:
        data = request.json
        logger.debug(f"Получен запрос на создание заказа в 1C: {data}")
        
        if not data or not data.get('userId') or not data.get('items'):
            return jsonify({"success": False, "error": "Отсутствуют необходимые данные"}), 400
            
        # Получаем данные пользователя из Redis
        user_id = data.get('userId')
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        
        if not user_data:
            return jsonify({"success": False, "error": "Пользователь не найден"}), 404
            
        # Получаем ID организации
        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({"success": False, "error": "ID организации не найден"}), 404
            
        # Формируем данные для запроса в 1C
        items = data.get('items', [])
        
        # Группируем товары по Legal Entity
        orders_by_legal = {}
        
        for item in items:
            legal_entity = str(item.get('legalEntity', config.STANDARD_LEGAL_ENTITIES[0]))
            
            if legal_entity not in orders_by_legal:
                orders_by_legal[legal_entity] = []
                
            orders_by_legal[legal_entity].append(item)
            
        # Создаем заказы в 1C для каждого Legal Entity
        result_orders = []
        
        for legal_entity, items in orders_by_legal.items():
            # Формируем данные для запроса
            order_data = {
                "ID_customer": org_id,
                "INN_legal_entity": legal_entity,
                "positions": []
            }
            
            # Добавляем позиции
            for item in items:
                position = {
                    "ID_product": item.get('uid') or item.get('id'),
                    "Amount": float(item.get('quantity', 0))
                }
                order_data["positions"].append(position)
                
            logger.debug(f"Отправка запроса на создание заказа в 1C: {order_data}")
            
            # Отправляем запрос к API 1C
            api_url = f"{config.API_1C_BASE_URL}/zakaz"
            
            try:
                response = requests.post(
                    api_url,
                    auth=config.API_1C_AUTH,
                    headers={'Content-Type': 'application/json'},
                    json=order_data,
                    timeout=config.API_1C_TIMEOUT
                )
                
                if response.status_code == 200:
                    try:
                        order_result = response.json()
                        logger.debug(f"Успешно создан заказ в 1C: {order_result}")
                        
                        # Добавляем информацию о товарах и успехе операции
                        result_orders.append({
                            "success": True,
                            "items": items,
                            "order": order_result
                        })
                    except Exception as e:
                        logger.error(f"Ошибка при обработке ответа создания заказа: {str(e)}")
                        result_orders.append({
                            "success": False,
                            "items": items,
                            "order": {"error": f"Ошибка обработки ответа: {str(e)}"}
                        })
                else:
                    logger.error(f"Ошибка API создания заказа: {response.status_code}, {response.text}")
                    result_orders.append({
                        "success": False,
                        "items": items,
                        "order": {"error": f"API error: {response.status_code} - {response.text}"}
                    })
            except Exception as e:
                logger.error(f"Ошибка при отправке запроса создания заказа: {str(e)}")
                result_orders.append({
                    "success": False,
                    "items": items,
                    "order": {"error": f"Ошибка запроса: {str(e)}"}
                })
                
        # Проверяем, был ли хотя бы один успешный заказ
        any_success = any(order["success"] for order in result_orders)
        
        return jsonify({
            "success": any_success,
            "orders": result_orders
        })
        
    except Exception as e:
        logger.error(f"Общая ошибка при создании заказа в 1C: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/calculate-prices', methods=['POST'])
def calculate_prices():
    try:
        data = request.json
        logger.debug(f"Получен запрос на расчет цен: {data}")
        
        if not data:
            return jsonify({"error": "Отсутствуют данные запроса"}), 400
            
        # Проверяем обязательные поля
        if not data.get('ID_customer') or not data.get('positions'):
            return jsonify({"error": "Отсутствуют обязательные поля (ID_customer, positions)"}), 400
            
        # Формируем URL запроса к API 1C
        api_url = f"{config.API_1C_BASE_URL}/raschet"
        
        # Отправляем запрос к API 1C
        response = requests.post(
            api_url,
            auth=config.API_1C_AUTH,
            headers={'Content-Type': 'application/json'},
            json=data,
            timeout=config.API_1C_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.error(f"Ошибка API расчета цен: {response.status_code}, {response.text}")
            return jsonify({"error": f"API error: {response.status_code}"}), 500
            
        # Обрабатываем ответ
        try:
            prices_data = response.json()
            logger.debug(f"Успешно получены данные о ценах: {prices_data}")
            return jsonify(prices_data)
        except Exception as e:
            logger.error(f"Ошибка при обработке ответа расчета цен: {str(e)}")
            return jsonify({"error": f"JSON parsing error: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Общая ошибка при расчете цен: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)