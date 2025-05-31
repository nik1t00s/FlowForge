import paho.mqtt.client as mqtt
import cv2
import numpy as np
from datetime import datetime
from clickhouse_driver import Client
import socket
import time
import sys
import functools

print = functools.partial(print, flush=True)

MQTT_BROKER = "mosquitto"
MQTT_TOPIC = "images/raw"

try:
    CLICKHOUSE_HOST = socket.gethostbyname("clickhouse")
    print(f"Resolved ClickHouse IP: {CLICKHOUSE_HOST}")
except socket.gaierror:
    print("DNS resolution failed, using default hostname")
    CLICKHOUSE_HOST = "clickhouse"

CLICKHOUSE_TABLE = "images_metadata"

def connect_clickhouse():
    max_retries = 10
    for i in range(max_retries):
        try:
            client = Client(
                host=CLICKHOUSE_HOST,
                port=9000,
                user='default',
                password='password',
                connect_timeout=10,  # Увеличим таймаут
                send_receive_timeout=30
            )
            client.execute('SELECT 1')
            print("Успешное подключение к ClickHouse")
            return client
        except Exception as e:
            print(f"Попытка подключения {i+1}/{max_retries} не удалась: {str(e)}")
            if i < max_retries - 1:
                time.sleep(10)
    print("Не удалось подключиться к ClickHouse")
    sys.exit(1)


ch_client = connect_clickhouse()

ch_client.execute('''
CREATE TABLE IF NOT EXISTS images_metadata (
    timestamp DateTime DEFAULT now(),
    source String
) ENGINE = MergeTree()
ORDER BY timestamp
''')
print("Таблица images_metadata создана/проверена")

def on_message(client, userdata, msg):
    try:
        img = cv2.imdecode(np.frombuffer(msg.payload, dtype=np.uint8), cv2.IMREAD_COLOR)
        
        if img is None:
            print("Ошибка декодирования изображения")
            return

        resized = cv2.resize(img, (640, 360))

        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        brightness = np.mean(hsv[:,:,2])
        print(f"Яркость: {brightness:.2f}")

        ch_client.execute(
            f"INSERT INTO {CLICKHOUSE_TABLE} (timestamp, source) VALUES",
            [{'timestamp': datetime.now(), 'source': msg.topic}]
        )
        print("Метаданные сохранены в ClickHouse")
    except Exception as e:
        print(f"Ошибка обработки сообщения: {str(e)}")

client = mqtt.Client()
client.connect(MQTT_BROKER, 1883)
client.subscribe(MQTT_TOPIC)
client.on_message = on_message
print("Ожидание изображений...")
client.loop_forever()