"""
Simple RTSP test script to verify functionality
"""

import cv2
import time
import sys

def test_rtsp_stream(rtsp_url: str, duration: int = 10):
    """Test RTSP stream connection and frame reading"""
    
    print(f"Testing RTSP stream: {rtsp_url}")
    
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        print("❌ Failed to open RTSP stream")
        return False
    
    print("✅ Successfully connected to RTSP stream")
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            ret, frame = cap.read()
            
            if not ret:
                print("❌ Failed to read frame")
                break
            
            frame_count += 1
            
            if frame_count % 30 == 0:  # Print every 30 frames
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                print(f"Frames: {frame_count}, FPS: {fps:.2f}, Resolution: {frame.shape[:2]}")
        
        elapsed = time.time() - start_time
        avg_fps = frame_count / elapsed if elapsed > 0 else 0
        
        print(f"\n📊 Test Results:")
        print(f"   Duration: {elapsed:.2f} seconds")
        print(f"   Total frames: {frame_count}")
        print(f"   Average FPS: {avg_fps:.2f}")
        
        return frame_count > 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return True
    
    finally:
        cap.release()
        print("🔒 Stream closed")

def main():
    # Test local RTSP server
    rtsp_url = "rtsp://localhost:8554/test"
    
    if len(sys.argv) > 1:
        rtsp_url = sys.argv[1]
    
    print("🎥 RTSP Stream Test")
    print("==================")
    
    success = test_rtsp_stream(rtsp_url, duration=10)
    
    if success:
        print("\n✅ RTSP test completed successfully!")
    else:
        print("\n❌ RTSP test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()

