# FlowForge

## Overview

FlowForge is a scalable image processing pipeline designed to efficiently receive, process, and analyze image data. The system leverages a microservice architecture to provide real-time image processing capabilities with persistent storage and visualization.

## Components

### MQTT Broker (Mosquitto)
- Acts as a message broker for receiving images through pub/sub messaging
- Handles all incoming image data through the `images/raw` topic
- Provides lightweight and reliable messaging for IoT and image streaming applications

### Python Microservice
- Subscribes to the MQTT broker to receive incoming images
- Processes images (resizing to 640x360)
- Extracts and stores metadata in ClickHouse
- Built with OpenCV for image processing capabilities

### ClickHouse Database
- High-performance columnar database for storing image metadata
- Optimized for analytical queries on large datasets
- Stores timestamp and source information for each processed image

### Grafana Dashboard
- Provides visualization of image processing metrics
- Connects directly to ClickHouse as a data source
- Enables real-time monitoring and historical analysis of image data flow

## Prerequisites

- Docker and Docker Compose
- Git
- At least 4GB of RAM for running all services
- Port availability: 1883 (MQTT), 8123 (ClickHouse), 3000 (Grafana)

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

## License

This project is licensed under the terms included in the [LICENSE](LICENSE) file.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
