# api/remove_watermark.py
import os
import io
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import cv2
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from pydub import AudioSegment
import imageio_ffmpeg as iioff
from PIL import Image

# ------------------- CONFIG -------------------
# Crop regions (adjust for your videos)
PORTRAIT_CROP = dict(x1=50, y1=100, x2=50, y2=150)   # left, top, right, bottom
LANDSCAPE_CROP = dict(x1=60, y1=60, x2=60, y2=60)

# LaMA model path
LAMA_MODEL_PATH = os.path.join(os.path.dirname(__file__), "../models/big-lama.pt")

# ------------------- FASTAPI APP -------------------
app = FastAPI()

# ------------------- LaMA Inpainting (Optional) -------------------
lama_model = None
try:
    from lama_cleaner.model_manager import ModelManager
    from lama_cleaner.schema import Config as LamaConfig
    model_manager = ModelManager(name="big-lama", device="cpu")
    model_manager.load_model(LAMA_MODEL_PATH)
    lama_model = model_manager.model
    print("LaMA model loaded")
except Exception as e:
    print("LaMA not available (optional):", e)

def inpaint_with_lama(frame_bgr, mask):
    if lama_model is None:
        return frame_bgr
    import torch
    img = torch.from_numpy(frame_bgr).float().permute(2,0,1).unsqueeze(0) / 255.0
    mask_t = torch.from_numpy(mask).float().unsqueeze(0).unsqueeze(0) / 255.0
    inpainted = lama_model(img, mask_t)
    result = (inpainted[0].permute(1,2,0).cpu().numpy() * 255).astype(np.uint8)
    return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)

# ------------------- CORE PROCESSING -------------------
def process_video(video_bytes: bytes) -> bytes:
    # --- Read video ---
    reader = imageio.get_reader(io.BytesIO(video_bytes), 'ffmpeg')
    fps = reader.get_meta_data()['fps']
    frames = [frame for frame in reader]
    width, height = frames[0].shape[1], frames[0].shape[0]
    is_portrait = height > width

    # --- Crop ---
    crop = PORTRAIT_CROP if is_portrait else LANDSCAPE_CROP
    cropped_frames = []
    for frame in frames:
        h, w = frame.shape[:2]
        x1 = crop['x1']
        y1 = crop['y1']
        x2 = w - crop['x2']
        y2 = h - crop['y2']
        cropped = frame[y1:y2, x1:x2]
        cropped_frames.append(cropped)

    # --- Optional: LaMA fallback on cropped regions ---
    # (Skip for speed; enable if watermark still visible)
    # final_frames = [inpaint_with_lama(f, mask) for f in cropped_frames]

    # --- Reconstruct video ---
    clip = ImageSequenceClip(cropped_frames, fps=fps)
    video_io = io.BytesIO()
    clip.write_videofile(video_io, fps=fps, codec='libx264', audio=False)
    video_io.seek(0)

    # --- Add original audio ---
    audio = AudioSegment.from_file(io.BytesIO(video_bytes))
    audio.export(video_io, format="mp3")
    video_io.seek(0)

    # Combine video + audio
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
        tmp_video.write(video_io.read())
        tmp_video_path = tmp_video.name
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
        tmp_audio.write(audio.export(format="mp3").read())
        tmp_audio_path = tmp_audio.name

    output_path = tempfile.mktemp(suffix=".mp4")
    subprocess.run([
        "ffmpeg", "-i", tmp_video_path, "-i", tmp_audio_path,
        "-c:v", "copy", "-c:a", "aac", output_path, "-y"
    ], check=True, capture_output=True)

    with open(output_path, "rb") as f:
        result = f.read()

    # Cleanup
    for p in [tmp_video_path, tmp_audio_path, output_path]:
        os.unlink(p)

    return result

# ------------------- API ENDPOINT -------------------
@app.post("/remove_watermark")
async def remove_watermark(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('.mp4', '.mov', '.webm')):
        raise HTTPException(400, "Invalid video format")

    video_bytes = await file.read()
    try:
        processed = process_video(video_bytes)
        return StreamingResponse(
            io.BytesIO(processed),
            media_type="video/mp4",
            headers={"Content-Disposition": f"attachment; filename=clean_{file.filename}"}
        )
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {str(e)}")