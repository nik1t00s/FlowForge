import paho.mqtt.client as mqtt
import time
import os

client = mqtt.Client()
client.connect("mosquitto", 1883)

for i in range(1000):

    file_path = f"/app/test_images/image_{i % 10}.jpg"
    
    # Проверить существование файла
    if not os.path.exists(file_path):
        print(f"Файл не найден: {file_path}")
        continue
        
    # Проверить размер файла
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        print(f"Пустой файл: {file_path}")
        continue

    with open(f"/app/test_images/image_{i % 10}.jpg", "rb") as f:
        client.publish("images/raw", f.read())
    print(f"Отправлено изображение {i+1}/1000")
    time.sleep(0.01)  # Имитация сетевого ограничения

client.disconnect()