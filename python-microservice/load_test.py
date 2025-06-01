import paho.mqtt.client as mqtt
import time
import os

client = mqtt.Client()
client.connect("mosquitto", 1883)

for i in range(1000):
    # Исправленный синтаксис f-строки
    file_path = f"/app/test_images/image_{i % 10}.jpg"
    
    if not os.path.exists(file_path):
        print(f"Файл не найден: {file_path}")
        continue
        
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        print(f"Пустой файл: {file_path}")
        continue
        
    with open(file_path, "rb") as f:
        image_data = f.read()
        client.publish("images/raw", image_data)
        print(f"Отправлено изображение {i+1}/1000")
        time.sleep(0.01)
        
client.disconnect()