from flask import Flask, request, jsonify
import os
import tempfile
import uuid
from utils.watermark_remover import remove_watermark
import requests  # For Vercel Blob API

app = Flask(__name__)

# Vercel Blob config (get your token from Vercel dashboard > Storage > Blob > Connect)
BLOB_URL = "https://blob.vercel-storage.com"  # Public endpoint
YOUR_BLOB_TOKEN = os.environ.get("BLOB_TOKEN")  # Set in Vercel env vars

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "MarkFree API - Upload a video to /process"})

@app.route("/process", methods=["POST"])
def process_video():
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.content_type.startswith("video/"):
        return jsonify({"error": "Invalid file type. Please upload a video."}), 400

    try:
        # Step 1: Upload to Vercel Blob (async-friendly for large files)
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        input_blob_path = f"uploads/{unique_id}_{file.filename}"
        
        # Upload via Vercel API (requires BLOB_TOKEN env var)
        upload_url = f"{BLOB_URL}/upload?token={YOUR_BLOB_TOKEN}"
        files = {"file": (input_blob_path, file.stream, file.content_type)}
        response = requests.post(upload_url, files=files)
        if response.status_code != 200:
            return jsonify({"error": "Failed to upload to storage"}), 500
        
        input_url = response.json().get("url")  # Signed URL for download

        # Step 2: Download to temp file (in serverless /tmp)
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_input:
            temp_input_path = temp_input.name
            temp_input.close()
            input_response = requests.get(input_url)
            with open(temp_input_path, "wb") as f:
                f.write(input_response.content)

        # Step 3: Process with OpenCV
        output_temp_path = temp_input_path.replace(".mp4", "_processed.mp4")
        success = remove_watermark(temp_input_path, output_temp_path)

        if not success:
            os.unlink(temp_input_path)
            return jsonify({"error": "Processing failed"}), 500

        # Step 4: Upload processed video to Blob
        output_blob_path = f"processed/{unique_id}_processed.mp4"
        with open(output_temp_path, "rb") as f:
            files = {"file": (output_blob_path, f, "video/mp4")}
            upload_response = requests.post(upload_url, files=files)
            if upload_response.status_code != 200:
                os.unlink(temp_input_path)
                os.unlink(output_temp_path)
                return jsonify({"error": "Failed to store processed video"}), 500

        processed_url = upload_response.json().get("url")  # Signed download URL

        # Cleanup temp files
        os.unlink(temp_input_path)
        os.unlink(output_temp_path)

        return jsonify({
            "message": "Processing complete",
            "download_url": processed_url,
            "extension": "mp4"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)