import paho.mqtt.client as mqtt
import cv2
import numpy as np
from PIL import Image
from datetime import datetime
from clickhouse_driver import Client

MQTT_BROKER = "mosquitto"
MQTT_TOPIC = "images/raw"

CLICKHOUSE_HOST = "clickhouse"
CLICKHOUSE_TABLE = "images_metadata"

ch_client = Client(host=CLICKHOUSE_HOST)

ch_client.execute('''
CREATE TABLE IF NOT EXISTS images_metadata (
    timestamp DateTime DEFAULT now(),
    source String
) ENGINE = MergeTree()
ORDER BY timestamp
''')
print("Таблица images_metadata создана/проверена")

def on_message(client, userdata, msg):
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

    
client = mqtt.Client()
client.connect(MQTT_BROKER, 1883)
client.subscribe(MQTT_TOPIC)
client.on_message = on_message
print("Ожидание изображений...")
client.loop_forever()