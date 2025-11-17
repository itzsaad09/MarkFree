# api/remove_watermark.py
import os
import io
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import cv2
import torch
from PIL import Image
import imageio
from moviepy.editor import VideoFileClip
import tempfile

# ------------------- Load LaMA Model -------------------
model_path = os.path.join(os.path.dirname(__file__), "../models/big-lama.pt")
device = torch.device("cpu")

print("Loading LaMA model...")
from lama_cleaner.model.lama import LaMA
model = LaMA(device=device)
model.load_state_dict(torch.load(model_path, map_location=device))
model.eval()
print("LaMA model loaded successfully!")

app = FastAPI()

# ------------------- Watermark Regions (Adjust These!) -------------------
# TikTok/Instagram typical positions
REGIONS = [
    (20, 60, 180, 90),     # Top-left logo
    (20, -150, 180, 90),   # Bottom-left (negative = from bottom)
    (500, 500, 200, 100),  # Middle-right floating watermark
]

def create_mask(frame_h, frame_w):
    mask = np.zeros((frame_h, frame_w), dtype=np.uint8)
    for x, y, w, h in REGIONS:
        if y < 0: y = frame_h + y  # negative = from bottom
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(frame_w, x + w)
        y2 = min(frame_h, y + h)
        mask[y1:y2, x1:x2] = 255
    return mask

def lama_inpaint(frame_bgr, mask):
    h, w = frame_bgr.shape[:2]
    img = torch.from_numpy(frame_bgr).float().permute(2,0,1).unsqueeze(0) / 255.0
    mask_t = torch.from_numpy(mask).float().unsqueeze(0).unsqueeze(0)
    img = img.to(device)
    mask_t = mask_t.to(device)
    with torch.no_grad():
        inpainted = model(img, mask_t)
    result = (inpainted[0].permute(1,2,0).cpu().numpy() * 255).astype(np.uint8)
    return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)

# ------------------- Main Endpoint -------------------
@app.post("/remove_watermark")
async def remove_watermark(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('.mp4', '.mov', '.webm', '.avi')):
        raise HTTPException(400, "Unsupported format")

    content = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_in:
        tmp_in.write(content)
        input_path = tmp_in.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_out:
        output_path = tmp_out.name

    try:
        clip = VideoFileClip(input_path)
        fps = clip.fps
        mask = create_mask(clip.h, clip.w)

        def process_frame(get_frame, t):
            frame = get_frame(t)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            cleaned = lama_inpaint(frame_bgr, mask)
            return cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB)

        new_clip = clip.fl(process_frame, apply_to='video')
        new_clip.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            threads=2,
            preset="medium"
        )

        with open(output_path, "rb") as f:
            result = f.read()

        return StreamingResponse(
            io.BytesIO(result),
            media_type="video/mp4",
            headers={"Content-Disposition": f"attachment; filename=clean_{file.filename}"}
        )

    finally:
        for p in [input_path, output_path]:
            if os.path.exists(p):
                os.unlink(p)