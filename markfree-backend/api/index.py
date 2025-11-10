# api/index.py
from flask import Flask, request, jsonify
import os
import traceback

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"msg": "MarkFree API – POST /process with a video file"})

@app.route("/process", methods=["POST"])
def process_video():
    try:
        # 1. Basic checks
        if "video" not in request.files:
            return jsonify({"error": "Field 'video' missing"}), 400

        file = request.files["video"]
        if not file.filename:
            return jsonify({"error": "Empty filename"}), 400

        # 2. Show environment info (helps debugging)
        return jsonify({
            "filename": file.filename,
            "size_bytes": len(file.read()),
            "BLOB_READ_WRITE_TOKEN_set": bool(os.environ.get("BLOB_READ_WRITE_TOKEN")),
            "PYTHONPATH": os.getenv("PYTHONPATH", "not set")
        })

    except Exception as exc:
        # 3. Print full traceback to Vercel logs
        print("=== UNHANDLED EXCEPTION ===")
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500