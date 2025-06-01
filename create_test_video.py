#!/usr/bin/env python3
"""
Simple script to create a test video for RTSP streaming
"""

import cv2
import numpy as np
import os

def create_test_video(output_path: str, duration: int = 30, fps: int = 15):
    """Create a test video file with moving patterns"""
    
    # Ensure test_videos directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (640, 480))
    
    total_frames = duration * fps
    print(f"Creating test video with {total_frames} frames...")
    
    for frame_num in range(total_frames):
        # Create colorful moving pattern
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Moving circles
        center_x = int(320 + 200 * np.sin(frame_num * 0.05))
        center_y = int(240 + 100 * np.cos(frame_num * 0.03))
        
        cv2.circle(frame, (center_x, center_y), 50, (0, 255, 0), -1)
        cv2.circle(frame, (center_x - 100, center_y + 50), 30, (255, 0, 0), -1)
        cv2.circle(frame, (center_x + 100, center_y - 50), 40, (0, 0, 255), -1)
        
        # Add frame number text
        cv2.putText(frame, f'Frame: {frame_num}', (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = f'Time: {frame_num/fps:.1f}s'
        cv2.putText(frame, timestamp, (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        out.write(frame)
        
        if frame_num % 100 == 0:
            print(f"Progress: {frame_num}/{total_frames} frames")
    
    out.release()
    print(f"Created test video: {output_path}")

if __name__ == "__main__":
    create_test_video("./test_videos/sample.mp4", duration=60, fps=15)
    print("Test video created successfully!")

