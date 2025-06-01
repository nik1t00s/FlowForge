import sqlite3
import threading
import paho.mqtt.client as mqtt
import cv2
import numpy as np
from datetime import datetime
from clickhouse_driver import Client
import time
import traceback

# Конфигурация
MQTT_BROKER = "mosquitto"
MQTT_TOPIC = "images/raw"
CLICKHOUSE_TABLE = "images_metadata"
BRIGHTNESS_THRESHOLD = 50  # Порог фильтрации по яркости

# Инициализация SQLite
def get_sqlite_connection():
    conn = sqlite3.connect('metadata_cache.db', check_same_thread=False)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            source TEXT,
            brightness REAL,
            processed BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    return conn

# Подключение к ClickHouse
def connect_clickhouse():
    client = Client(
        host='clickhouse-db',
        port=9000,
        user='default',
        password='password',
        settings={'use_numpy': False}
    )
    client.execute(f'''
        CREATE TABLE IF NOT EXISTS {CLICKHOUSE_TABLE} (
            timestamp DateTime,
            source String,
            brightness Float32
        ) ENGINE = MergeTree()
        ORDER BY timestamp
    ''')
    return client

ch_client = connect_clickhouse()

# Фоновая отправка данных в ClickHouse
def background_sender():
    while True:
        time.sleep(10)
        try:
            with get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, timestamp, source, brightness FROM metadata WHERE processed=0")
                rows = cursor.fetchall()

                if rows:
                    data = []
                    for row in rows:
                        # Преобразование строки в DateTime
                        dt = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S.%f")
                        data.append({
                            'timestamp': dt,
                            'source': row[2],
                            'brightness': float(row[3])
                        })
                    
                    # Вставка данных
                    ch_client.execute(
                        f"INSERT INTO {CLICKHOUSE_TABLE} (timestamp, source, brightness) VALUES",
                        data,
                        types_check=True
                    )
                    
                    # Помечаем записи как обработанные
                    ids = [row[0] for row in rows]
                    for row_id in ids:
                        cursor.execute("UPDATE metadata SET processed=1 WHERE id=?", (row_id,))
                    conn.commit()
                    print(f"Отправлено {len(rows)} записей в ClickHouse")
        except Exception as e:
            print(f"Ошибка фоновой отправки: {str(e)}")
            traceback.print_exc()

# Обработчик MQTT
def on_message(client, userdata, msg):
    try:
        if not msg.payload:
            print("Получено пустое сообщение")
            return

        nparr = np.frombuffer(msg.payload, dtype=np.uint8)
        if nparr.size == 0:
            print("Буфер изображения пуст")
            return

        # Декодирование изображения
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            print("Ошибка декодирования: получены некорректные данные изображения")
            return

        # Сжатие
        resized = cv2.resize(img, (640, 360))

        # Вычисление яркости
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        brightness = np.mean(hsv[:,:,2])
        print(f"Яркость: {brightness:.2f}")

        # Фильтрация
        if brightness < BRIGHTNESS_THRESHOLD:
            print("Изображение отфильтровано по яркости")
            return

        # Сохранение в SQLite
        timestamp = datetime.now()
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO metadata (timestamp, source, brightness) VALUES (?, ?, ?)",
                (timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"), msg.topic, float(brightness))
            )
            conn.commit()

    except Exception as e:
        print(f"Ошибка обработки: {str(e)}")
        traceback.print_exc()

# Запуск фонового потока
threading.Thread(target=background_sender, daemon=True).start()

# MQTT Клиент
client = mqtt.Client()
client.connect(MQTT_BROKER, 1883)
client.subscribe(MQTT_TOPIC)
client.on_message = on_message
print("Ожидание изображений...")
client.loop_forever()