from flask import Flask, render_template, request
import mysql.connector
from mysql.connector import Error
from celery import Celery
import redis

app = Flask(__name__)

# Параметры подключения к MySQL базе данных
DATABASE_HOST = "db"
DATABASE_USER = "user"
DATABASE_PASSWORD = "password"
DATABASE_NAME = "shop"

# Настройки для Celery и Redis
app.config['CELERY_BROKER_URL'] = 'redis://redis:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://redis:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Инициализация базы данных
def init_db():
    try:
        conn = mysql.connector.connect(
            host=DATABASE_HOST,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            database=DATABASE_NAME
        )
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(255) NOT NULL,
                product VARCHAR(255) NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    except Error as e:
        print(f"Error connecting to MySQL: {e}")

# Задача Celery для подсчета заказов
@celery.task
def count_orders():
    try:
        conn = mysql.connector.connect(
            host=DATABASE_HOST,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            database=DATABASE_NAME
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders")
        result = cursor.fetchone()
        conn.close()
        return result[0]
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    phone = request.form['phone']
    products = request.form.getlist('product')
    
    try:
        conn = mysql.connector.connect(
            host=DATABASE_HOST,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            database=DATABASE_NAME
        )
        cursor = conn.cursor()
        for product in products:
            cursor.execute("INSERT INTO orders (name, phone, product) VALUES (%s, %s, %s)", (name, phone, product))
        conn.commit()
        conn.close()

        # Запуск задачи Celery для подсчета заказов
        count_orders.apply_async()

        return "Заказ успешно отправлен! С вами скоро свяжутся)"
    except Error as e:
        return f"Ошибка: {e}"

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
