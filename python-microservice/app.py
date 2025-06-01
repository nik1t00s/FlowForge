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
def get_sqlite_connection():
    conn = sqlite3.connect('metadata_cache.db', check_same_thread=False)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            id INTEGER PRIMARY KEY,
            timestamp DATETIME,
            source TEXT,
            brightness REAL,
            processed BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    return conn

# Инициализация таблицы
with get_sqlite_connection() as conn:
    pass

# Подключение к ClickHouse
def connect_clickhouse():
    client = Client(
        host="clickhouse-db",
        user='default',
        password='password'
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
                cursor.execute("SELECT * FROM metadata WHERE processed=0")
                rows = cursor.fetchall()
                
                if rows:
                    processed_count = 0
                    
                    for row in rows:
                        # Обрабатываем каждую запись отдельно для упрощения
                        if row[1] is not None:
                            try:
                                # Преобразуем строку в объект datetime и затем формируем для ClickHouse
                                dt = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S.%f")
                                
                                # Простая вставка одной записи
                                query = f"INSERT INTO {CLICKHOUSE_TABLE} (timestamp, source, brightness) VALUES"
                                ch_client.execute(query, [(dt, row[2], float(row[3]))])
                                
                                # Помечаем как обработанную
                                cursor.execute("UPDATE metadata SET processed=1 WHERE id=?", (row[0],))
                                conn.commit()
                                processed_count += 1
                            except Exception as e:
                                print(f"Ошибка при вставке записи {row[0]}: {str(e)}")
                        else:
                            print(f"Skipping row with NULL timestamp: {row}")
                            # Помечаем как обработанную, чтобы не пытаться обработать снова
                            cursor.execute("UPDATE metadata SET processed=1 WHERE id=?", (row[0],))
                            conn.commit()
                    
                    if processed_count > 0:
                        print(f"Отправлено {processed_count} записей в ClickHouse")
                    
                    
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
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO metadata (timestamp, source, brightness) VALUES (?, ?, ?)",
                (timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"), msg.topic, float(brightness))
            )
            conn.commit()
        
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