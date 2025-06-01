import sqlite3
import threading
import paho.mqtt.client as mqtt
import cv2
import numpy as np
from datetime import datetime
from clickhouse_driver import Client
import time
import os
import glob
from concurrent.futures import ThreadPoolExecutor
import queue
import logging
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RTSPProcessor:
    """RTSP stream processor with parallel frame handling"""
    
    def __init__(self, rtsp_url: str, max_workers: int = 2):
        self.rtsp_url = rtsp_url
        self.max_workers = max_workers
        self.frame_queue = queue.Queue(maxsize=30)
        self.running = False
        self.cap = None
        self.stats = {
            'frames_captured': 0,
            'frames_processed': 0,
            'processing_errors': 0
        }
        
    def start(self):
        """Start RTSP processing"""
        self.running = True
        
        # Start capture thread
        capture_thread = threading.Thread(target=self._capture_frames, daemon=True)
        capture_thread.start()
        
        # Start processing threads
        for i in range(self.max_workers):
            processing_thread = threading.Thread(target=self._process_frames, daemon=True)
            processing_thread.start()
        
        logger.info(f"Started RTSP processor for {self.rtsp_url}")
    
    def stop(self):
        """Stop RTSP processing"""
        self.running = False
        if self.cap:
            self.cap.release()
        logger.info("Stopped RTSP processor")
    
    def _capture_frames(self):
        """Capture frames from RTSP stream"""
        self.cap = cv2.VideoCapture(self.rtsp_url)
        
        if not self.cap.isOpened():
            logger.error(f"Failed to open RTSP stream: {self.rtsp_url}")
            return
        
        logger.info(f"Connected to RTSP stream: {self.rtsp_url}")
        
        frame_number = 0
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to read frame from RTSP stream")
                time.sleep(0.1)
                continue
            
            frame_info = {
                'frame_number': frame_number,
                'timestamp': datetime.now(),
                'source': self.rtsp_url
            }
            
            try:
                self.frame_queue.put_nowait((frame, frame_info))
                self.stats['frames_captured'] += 1
            except queue.Full:
                # Drop frame if queue is full
                pass
            
            frame_number += 1
            
        self.cap.release()
    
    def _process_frames(self):
        """Process frames from queue"""
        while self.running:
            try:
                frame, frame_info = self.frame_queue.get(timeout=1.0)
                self._process_single_frame(frame, frame_info)
                self.stats['frames_processed'] += 1
                self.frame_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing frame: {e}")
                self.stats['processing_errors'] += 1
    
    def _process_single_frame(self, frame: np.ndarray, frame_info: dict):
        """Process a single frame like MQTT image"""
        try:
            # Resize frame
            resized = cv2.resize(frame, (640, 360))
            
            # Calculate brightness
            hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
            brightness = np.mean(hsv[:,:,2])
            
            # Filter by brightness
            if brightness < BRIGHTNESS_THRESHOLD:
                return
            
            # Save to SQLite
            timestamp = frame_info['timestamp']
            with get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO metadata (timestamp, source, brightness) VALUES (?, ?, ?)",
                    (timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"), frame_info['source'], float(brightness))
                )
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error processing RTSP frame: {e}")
    
    def get_stats(self) -> dict:
        """Get processing statistics"""
        return self.stats.copy()

class ImageBatchProcessor:
    """Parallel processor for static images"""
    
    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.stats = {
            'images_processed': 0,
            'processing_errors': 0
        }
    
    def process_directory(self, directory: str) -> int:
        """Process all images in a directory"""
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.webp']
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(directory, ext)))
        
        logger.info(f"Found {len(image_files)} images to process")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._process_image, filepath) for filepath in image_files]
            
            for future in futures:
                try:
                    future.result()
                    self.stats['images_processed'] += 1
                except Exception as e:
                    logger.error(f"Error processing image: {e}")
                    self.stats['processing_errors'] += 1
        
        return len(image_files)
    
    def _process_image(self, filepath: str):
        """Process a single image file"""
        try:
            # Read image
            img = cv2.imread(filepath)
            if img is None:
                logger.warning(f"Could not read image: {filepath}")
                return
            
            # Resize image
            resized = cv2.resize(img, (640, 360))
            
            # Calculate brightness
            hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
            brightness = np.mean(hsv[:,:,2])
            
            # Filter by brightness
            if brightness < BRIGHTNESS_THRESHOLD:
                return
            
            # Save to SQLite
            timestamp = datetime.now()
            with get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO metadata (timestamp, source, brightness) VALUES (?, ?, ?)",
                    (timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"), filepath, float(brightness))
                )
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error processing image {filepath}: {e}")
    
    def get_stats(self) -> dict:
        """Get processing statistics"""
        return self.stats.copy()

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

# Global processors
rtsp_processor = None
image_processor = None

def initialize_processors():
    """Initialize RTSP and image processors"""
    global rtsp_processor, image_processor
    
    # Initialize image batch processor
    image_processor = ImageBatchProcessor(max_workers=2)
    
    # Check for RTSP URL from environment
    rtsp_url = os.getenv('RTSP_URL')
    if rtsp_url:
        logger.info(f"Starting RTSP processor for: {rtsp_url}")
        rtsp_processor = RTSPProcessor(rtsp_url, max_workers=2)
        rtsp_processor.start()
    
    # Process existing images in test_images directory
    test_images_dir = "/app/test_images"
    if os.path.exists(test_images_dir):
        logger.info(f"Processing existing images in {test_images_dir}")
        image_count = image_processor.process_directory(test_images_dir)
        logger.info(f"Processed {image_count} images from directory")

def cleanup_processors():
    """Cleanup processors on shutdown"""
    global rtsp_processor
    if rtsp_processor:
        rtsp_processor.stop()

def print_stats():
    """Print processing statistics periodically"""
    while True:
        time.sleep(60)  # Every minute
        try:
            if rtsp_processor:
                stats = rtsp_processor.get_stats()
                logger.info(f"RTSP Stats: {stats}")
            
            if image_processor:
                stats = image_processor.get_stats()
                logger.info(f"Image Processor Stats: {stats}")
        except Exception as e:
            logger.error(f"Error printing stats: {e}")

# Запуск фонового потока
threading.Thread(target=background_sender, daemon=True).start()

# Initialize processors
initialize_processors()

# Start stats thread
threading.Thread(target=print_stats, daemon=True).start()

try:
    # MQTT Клиент
    client = mqtt.Client()
    client.connect(MQTT_BROKER, 1883)
    client.subscribe(MQTT_TOPIC)
    client.on_message = on_message
    
    logger.info("Starting MQTT client loop...")
    client.loop_forever()
    
except KeyboardInterrupt:
    logger.info("Shutting down...")
finally:
    cleanup_processors()
