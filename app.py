from flask import Flask, render_template, jsonify, request, redirect
from flask_pymongo import PyMongo
import logging
from bson import json_util, ObjectId
import json
import redis
from datetime import datetime, timedelta
import pytz

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
        # Проверяем что есть данные и UserChatID совпадает
        return bool(user_data) and user_data.get('UserChatID') == str(user_id)
    except Exception as e:
        logger.error(f"Error checking Redis: {str(e)}")
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
                'volume': float(product.get('volume', 0)),
                'price': int(product.get('price', 0)),
                'legalEntity': int(product.get('legalEntity', 1))
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
                'volume': float(product.get('volume', 0)),
                'price': int(product.get('price', 0)),
                'legalEntity': int(product.get('legalEntity', 1))
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
                'volume': float(product.get('volume', 0)),
                'price': int(product.get('price', 0)),
                'legalEntity': int(product.get('legalEntity', 1))
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
            positions[position_key] = {
                'Beer_ID': int(item['id']),
                'Beer_Name': item['name'],
                'Legal_Entity': int(item['legalEntity']),
                'Beer_Count': int(item['quantity'])
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
            'Positions': positions
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
                'volume': float(product.get('volume', 0)),
                'price': int(product.get('price', 0)),
                'legalEntity': int(product.get('legalEntity', 1))
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

        # Получаем последние 3 заказа организации, отсортированные по дате
        orders = list(mongo.cx.Pivo.Orders.find(
            {"org_ID": org_id},
            {"Positions": 1, "_id": 0}
        ).sort("date", -1).limit(3))

        # Собираем все уникальные позиции
        unique_positions = {}
        for order in orders:
            positions = order.get('Positions', {})
            for position in positions.values():
                position_key = f"{position['Beer_ID']}_{position['Legal_Entity']}"
                if position_key not in unique_positions:
                    unique_positions[position_key] = {
                        'Beer_ID': position['Beer_ID'],
                        'Beer_Name': position['Beer_Name'],
                        'Legal_Entity': position['Legal_Entity'],
                        'Beer_Count': 0  # Начальное значение для количества
                    }

        # Преобразуем в список
        result = list(unique_positions.values())
        
        # Добавляем org_ID в ответ для n8n
        response_data = {
            "success": True,
            "positions": result,
            "org_ID": org_id  # Добавляем org_ID в ответ
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
        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        if not user_data:
            return jsonify({'success': False, 'error': 'User not found in Redis'}), 404

        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({'success': False, 'error': 'Organization ID not found'}), 404

        # Получаем 5 последних заказов из MongoDB по org_ID, сортированных по дате
        orders = list(mongo.cx.Pivo.Orders.find({'org_ID': org_id}).sort('date', -1).limit(5))
        
        # Получаем каталог продуктов для цен
        products = {str(p['id']): p for p in mongo.cx.Pivo.catalog.find()}
        
        # Преобразуем заказы в нужный формат
        formatted_orders = []
        for order in orders:
            # Преобразуем позиции из словаря в список
            positions = []
            total_amount = 0
            
            for pos_key, pos_data in order.get('Positions', {}).items():
                beer_id = str(pos_data.get('Beer_ID'))
                quantity = pos_data.get('Beer_Count', 0)
                
                # Получаем цену из каталога
                product = products.get(beer_id, {})
                price = product.get('price', 0)
                
                # Считаем сумму для позиции
                position_total = price * quantity
                total_amount += position_total

                positions.append({
                    'name': pos_data.get('Beer_Name'),
                    'quantity': quantity,
                    'id': beer_id,
                    'price': price,
                    'legal_entity': pos_data.get('Legal_Entity')
                })

            # Преобразуем дату из строки в правильный формат
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
                'positions': positions,
                'total_amount': total_amount
            }
            formatted_orders.append(formatted_order)

        return jsonify({
            'success': True,
            'orders': formatted_orders
        })
    except Exception as e:
        app.logger.error(f'Error getting orders: {str(e)}')
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

        # Получаем каталог продуктов для цен
        products = {str(p['id']): p for p in mongo.cx.Pivo.catalog.find()}

        # Преобразуем позиции из словаря в список
        positions = []
        total_amount = 0
        
        for pos_key, pos_data in order.get('Positions', {}).items():
            beer_id = str(pos_data.get('Beer_ID'))
            quantity = pos_data.get('Beer_Count', 0)
            
            # Получаем цену из каталога
            product = products.get(beer_id, {})
            price = product.get('price', 0)
            
            # Считаем сумму для позиции
            position_total = price * quantity
            total_amount += position_total

            positions.append({
                'name': pos_data.get('Beer_Name'),
                'quantity': quantity,
                'id': beer_id,
                'price': price,
                'legal_entity': pos_data.get('Legal_Entity')
            })

        # Преобразуем дату из строки в правильный формат
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
            'positions': positions,
            'total_amount': total_amount
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
        data = request.json
        order_id = data.get('order_id')
        user_id = data.get('user_id')
        
        if not order_id or not user_id:
            return jsonify({"success": False, "error": "Order ID and User ID are required"}), 400

        # Получаем данные пользователя из Redis
        user_data = redis_client.hgetall(f'beer:user:{user_id}')
        if not user_data:
            return jsonify({"success": False, "error": "User not found"}), 404

        org_id = user_data.get('org_ID')
        if not org_id:
            return jsonify({"success": False, "error": "Organization ID not found"}), 404

        # Обновляем статус заказа на "Отменен" только если он соответствует всем критериям
        result = mongo.cx.Pivo.Orders.update_one(
            {
                '_id': ObjectId(order_id),
                'status': 'Новый',
                'org_ID': org_id,
                'userid': str(user_id)
            },
            {'$set': {'status': 'Отменен'}}
        )

        if result.modified_count == 0:
            return jsonify({
                "success": False,
                "error": "Order not found or cannot be cancelled"
            }), 404

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)