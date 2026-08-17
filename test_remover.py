import os
import cv2
import numpy as np
from remover import WatermarkRemoverWorker

def generate_test_video(path="test_input.mp4"):
    """
    Generates a 3-second 720x1280 test video with a moving colorful circle
    and a static white "Dola AI" watermark at the bottom right.
    """
    print(f"Generating test video: {path}...")
    width, height = 720, 1280
    fps = 30
    duration = 3  # seconds
    total_frames = duration * fps
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
    
    if not writer.isOpened():
        raise RuntimeError("Failed to open test video writer.")
        
    for frame_idx in range(total_frames):
        # Create a moving background pattern (gradient + moving circle)
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Color gradient background
        for y in range(height):
            # Vertically interpolate color from dark blue to dark violet
            r = int(20 + 30 * (y / height))
            g = int(20 + 10 * (y / height))
            b = int(40 + 60 * (y / height))
            frame[y, :] = [b, g, r] # OpenCV BGR format
            
        # Draw a bright moving circle that passes through the watermark area
        # Watermark will be near bottom right (x=500-690, y=1170-1220)
        # Circle starts top-left and moves diagonally to bottom-right
        cx = int((frame_idx / total_frames) * width * 1.1)
        cy = int((frame_idx / total_frames) * height * 1.1)
        cv2.circle(frame, (cx, cy), 120, (0, 165, 255), -1)  # Orange circle
        
        # Add some smaller particles
        cv2.circle(frame, (width - cx, cy), 40, (180, 50, 180), -1)  # Purple circle
        
        # Add the watermark text "Dola AI" at the bottom right
        # We will write in white text (255, 255, 255)
        # Bottom-right position: x=520, y=1200
        font = cv2.FONT_HERSHEY_DUPLEX
        text = "Dola AI"
        font_scale = 1.2
        thickness = 2
        
        # Draw text shadow (black) slightly offset
        cv2.putText(frame, text, (522, 1202), font, font_scale, (30, 30, 30), thickness + 1, cv2.LINE_AA)
        # Draw text (white)
        cv2.putText(frame, text, (520, 1200), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        
        writer.write(frame)
        
    writer.release()
    print("Test video generated successfully.")

def test_watermark_removal():
    input_file = "test_input.mp4"
    output_file = "test_output.mp4"
    
    # 1. Generate test video if not exists
    if not os.path.exists(input_file):
        generate_test_video(input_file)
        
    # 2. Define the Watermark ROI
    # For a 720x1280 video, "Dola AI" text at (520, 1200) fits inside (500, 1150, 200, 70)
    roi = {
        "x": 500,
        "y": 1150,
        "width": 200,
        "height": 70,
        "ref_width": 720,
        "ref_height": 1280
    }
    
    print("\nStarting Watermark Removal processing via remover.py...")
    # Initialize worker and call run synchronously
    worker = WatermarkRemoverWorker(
        video_paths=[input_file],
        output_dir=output_file,
        roi=roi,
        threshold=200,
        dilation_size=2,
        inpaint_radius=4,
        inpaint_method="Telea",
        is_batch=False
    )
    
    # Hook up simple print callbacks
    worker.progress_changed.connect(lambda pct: print(f"Progress: {pct}%"))
    worker.status_changed.connect(lambda msg: print(f"Status: {msg}"))
    
    def on_finished(success, message):
        print(f"Finished. Success: {success}, Message: {message}")
        if success:
            assert os.path.exists(output_file), "Output file should exist upon success!"
            print(f"Success! Output video written to {output_file}")
            # Verify file size is positive
            size = os.path.getsize(output_file)
            print(f"Output video file size: {size} bytes")
            
    worker.finished.connect(on_finished)
    
    # Run synchronously
    worker.run()

if __name__ == "__main__":
    test_watermark_removal()
