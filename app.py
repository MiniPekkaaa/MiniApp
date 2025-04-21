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

@app.route('/api/get-last-orders')
def get_last_orders():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return jsonify({"error": "Unauthorized"}), 401

        # Получаем последние 3 заказа пользователя, отсортированные по дате
        orders = list(mongo.cx.Pivo.Orders.find(
            {"userid": str(user_id)},
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
        return jsonify({"success": True, "positions": result})

    except Exception as e:
        logger.error(f"Ошибка при получении последних заказов: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/loading')
def loading():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return redirect('/')
        return render_template('loading.html', user_id=user_id)
    except Exception as e:
        logger.error(f"Error in loading route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/api/analyze-remains', methods=['POST'])
def analyze_remains():
    try:
        data = request.json
        user_id = data.get('userId')
        remains = data.get('remains')

        logger.debug(f"Получен запрос на анализ остатков для пользователя {user_id}")
        logger.debug(f"Данные об остатках: {remains}")

        if not user_id or not check_user_registration(user_id):
            logger.error(f"Неавторизованный запрос для пользователя {user_id}")
            return jsonify({"error": "Unauthorized"}), 401

        # Получаем API ключ OpenAI из Redis
        try:
            # Прямой доступ к полю OpenAI в хэше beer:setting
            openai_key = redis_client.hget('beer:setting', 'OpenAI')
            logger.debug(f"Попытка получить ключ OpenAI: {openai_key}")
            
            if not openai_key:
                logger.error("OpenAI API ключ не найден в Redis")
                return jsonify({"error": "OpenAI API key not found"}), 500
            
            logger.debug("OpenAI API ключ успешно получен")
            openai.api_key = openai_key.decode('utf-8') if isinstance(openai_key, bytes) else openai_key
            
        except Exception as e:
            logger.error(f"Ошибка при получении ключа OpenAI из Redis: {str(e)}")
            return jsonify({"error": f"Ошибка при получении ключа OpenAI: {str(e)}"}), 500

        # Получаем последние 3 заказа пользователя
        last_orders = list(mongo.cx.Pivo.Orders.find(
            {"userid": str(user_id)},
            {"Positions": 1, "_id": 0}
        ).sort([("date", -1)]).limit(3))

        logger.debug(f"Найдено {len(last_orders)} последних заказов")

        # Формируем контекст для OpenAI
        order_history = []
        for order in last_orders:
            positions = order.get('Positions', {})
            for pos in positions.values():
                order_history.append({
                    'name': pos['Beer_Name'],
                    'count': pos['Beer_Count']
                })

        logger.debug(f"Сформирована история заказов: {order_history}")

        # Формируем промпт для OpenAI
        prompt = f"""На основе следующих данных о последних заказах пользователя и текущих остатках, 
        предложите рекомендуемое количество для заказа каждой позиции.

        История заказов:
        {json.dumps(order_history, ensure_ascii=False, indent=2)}

        Текущие остатки:
        {json.dumps(remains, ensure_ascii=False, indent=2)}

        Пожалуйста, верните рекомендации в формате JSON, где ключ - это ID товара, а значение - рекомендуемое количество.
        Учитывайте историю заказов и текущие остатки при формировании рекомендаций."""

        logger.debug("Отправляем запрос к OpenAI")
        
        # Отправляем запрос к OpenAI
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Вы - аналитическая система, которая помогает предсказать оптимальное количество товара для заказа на основе истории заказов и текущих остатков."},
                    {"role": "user", "content": prompt}
                ]
            )
            logger.debug("Получен ответ от OpenAI")
            logger.debug(f"Ответ OpenAI: {response.choices[0].message.content}")
        except Exception as e:
            logger.error(f"Ошибка при запросе к OpenAI: {str(e)}")
            return jsonify({"error": f"Ошибка при запросе к OpenAI: {str(e)}"}), 500

        # Парсим ответ от OpenAI
        try:
            recommendations = json.loads(response.choices[0].message.content)
            logger.debug(f"Распарсены рекомендации: {recommendations}")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при парсинге ответа OpenAI: {str(e)}")
            logger.error(f"Содержимое ответа: {response.choices[0].message.content}")
            return jsonify({"error": "Ошибка при обработке ответа от OpenAI"}), 500

        return jsonify({
            "success": True,
            "recommendations": recommendations
        })

    except Exception as e:
        logger.error(f"Необработанная ошибка в analyze-remains: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)