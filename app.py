from flask import Flask, render_template, jsonify
from flask_pymongo import PyMongo
import logging
from bson import json_util
import json

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Правильная конфигурация MongoDB:
# Используем admin для аутентификации, но работаем с базой Pivo
app.config["MONGO_URI"] = "mongodb://root:otlehjoq543680@46.101.121.75:27017/admin?authSource=admin&directConnection=true"
mongo = PyMongo(app)

@app.route('/')
def index():
    try:
        logger.debug("Attempting to connect to MongoDB...")
        
        # Получаем все документы из коллекции catalog в базе Pivo
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
        return render_template('index.html', products=formatted_products)
    
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/api/products')
def get_products():
    try:
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)