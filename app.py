from flask import Flask, render_template, jsonify, request
from flask_pymongo import PyMongo
import redis
import logging
from bson import json_util, ObjectId
import json
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
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
    """Проверяет регистрацию пользователя в Redis"""
    try:
        user_key = f"beer:user:{user_id}"
        return redis_client.exists(user_key)
    except Exception as e:
        logger.error(f"Error checking user registration: {str(e)}")
        return False

@app.route('/')
def index():
    try:
        # Получаем user_id из параметров запроса
        user_id = request.args.get('user_id')
        if not user_id:
            return "User ID is required", 400

        # Проверяем регистрацию пользователя
        if not check_user_registration(user_id):
            return render_template('not_registered.html')

        # Получаем все документы из коллекции catalog в базе Pivo
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

        return render_template('index.html', products=formatted_products)
    
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/cart')
def cart():
    user_id = request.args.get('user_id')
    if not user_id:
        return "User ID is required", 400

    if not check_user_registration(user_id):
        return render_template('not_registered.html')

    return render_template('cart.html')

@app.route('/api/create_order', methods=['POST'])
def create_order():
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        if not check_user_registration(user_id):
            return jsonify({"error": "User is not registered"}), 403

        # Получаем информацию о пользователе из Redis
        user_key = f"beer:user:{user_id}"
        user_info = redis_client.hgetall(user_key)

        # Создаем заказ
        order = {
            "status": "in work",
            "userId": user_id,
            "username": user_info.get('organization', 'Unknown'),
            "process": "промежуточный процесс добавления пива",
            "Positions": {}
        }

        # Добавляем позиции из корзины
        positions = {}
        for idx, item in enumerate(data.get('items', []), 1):
            position = {
                f"Position_{idx}": {
                    "Beer_ID": item['id'],
                    "Beer_Name": item['name'],
                    "Legal_Entity": item['legalEntity'],
                    "Beer_Count": item['quantity']
                }
            }
            positions.update(position)

        order["Positions"] = positions

        # Сохраняем заказ в MongoDB
        result = mongo.cx.Pivo.Orders.insert_one(order)
        
        return jsonify({
            "success": True,
            "order_id": str(result.inserted_id)
        })

    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)