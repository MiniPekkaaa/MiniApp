from flask import Flask, render_template, jsonify, request, redirect
from flask_pymongo import PyMongo
import logging
from bson import json_util, ObjectId
import json
import redis
from datetime import datetime, timedelta
import pytz
import requests

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

        # Проверяем регистрацию пользователя
        if not check_user_registration(user_id):
            return render_template('unauthorized.html')

        # Проверяем, является ли пользователь администратором
        if check_admin_access(user_id):
            return redirect(f'/admin_panel?user_id={user_id}')

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

        # Получаем последние 3 ВЫПОЛНЕННЫХ заказа организации, отсортированные по дате
        orders = list(mongo.cx.Pivo.Orders.find(
            {
                "org_ID": org_id,
                "status": "Выполнен"  # Только выполненные заказы
            },
            {"Positions": 1, "_id": 0}
        ).sort("date", -1).limit(3))

        # Собираем все уникальные позиции
        unique_positions = {}
        for order in orders:
            positions = order.get('Positions', {})
            for position in positions.values():
                beer_id = position.get('Beer_ID')
                legal_entity = position.get('Legal_Entity')
                beer_count = position.get('Beer_Count')
                
                if beer_id is None or legal_entity is None:
                    continue
                
                position_key = f"{beer_id}_{legal_entity}"
                if position_key not in unique_positions:
                    unique_positions[position_key] = {
                        'Beer_ID': beer_id,
                        'Beer_Name': position.get('Beer_Name', ''),
                        'Legal_Entity': legal_entity,
                        'Beer_Count': beer_count if beer_count is not None else 0
                    }

        # Преобразуем в список
        result = list(unique_positions.values())
        
        # Добавляем org_ID в ответ для n8n
        response_data = {
            "success": True,
            "positions": result,
            "org_ID": org_id
        }
        
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Ошибка при получении последних заказов: {str(e)}")
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
        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        if not user_data:
            return jsonify({'success': False, 'error': 'User not found in Redis'}), 404

        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({'success': False, 'error': 'Organization ID not found'}), 404

        # Получаем 5 последних заказов из MongoDB по org_ID, сортированных по дате
        orders = list(mongo.cx.Pivo.Orders.find({'org_ID': org_id}).sort('date', -1).limit(5))
        
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

            formatted_order = {
                'created_at': order.get('date', ''),
                'status': order.get('status', 'in work'),
                'positions': positions
            }
            formatted_orders.append(formatted_order)

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

        formatted_order = {
            'order_ID': str(order.get('_id')),
            'created_at': formatted_date,
            'status': order.get('status', 'in work'),
            'positions': positions
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

        # Проверяем регистрацию и права администратора
        if not check_user_registration(user_id) or not check_admin_access(user_id):
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
            organization_id = '16d79d5f-a651-11ef-895a-005056c00008'  # Значение по умолчанию
            
        # Получаем информацию о товарах для получения UID и legalEntity
        catalog_items = list(mongo.cx.Pivo.catalog.find({}, {'id': 1, 'UID': 1, 'legalEntity': 1}))
        
        # Создаем словарь сопоставления id -> UID для товаров
        uid_map = {}
        
        # Устанавливаем фиксированное значение legalEntity для всех запросов
        legal_entity = "2724132975"  # Фиксированное значение ИНН
        
        for item in catalog_items:
            if 'id' in item and 'UID' in item:
                uid_map[str(item['id'])] = item.get('UID', '')

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
        data = request.json
        logger.debug(f"Получен запрос на расчет цен: {data}")
        
        # Проверка наличия необходимых полей
        if not data.get('INN_legal_entity'):
            logger.warning("INN_legal_entity отсутствует в запросе")
            
        if not data.get('ID_customer'):
            logger.warning("ID_customer отсутствует в запросе")
            
        if not data.get('positions') or len(data.get('positions')) == 0:
            logger.warning("Positions пусты или отсутствуют в запросе")
        
        # Формируем запрос к внешнему API с правильными параметрами
        request_body = {
            "DATE": data.get('DATE', str(int(datetime.now().timestamp()))),
            "ID_customer": data.get('ID_customer', ''),
            "INN_legal_entity": data.get('INN_legal_entity', ''),
            "positions": data.get('positions', [])
        }
        
        logger.debug(f"Отправляем запрос на расчет цен: {request_body}")
        
        try:
            response = requests.post(
                'http://87.225.110.142:65531/uttest/hs/int/calculate_checkout',
                json=request_body,
                auth=('int2', 'pcKnE8GqXn'),
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
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке запроса: {str(e)}")
            return jsonify({"error": f"Request error: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Ошибка при расчете цен: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/create-1c-order', methods=['POST'])
def create_1c_order():
    try:
        logger.debug("Получен запрос на создание заказа в 1С")
        data = request.json
        user_id = data.get('userId')
        
        if not user_id or not check_user_registration(user_id):
            return jsonify({"error": "Unauthorized"}), 401

        logger.debug(f"Данные заказа: {data}")

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
            
        # Группируем товары по legalEntity
        items_by_legal_entity = {}
        for item in data.get('items', []):
            legal_entity = item.get('legalEntity')
            if legal_entity not in items_by_legal_entity:
                items_by_legal_entity[legal_entity] = []
            items_by_legal_entity[legal_entity].append(item)
            
        logger.debug(f"Товары сгруппированы по legalEntity: {len(items_by_legal_entity)} групп")
        
        # Создаем заказы для каждой группы товаров
        orders_results = []
        
        for legal_entity, items in items_by_legal_entity.items():
            # Формируем запрос к API 1С
            positions = []
            for item in items:
                uid = item.get('uid')  # ID продукта в 1С (UID)
                positions.append({
                    "ID_product": uid,
                    "Amount": int(item.get('quantity', 0))
                })
                
            # Формируем запрос
            request_body = {
                "DATE": str(int(datetime.now().timestamp())),
                "ID_customer": organization_id,
                "INN_legal_entity": str(legal_entity),
                "positions": positions
            }
            
            logger.debug(f"Запрос на создание заказа в 1С: {request_body}")
            
            # Отправляем запрос
            try:
                response = requests.post(
                    'http://87.225.110.142:65531/uttest/hs/int/novzakaz',
                    json=request_body,
                    auth=('int2', 'pcKnE8GqXn'),
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                logger.debug(f"Ответ от API 1С: Статус {response.status_code}, Тело: {response.text}")
                
                if response.status_code != 200:
                    logger.error(f"Ошибка API 1С: {response.status_code}, {response.text}")
                    return jsonify({"error": f"API error: {response.status_code}"}), 500
                    
                # Парсим ответ
                try:
                    order_response = response.json()
                    logger.debug(f"Ответ API 1С (JSON): {order_response}")
                    
                    # Сохраняем результат
                    orders_results.append({
                        "legalEntity": legal_entity,
                        "items": items,
                        "order": order_response
                    })
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке JSON ответа: {str(e)}")
                    return jsonify({"error": f"JSON parsing error: {str(e)}"}), 500
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка при отправке запроса в 1С: {str(e)}")
                return jsonify({"error": f"Request error: {str(e)}"}), 500
        
        # Формируем окончательный ответ
        response_data = {
            "success": True,
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
            response = requests.get(
                f'http://87.225.110.142:65531/uttest/hs/int/istorzakaz/{org_id}',
                auth=('int2', 'pcKnE8GqXn'),
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
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке запроса истории заказов: {str(e)}")
            return jsonify({"error": f"Request error: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Ошибка при получении истории заказов: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-orders-from-1c')
def get_orders_from_1c():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        if not user_data:
            return jsonify({"error": "User not found"}), 404
            
        # Получаем информацию об организации для получения organizationId
        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({"error": "Organization ID not found"}), 404
            
        # Получаем историю заказов из 1С используя новый эндпоинт
        try:
            response = requests.get(
                f'http://87.225.110.142:65531/uttest/hs/int/istorzakaz/{org_id}',
                auth=('int2', 'pcKnE8GqXn'),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            logger.debug(f"Статус ответа от API истории заказов: {response.status_code}")
            logger.debug(f"Ответ от API истории заказов: {response.text[:200]}...")
            
            if response.status_code != 200:
                logger.error(f"Ошибка API истории заказов: {response.status_code}, {response.text}")
                return jsonify({"error": f"API error: {response.status_code}"}), 500
                
            # Преобразуем ответ в JSON
            try:
                orders_data = response.json()
                logger.debug(f"Данные истории заказов: {orders_data}")
                return jsonify({"success": True, "orders": orders_data})
            except Exception as e:
                logger.error(f"Ошибка при обработке JSON ответа: {str(e)}")
                return jsonify({"error": f"JSON parsing error: {str(e)}"}), 500
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке запроса истории заказов: {str(e)}")
            return jsonify({"error": f"Request error: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Ошибка при получении истории заказов из 1С: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)