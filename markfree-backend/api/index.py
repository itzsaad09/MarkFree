import cv2
import numpy as np
from flask import Flask, request, send_file, jsonify
import os
import tempfile
import json

app = Flask(__name__)

def remove_watermark(input_path, output_path, regions):
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Create mask template
    mask = np.zeros((height, width), dtype=np.uint8)

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Reset mask per frame (for dynamic watermarks if needed)
        mask.fill(0)

        # Draw watermark regions on mask
        for region in regions:
            x, y, w, h = int(region['x']), int(region['y']), int(region['width']), int(region['height'])
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

        # Inpaint using Telea (fast) or Navier-Stokes (better quality)
        inpainted = cv2.inpaint(frame, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        out.write(inpainted)

        frame_count += 1
        if frame_count % 30 == 0:  # Log progress every 30 frames
            print(f"Processed {frame_count} frames...")

    cap.release()
    out.release()
    print(f"Processing complete: {frame_count} frames")

@app.route('/')
def home():
    return "MarkFree backend is running! POST to /remove-watermark"

@app.route('/remove-watermark', methods=['POST'])
def remove_watermark_api():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400

    file = request.files['video']
    regions_str = request.form.get('regions')
    
    if not regions_str:
        return jsonify({'error': 'Regions required'}), 400

    try:
        regions = json.loads(regions_str)  # Parse JSON regions
    except:
        return jsonify({'error': 'Invalid regions format'}), 400

    # Save uploaded video to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_in:
        file.save(tmp_in.name)
        input_path = tmp_in.name

    output_path = tempfile.mktemp(suffix='_clean.mp4')

    try:
        remove_watermark(input_path, output_path, regions)
        return send_file(output_path, as_attachment=True, download_name='clean_video.mp4')
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Cleanup
        if os.path.exists(input_path):
            os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)

# Vercel requires this for WSGI
if __name__ == "__main__":
    app.run()