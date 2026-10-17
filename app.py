import os
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, render_template, request, send_from_directory

app = Flask(__name__)

# Автоматическое определение среды: в облаке Render или на локальном компьютере
IS_RENDER = os.environ.get('RENDER')
BASE_DIR = '/data' if IS_RENDER else os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(BASE_DIR, 'smart_city.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

# Создаем папку для хранения фотографий, если её нет
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            description TEXT,
            latitude REAL,
            longitude REAL,
            photo_path TEXT,
            date_created TEXT
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/')
def index():
    return render_template('index.html')


# API для отправки новой проблемы с координатами и фото
@app.route('/api/report', methods=['POST'])
def report_issue():
    category = request.form.get('category')
    description = request.form.get('description')
    lat = request.form.get('latitude')
    lng = request.form.get('longitude')
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not lat or not lng:
        return jsonify({"status": "error", "message": "Не указаны координаты на карте!"}), 400

    # Обработка загрузки фотографии
    photo_file = request.files.get('photo')
    photo_path = ""
    if photo_file and photo_file.filename != "":
        # Формируем уникальное имя файла
        filename = f"{datetime.now().timestamp()}_{photo_file.filename}"
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo_file.save(full_path)
        photo_path = f"/uploads/{filename}"

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO issues (category, description, latitude, longitude, photo_path, date_created)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (category, description, lat, lng, photo_path, date_now))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Проблема и фото успешно сохранены!"})


# API для получения всех точек для отображения на карте Яндекса
@app.route('/api/issues', methods=['GET'])
def get_issues():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM issues')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


# Маршрут для отображения загруженных фотографий
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    init_db()
    # Порт динамически берется из настроек облака или равен 5000 по умолчанию
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
