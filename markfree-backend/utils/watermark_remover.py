import cv2
import numpy as np
import os

def remove_watermark(input_video_path, output_video_path, is_portrait=None):
    """
    Removes watermarks from a video by inpainting specified regions using OpenCV.
    
    Args:
    - input_video_path (str): Path to the input video file.
    - output_video_path (str): Path to save the output video file.
    - is_portrait (bool, optional): If True, assumes portrait; else landscape. Auto-detects if None.
    
    Returns: bool - True if successful, False otherwise.
    """
    # Open the input video
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        raise ValueError(f"Error opening video file: {input_video_path}")

    # Get video properties
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Auto-detect orientation
    if is_portrait is None:
        is_portrait = frame_height > frame_width
        print(f"Detected {'portrait' if is_portrait else 'landscape'} orientation ({frame_width}x{frame_height})")
    else:
        print(f"Using forced {'portrait' if is_portrait else 'landscape'} orientation")

    # Define regions (scale proportionally if resolution differs, but for simplicity, use fixed for common res)
    if is_portrait:
        regions = [
            {'x': 23, 'y': 61, 'width': 175, 'height': 80},    # Top-left
            {'x': 552, 'y': 592, 'width': 175, 'height': 80},  # Middle-right
            {'x': 23, 'y': 1031, 'width': 175, 'height': 80}   # Bottom-left
        ]
    else:
        regions = [
            {'x': 45, 'y': 50, 'width': 230, 'height': 100},    # Top-left
            {'x': 1025, 'y': 300, 'width': 230, 'height': 100}, # Middle-right
            {'x': 45, 'y': 580, 'width': 230, 'height': 100}    # Bottom-left
        ]

    # Define codec and create VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

    if not out.isOpened():
        raise ValueError(f"Error creating output video file: {output_video_path}")

    print(f"Processing video: {total_frames} frames at {fps} FPS")

    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % 100 == 0:
            print(f"Processed {frame_count}/{total_frames} frames")

        # Create mask
        mask = np.zeros((frame_height, frame_width), dtype=np.uint8)

        for region in regions:
            x, y, w, h = region['x'], region['y'], region['width'], region['height']
            x = max(0, min(x, frame_width - 1))
            y = max(0, min(y, frame_height - 1))
            w = min(w, frame_width - x)
            h = min(h, frame_height - y)
            mask[y:y+h, x:x+w] = 255

        # Inpaint
        inpainted_frame = cv2.inpaint(frame, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

        # Write frame
        out.write(inpainted_frame)

    # Cleanup
    cap.release()
    out.release()
    cv2.destroyAllWindows()

    print(f"Processing complete. Output saved to: {output_video_path}")
    return True