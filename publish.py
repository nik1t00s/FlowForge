import paho.mqtt.client as mqtt
import time

broker = "localhost"
topic = "images/raw"

client = mqtt.Client()
client.connect(broker, 1883)

with open("test_images/test_image.jpg", "rb") as f:
    image_data = f.read()

client.publish(topic, image_data)
print("Изображение отправлено")
time.sleep(2)
client.disconnect()