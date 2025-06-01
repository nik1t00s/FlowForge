import sqlite3
import threading
import paho.mqtt.client as mqtt
import cv2
import numpy as np
from datetime import datetime
from clickhouse_driver import Client
import time

# Конфигурация
MQTT_BROKER = "mosquitto"
MQTT_TOPIC = "images/raw"
CLICKHOUSE_TABLE = "images_metadata"
BRIGHTNESS_THRESHOLD = 50  # Порог фильтрации по яркости

# Инициализация SQLite
conn_sqlite = sqlite3.connect('metadata_cache.db', check_same_thread=False)
cursor_sqlite = conn_sqlite.cursor()
cursor_sqlite.execute('''
    CREATE TABLE IF NOT EXISTS metadata (
        id INTEGER PRIMARY KEY,
        timestamp DATETIME,
        source TEXT,
        brightness REAL,
        processed BOOLEAN DEFAULT 0
    )
''')
conn_sqlite.commit()

# Подключение к ClickHouse
def connect_clickhouse():
    client = Client(
        host="clickhouse",
        user='default',
        password='password',
        settings={'use_numpy': True}
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
        time.sleep(10)  # Отправка каждые 10 секунд
        try:
            cursor_sqlite.execute("SELECT * FROM metadata WHERE processed=0")
            rows = cursor_sqlite.fetchall()
            
            if rows:
                data = []
                for row in rows:
                    data.append({
                        'timestamp': datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S.%f"),
                        'source': str(row[2]),  # Явное преобразование в string
                        'brightness': float(row[3])
                    })
                
                ch_client.execute(
                    f"INSERT INTO {CLICKHOUSE_TABLE} (timestamp, source, brightness) VALUES",
                    data,
                    types_check=True
                )
                
                # Пометить как обработанные
                ids = [row[0] for row in rows]
                cursor_sqlite.executemany(
                    "UPDATE metadata SET processed=1 WHERE id=?",
                    [(id,) for id in ids]
                )
                conn_sqlite.commit()
                print(f"Отправлено {len(rows)} записей в ClickHouse")

        except Exception as e:
            print(f"Ошибка фоновой отправки: {str(e)}")
            import traceback
            traceback.print_exc()

# Обработчик MQTT
def on_message(client, userdata, msg):
    try:

        if not msg.payload:
            print("Получено пустое сообщение")
            return
            
        print(f"Получено сообщение размером: {len(msg.payload)} байт")

        nparr = np.frombuffer(msg.payload, dtype=np.uint8)
        if nparr.size == 0:
            print("Буфер изображения пуст")
            return

        # Декодирование изображения
        img = cv2.imdecode(np.frombuffer(msg.payload, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print("Ошибка декодирования: получены некорректные данные изображения")
            return

        # Сжатие
        resized = cv2.resize(img, (640, 360))
        
        # Вычисление яркости (V-канал в HSV)
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        brightness = np.mean(hsv[:,:,2])
        
        # Фильтрация
        if brightness < BRIGHTNESS_THRESHOLD:
            return
        
        # Сохранение в SQLite
        timestamp = datetime.now()
        cursor_sqlite.execute(
            "INSERT INTO metadata (timestamp, source, brightness) VALUES (?, ?, ?)",
            (str(timestamp), msg.topic, float(brightness))
        )
        conn_sqlite.commit()
        
    except Exception as e:
        print(f"Ошибка обработки: {str(e)}")

# Запуск фонового потока
threading.Thread(target=background_sender, daemon=True).start()

# MQTT Клиент
client = mqtt.Client()
client.connect(MQTT_BROKER, 1883)
client.subscribe(MQTT_TOPIC)
client.on_message = on_message
client.loop_forever()