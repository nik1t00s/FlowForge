# FlowForge

## Overview

FlowForge is a scalable image processing pipeline designed to efficiently receive, process, and analyze image data from multiple sources including MQTT messages, RTSP video streams, and batch image processing. The system leverages a microservice architecture to provide real-time image processing capabilities with persistent storage and visualization.

## Components

### MQTT Broker (Mosquitto)
- Acts as a message broker for receiving images through pub/sub messaging
- Handles all incoming image data through the `images/raw` topic
- Provides lightweight and reliable messaging for IoT and image streaming applications

### Python Microservice
- Subscribes to the MQTT broker to receive incoming images
- Processes RTSP video streams in real-time with parallel frame processing
- Batch processes static images from directories
- Processes images (resizing to 640x360) and calculates brightness metrics
- Extracts and stores metadata in ClickHouse via SQLite cache
- Built with OpenCV for image processing capabilities
- Multi-threaded architecture for optimal performance

### ClickHouse Database
- High-performance columnar database for storing image metadata
- Optimized for analytical queries on large datasets
- Stores timestamp and source information for each processed image

### RTSP Simulator
- Provides RTSP streaming server for testing video processing
- Supports multiple concurrent streams
- API and metrics endpoints for monitoring
- Configurable stream parameters

### Grafana Dashboard
- Provides visualization of image processing metrics
- Connects directly to ClickHouse as a data source
- Enables real-time monitoring and historical analysis of image data flow

## Prerequisites

- Docker and Docker Compose
- Git
- At least 4GB of RAM for running all services
- Port availability: 1883 (MQTT), 8123 (ClickHouse), 3000 (Grafana), 8554 (RTSP)

## Installation & Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/FlowForge.git
   cd FlowForge
   ```

2. Start the services using Docker Compose:
   ```
   docker-compose up -d
   ```

3. Verify that all services are running:
   ```
   docker-compose ps
   ```

4. Access Grafana at http://localhost:3000 (default credentials: admin/admin)

## Usage

### Publishing Images to MQTT

You can publish images to the MQTT broker using any MQTT client with the following parameters:
- Broker: localhost:1883
- Topic: images/raw
- Payload: Binary image data

Example using mosquitto_pub:
```
mosquitto_pub -h localhost -p 1883 -t images/raw -f /path/to/your/image.jpg
```

### Viewing Data in Grafana

1. Log in to Grafana at http://localhost:3000
2. Navigate to Dashboards
3. Select the FlowForge dashboard to view image processing metrics
4. Use the time range selector to analyze historical data

### Accessing ClickHouse Directly

You can query the image metadata directly using the ClickHouse client:
```
curl http://localhost:8123/play -d "SELECT * FROM images_metadata LIMIT 10"
```

### Testing RTSP Functionality

1. Create a test video (optional):
   ```
   python3 create_test_video.py
   ```

2. Test RTSP stream connectivity:
   ```
   python3 test_rtsp.py
   ```

3. Check RTSP server status:
   ```
   curl http://localhost:9997/v1/config
   curl http://localhost:9997/v1/paths
   ```

4. Monitor processing statistics in the Python service logs:
   ```
   docker-compose logs -f python-service
   ```

## Features

### Multi-Source Processing
- **MQTT Images**: Real-time processing of images received via MQTT
- **RTSP Streams**: Parallel processing of video frames from RTSP streams
- **Batch Processing**: Automatic processing of images from directories

### Performance Optimizations
- **Parallel Processing**: Multi-threaded frame and image processing
- **Queue Management**: Frame dropping to prevent memory overflow
- **SQLite Caching**: Local caching before ClickHouse insertion
- **Brightness Filtering**: Skip processing of dark/low-quality images

### Monitoring & Observability
- **Processing Statistics**: Real-time metrics for all processing pipelines
- **Health Checks**: Service health monitoring for all components
- **Resource Limits**: Docker resource constraints to prevent system overload

## Environment Variables

The Python microservice supports the following environment variables:

- `RTSP_URL`: RTSP stream URL to process (default: rtsp://rtsp-simulator:8554/test)
- `MQTT_HOST`: MQTT broker hostname (default: mqtt-broker)
- `MQTT_PORT`: MQTT broker port (default: 1883)
- `CLICKHOUSE_HOST`: ClickHouse hostname (default: clickhouse-db)
- `CLICKHOUSE_PORT`: ClickHouse port (default: 9000)
- `PYTHONUNBUFFERED`: Python output buffering (default: 1)

## Troubleshooting

### RTSP Connection Issues
1. Check if RTSP simulator is running: `docker-compose ps rtsp-simulator`
2. Verify RTSP server health: `curl http://localhost:9997/v1/config`
3. Test stream manually: `python3 test_rtsp.py`

### Performance Issues
1. Monitor resource usage: `docker stats`
2. Check processing statistics in logs: `docker-compose logs python-service`
3. Adjust worker threads by modifying the Python service code

### Database Issues
1. Check ClickHouse health: `curl http://localhost:8123/ping`
2. Verify data insertion: `curl 'http://localhost:8123/' -d 'SELECT COUNT(*) FROM images_metadata'`

## License

This project is licensed under the terms included in the [LICENSE](LICENSE) file.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
