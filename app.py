from flask import Flask, render_template, jsonify, request, redirect
from flask_pymongo import PyMongo
import logging
from bson import json_util, ObjectId
import json
import redis
from datetime import datetime, timedelta
import pytz
import openai

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

def get_openai_key():
    """Получение API ключа OpenAI из Redis"""
    try:
        settings = redis_client.hgetall('beer:setting')
        if settings and 'OpenAI' in settings:
            return settings['OpenAI']
        logger.error("OpenAI API key not found in Redis settings")
        return None
    except Exception as e:
        logger.error(f"Error loading OpenAI API key from Redis: {str(e)}")
        return None

# Конфигурация OpenAI
openai.api_key = None  # Инициализируем как None

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
            'status': "in work",
            'date': current_time.strftime("%d.%m.%y %H:%M"),
            'userid': str(user_id),
            'username': user_data.get('organization', 'ООО Пивной мир'),
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

def get_last_orders(user_id, limit=3):
    """Получает последние заказы пользователя"""
    try:
        orders = list(mongo.cx.Pivo.Orders.find(
            {'userid': str(user_id)},
            {'Positions': 1, 'date': 1}
        ).sort('date', -1).limit(limit))
        
        # Собираем уникальные позиции
        unique_positions = {}
        for order in orders:
            positions = order.get('Positions', {})
            for pos in positions.values():
                beer_id = pos.get('Beer_ID')
                if beer_id not in unique_positions:
                    unique_positions[beer_id] = {
                        'Beer_ID': beer_id,
                        'Beer_Name': pos.get('Beer_Name'),
                        'Legal_Entity': pos.get('Legal_Entity'),
                        'history': []
                    }
                unique_positions[beer_id]['history'].append(pos.get('Beer_Count', 0))
        
        return list(unique_positions.values())
    except Exception as e:
        logger.error(f"Error getting last orders: {str(e)}")
        return []

def analyze_with_gpt(product_history):
    """Анализирует историю заказов с помощью GPT-4"""
    try:
        # Получаем ключ непосредственно перед использованием
        api_key = get_openai_key()
        if not api_key:
            # Если ключ не получен, возвращаем среднее значение
            return sum(product_history['history']) // len(product_history['history'])

        openai.api_key = api_key
        prompt = f"""Проанализируй историю заказов пива и предложи оптимальное количество для следующего заказа.
История заказов (последние 3 заказа): {product_history['history']}
Название пива: {product_history['Beer_Name']}

Учитывай следующие факторы:
1. Тренд изменения количества в заказах
2. Среднее значение заказов
3. Сезонность (если очевидна)

Ответ дай только числом (количество для заказа)."""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты - аналитик, специализирующийся на прогнозировании заказов."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=50
        )

        suggested_amount = int(response.choices[0].message.content.strip())
        return suggested_amount
    except Exception as e:
        logger.error(f"Error in GPT analysis: {str(e)}")
        # Если произошла ошибка, возвращаем среднее значение
        return sum(product_history['history']) // len(product_history['history'])

@app.route('/get_remaining_input')
def get_remaining_input():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return redirect('/')

        # Получаем последние заказы
        last_orders = get_last_orders(user_id)
        return render_template('remaining_input.html', products=last_orders, user_id=user_id)
    except Exception as e:
        logger.error(f"Error in get_remaining_input: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/analyze_remaining', methods=['POST'])
def analyze_remaining():
    try:
        data = request.json
        user_id = data.get('userId')
        remaining = data.get('remaining', {})
        
        if not user_id or not check_user_registration(user_id):
            return jsonify({"error": "Unauthorized"}), 401

        # Получаем историю заказов
        products = get_last_orders(user_id)
        
        # Анализируем каждую позицию
        suggestions = []
        for product in products:
            if str(product['Beer_ID']) in remaining:
                current_remaining = int(remaining[str(product['Beer_ID'])])
                # Добавляем текущий остаток в историю для анализа
                product['history'].append(current_remaining)
                
                # Получаем рекомендацию от GPT
                suggested_amount = analyze_with_gpt(product)
                
                suggestions.append({
                    'id': product['Beer_ID'],
                    'name': product['Beer_Name'],
                    'legal_entity': product['Legal_Entity'],
                    'quantity': suggested_amount
                })

        return jsonify({"success": True, "suggestions": suggestions})
    except Exception as e:
        logger.error(f"Error in analyze_remaining: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)