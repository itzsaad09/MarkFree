# api/index.py
from flask import Flask, request, jsonify
import os, tempfile, uuid, traceback, requests
from utils.watermark_remover import remove_watermark

app = Flask(__name__)

BLOB_URL   = "https://blob.vercel-storage.com"
BLOB_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN")
if not BLOB_TOKEN:
    raise RuntimeError("BLOB_READ_WRITE_TOKEN env var missing")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"msg": "MarkFree API – POST /process with video"})

@app.route("/process", methods=["POST"])
def process_video():
    try:
        if "video" not in request.files:
            return jsonify({"error": "No video file"}), 400

        file = request.files["video"]
        unique = str(uuid.uuid4())

        # ---- 1. Upload to Vercel Blob ----
        blob_path = f"uploads/{unique}_{file.filename}"
        upload_url = f"{BLOB_URL}/upload?token={BLOB_TOKEN}"
        files = {"file": (blob_path, file.stream, file.content_type)}
        r = requests.post(upload_url, files=files)
        r.raise_for_status()
        input_blob_url = r.json()["url"]   # signed download URL

        # ---- 2. Download into /tmp ----
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_in:
            tmp_in_path = tmp_in.name
            tmp_in.write(requests.get(input_blob_url).content)

        # ---- 3. Process with OpenCV ----
        tmp_out_path = tmp_in_path.replace(".mp4", "_out.mp4")
        remove_watermark(tmp_in_path, tmp_out_path)

        # ---- 4. Upload processed file ----
        out_blob_path = f"processed/{unique}_processed.mp4"
        with open(tmp_out_path, "rb") as f:
            files = {"file": (out_blob_path, f, "video/mp4")}
            r2 = requests.post(upload_url, files=files)
            r2.raise_for_status()
            out_url = r2.json()["url"]

        # ---- 5. Cleanup ----
        os.unlink(tmp_in_path)
        os.unlink(tmp_out_path)

        return jsonify({
            "message": "Done",
            "download_url": out_url,
            "extension": "mp4"
        })

    except Exception as e:
        print("=== ERROR ===")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500