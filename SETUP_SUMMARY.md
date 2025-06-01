# FlowForge RTSP and Parallel Processing Setup Summary

## What was Added/Modified

### ✅ Enhanced Python Microservice (`python-microservice/app.py`)

**New Classes Added:**
- `RTSPProcessor`: Handles RTSP video stream processing with parallel frame handling
- `ImageBatchProcessor`: Processes static images from directories in parallel

**Key Features:**
- **Multi-threaded RTSP processing**: Separate threads for frame capture and processing
- **Frame queue management**: Prevents memory overflow with automatic frame dropping
- **Batch image processing**: Automatically processes existing images in `/app/test_images`
- **Statistics tracking**: Real-time metrics for processed frames/images
- **Brightness filtering**: Skips processing dark/low-quality content
- **Graceful shutdown**: Proper cleanup of resources

### ✅ RTSP Simulator Configuration (`rtsp-config.yml`)

**Features:**
- RTSP server configuration for testing
- Multiple stream paths support
- API and metrics endpoints
- HLS streaming support

### ✅ Updated Docker Compose (`docker-compose.yml`)

**Added:**
- RTSP simulator service with proper health checks
- Environment variable `RTSP_URL` for Python service
- Additional ports for RTSP (8554), API (9997), metrics (9998), HLS (8888)

### ✅ Test Utilities

**`create_test_video.py`:**
- Creates test video files with moving patterns
- Useful for RTSP streaming tests

**`test_rtsp.py`:**
- Tests RTSP stream connectivity
- Measures frame rate and resolution
- Verifies stream health

### ✅ Updated Documentation (`README.md`)

**Added sections:**
- RTSP functionality testing
- Multi-source processing features
- Performance optimizations
- Environment variables
- Troubleshooting guide

## How to Use

### 1. Start the System
```bash
cd /home/nikita/Desktop/Projects/FlowForge
docker-compose up -d
```

### 2. Verify Services
```bash
# Check all services are running
docker-compose ps

# Check RTSP server
curl http://localhost:9997/v1/config

# Check ClickHouse
curl http://localhost:8123/ping
```

### 3. Monitor Processing
```bash
# View Python service logs (shows RTSP and image processing)
docker-compose logs -f python-service

# View processing statistics (printed every minute)
docker-compose logs python-service | grep "Stats:"
```

### 4. Test RTSP Functionality
```bash
# Test RTSP stream (requires opencv-python locally)
python3 test_rtsp.py

# Or test from within container
docker-compose exec python-service python test_rtsp.py
```

## Processing Pipeline Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  MQTT Images    │───▶│   Python Service │───▶│   SQLite Cache  │
└─────────────────┘    │                  │    └─────────────────┘
                       │  ┌─────────────┐ │             │
┌─────────────────┐    │  │   Parallel  │ │             ▼
│  RTSP Streams   │───▶│  │ Processing  │ │    ┌─────────────────┐
└─────────────────┘    │  │  Workers    │ │    │   ClickHouse    │
                       │  └─────────────┘ │    │    Database     │
┌─────────────────┐    │                  │    └─────────────────┘
│ Batch Images    │───▶│  Filter by       │             │
│ (test_images)   │    │  Brightness      │             ▼
└─────────────────┘    └──────────────────┘    ┌─────────────────┐
                                               │     Grafana     │
                                               │   Dashboard     │
                                               └─────────────────┘
```

## Performance Features

### 🚀 Parallel Processing
- **RTSP**: 2 worker threads per stream (configurable)
- **Batch Images**: 2 worker threads (configurable)
- **Frame Queue**: 30 frame buffer with automatic dropping

### 🔧 Resource Management
- **Memory Limits**: All services have Docker memory limits
- **CPU Limits**: Prevents single service from overwhelming system
- **Health Checks**: Automatic service restart on failure

### 📊 Monitoring
- **Real-time Stats**: Processing metrics every minute
- **Error Tracking**: Comprehensive error logging
- **Queue Status**: Frame buffer monitoring

## Error Handling

### ✅ Implemented
- RTSP connection retry logic
- Frame processing error isolation
- SQLite transaction safety
- Graceful service shutdown
- Memory overflow protection

### 🔍 Troubleshooting

**RTSP Issues:**
```bash
# Check RTSP server status
curl http://localhost:9997/v1/paths

# Test stream connectivity
python3 test_rtsp.py
```

**Performance Issues:**
```bash
# Monitor resource usage
docker stats

# Check processing statistics
docker-compose logs python-service | grep "Stats:"
```

**Database Issues:**
```bash
# Check ClickHouse health
curl http://localhost:8123/ping

# Query processed data
curl 'http://localhost:8123/' -d 'SELECT COUNT(*) FROM images_metadata'
```

## Next Steps

1. **Start the system**: `docker-compose up -d`
2. **Monitor logs**: `docker-compose logs -f python-service`
3. **Check Grafana**: http://localhost:3000 (admin/admin)
4. **Test RTSP**: `python3 test_rtsp.py` (if opencv available locally)
5. **Add test images**: Place images in `test_images/` directory

The system will automatically:
- Process any existing images in `test_images/`
- Connect to RTSP stream if available
- Handle MQTT image messages
- Store all processed metadata in ClickHouse
- Display metrics in Grafana

