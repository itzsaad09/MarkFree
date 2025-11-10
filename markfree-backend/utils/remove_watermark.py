import cv2
import numpy as np
from flask import Flask, request, send_file, jsonify
import os
import tempfile

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

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Reset mask
        mask.fill(0)

        # Draw watermark regions on mask
        for region in regions:
            x, y, w, h = region['x'], region['y'], region['width'], region['height']
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

        # Inpaint using Telea (fast) or Navier-Stokes (better quality)
        inpainted = cv2.inpaint(frame, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        out.write(inpainted)

    cap.release()
    out.release()

@app.route('/remove-watermark', methods=['POST'])
def remove_watermark_api():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400

    file = request.files['video']
    regions = request.form.get('regions')
    
    if not regions:
        return jsonify({'error': 'Regions required'}), 400

    try:
        regions = eval(regions)  # or use json.loads if sent as JSON
    except:
        return jsonify({'error': 'Invalid regions format'}), 400

    # Save uploaded video
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_in:
        file.save(tmp_in.name)
        input_path = tmp_in.name

    output_path = tempfile.mktemp(suffix='_clean.mp4')

    try:
        remove_watermark(input_path, output_path, regions)
        return send_file(output_path, as_attachment=True, download_name='clean_video.mp4')
    finally:
        # Cleanup
        if os.path.exists(input_path):
            os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)