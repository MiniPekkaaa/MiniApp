from flask import Flask, render_template, jsonify, request, redirect
from flask_pymongo import PyMongo
import logging
from bson import json_util, ObjectId
import json
import redis

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
    db=0,
    socket_timeout=5,
    decode_responses=True
)

def check_user_registration(user_id):
    try:
        # Проверяем существование пользователя в Redis
        key = f'beer:user:{user_id}'
        logger.debug(f"Checking Redis key: {key}")
        user_data = redis_client.hgetall(key)
        logger.debug(f"Redis data for user {user_id}: {user_data}")
        return bool(user_data)
    except Exception as e:
        logger.error(f"Error checking Redis: {str(e)}")
        return False

@app.route('/test-redis')
def test_redis():
    try:
        # Проверяем подключение к Redis
        redis_client.ping()
        
        # Пробуем получить тестового пользователя
        test_user_id = "7944903241"
        key = f'beer:user:{test_user_id}'
        user_data = redis_client.hgetall(key)
        
        return jsonify({
            "redis_connection": "OK",
            "test_user_data": user_data,
            "test_key": key
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": str(type(e))
        }), 500

@app.route('/')
def index():
    try:
        user_id = request.args.get('user_id')
        logger.debug(f"Index route - Checking authorization for user: {user_id}")
        
        if not user_id:
            logger.debug("No user_id provided")
            return render_template('unauthorized.html')

        # Проверяем регистрацию пользователя
        is_registered = check_user_registration(user_id)
        logger.debug(f"User {user_id} registration status: {is_registered}")
        
        if not is_registered:
            logger.debug(f"User {user_id} not registered")
            return render_template('unauthorized.html')

        logger.debug(f"User {user_id} authorized, loading products")
        products = list(mongo.cx.Pivo.catalog.find())
        logger.debug(f"Found {len(products)} products")
        
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

        return render_template('index.html', products=formatted_products)
    
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

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

@app.route('/cart')
def cart():
    user_id = request.args.get('user_id')
    if not user_id or not check_user_registration(user_id):
        return render_template('unauthorized.html')
    return render_template('cart.html')

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
        
        order_data = {
            '_id': ObjectId(),
            'status': "in work",
            'userid': str(user_id),
            'username': user_data.get('organization', 'ООО Пивной мир'),
            'process': "промежуточный процесс добавления пива",
            'positions': {}
        }

        items = data.get('items', [])
        for index, item in enumerate(items, 1):
            position_key = f"Position_{index}"
            order_data['positions'][position_key] = {
                'Beer_ID': int(item['id']),
                'Beer_Name': item['name'],
                'Legal_Entity': int(item['legalEntity']),
                'Beer_Count': int(item['quantity'])
            }

        logger.debug(f"Подготовленный заказ: {order_data}")
        
        result = mongo.cx.Pivo.Orders.insert_one(order_data)
        logger.debug(f"Заказ создан, ID: {result.inserted_id}")

        return jsonify({"success": True, "orderId": str(result.inserted_id)})
    except Exception as e:
        logger.error(f"Ошибка при создании заказа: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)