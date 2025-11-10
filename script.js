document.addEventListener("DOMContentLoaded", () => {
  // Screen Containers
  const uploadContainer = document.getElementById("upload-container");
  const processingContainer = document.getElementById("processing-container");
  const resultsContainer = document.getElementById("results-container");

  // UI Elements
  const videoUpload = document.getElementById("videoUpload");
  const uploadButton = document.getElementById("uploadButton");
  const originalVideo = document.getElementById("originalVideo");
  const processedVideo = document.getElementById("processedVideo");
  const downloadButton = document.getElementById("downloadVideo");
  const processingStatus = document.getElementById("processing-status");
  const videoError = document.getElementById("videoError");
  const processedError = document.getElementById("processedError");

  // --- NEW: Elements for new features ---
  const uploadCard = document.getElementById("uploadCard");
  const processAnotherButton = document.getElementById("processAnotherButton");

  let processedBlob = null;
  let processedFileExtension = "webm";

  // --- Watermark Regions ---
  // NOTE: Coordinates are based on the video's ACTUAL resolution.

  // Regions for PORTRAIT videos (e.g., 720x1280)
  // The original hardcoded values seemed to be for a tall video.
  const portraitRegions = [
    { x: 23, y: 61, width: 175, height: 80 }, // Top-left
    { x: 552, y: 592, width: 175, height: 80 }, // Middle-right
    { x: 23, y: 1031, width: 175, height: 80 }, // Bottom-left
  ];

  // !!IMPORTANT!!: Regions for a LANDSCAPE video (e.g., 1280x720)
  // You MUST adjust these example coordinates for your landscape watermarks
  const landscapeRegions = [
    { x: 45, y: 50, width: 230, height: 100 }, // Example: Top-left
    { x: 1025, y: 300, width: 230, height: 100 }, // Example: Middle-right
    { x: 45, y: 580, width: 230, height: 100 }, // Example: Bottom-left
    // Add more landscape regions as needed
  ];

  // --- Screen Management Function ---
  function showScreen(screenName) {
    uploadContainer.classList.remove("active");
    processingContainer.classList.remove("active");
    resultsContainer.classList.remove("active");

    if (screenName === "upload") {
      uploadContainer.classList.add("active");
    } else if (screenName === "processing") {
      processingContainer.classList.add("active");
    } else if (screenName === "results") {
      resultsContainer.classList.add("active");
    }
  }

  // --- Trigger file input from our custom button ---
  uploadButton.addEventListener("click", () => {
    videoError.textContent = "";
    videoUpload.click(); // Open file dialog
  });

  // --- Handle video upload (from file input) ---
  videoUpload.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (file) {
      handleFile(file);
    }
  });

  // --- NEW: Handle "Process Another" button ---
  processAnotherButton.addEventListener("click", () => {
    // Show upload screen
    showScreen("upload");

    // Reset state
    if (originalVideo.src) URL.revokeObjectURL(originalVideo.src);
    if (processedVideo.src) URL.revokeObjectURL(processedVideo.src);

    originalVideo.src = "";
    processedVideo.src = "";
    processedBlob = null;

    downloadButton.disabled = true;
    downloadButton.textContent = "Download Processed Video";

    videoError.textContent = "";
    processedError.textContent = "";

    // Reset file input so user can re-upload same file
    videoUpload.value = null;

    // Reset progress bar
    document.getElementById("progressBar").style.width = "0%";
  });

  // --- NEW: Drag and Drop Event Handlers ---
  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  // Prevent browser default behavior for drag/drop
  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    uploadCard.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
  });

  // Add visual cue
  ["dragenter", "dragover"].forEach((eventName) => {
    uploadCard.addEventListener(
      eventName,
      () => {
        uploadCard.classList.add("drag-over");
      },
      false
    );
  });

  // Remove visual cue
  ["dragleave", "drop"].forEach((eventName) => {
    uploadCard.addEventListener(
      eventName,
      () => {
        uploadCard.classList.remove("drag-over");
      },
      false
    );
  });

  // Handle file drop
  uploadCard.addEventListener(
    "drop",
    (e) => {
      videoError.textContent = ""; // Clear previous errors
      const dt = e.dataTransfer;
      const file = dt.files[0];

      if (file) {
        handleFile(file);
      }
    },
    false
  );

  // --- NEW: Central File Handling Function ---
  // (All logic from 'videoUpload.addEventListener' moved here)
  function handleFile(file) {
    // Cleanup old URLs
    if (originalVideo.src) URL.revokeObjectURL(originalVideo.src);
    if (processedVideo.src) URL.revokeObjectURL(processedVideo.src);
    processedBlob = null;
    downloadButton.disabled = true;

    if (!file.type.startsWith("video/")) {
      videoError.textContent =
        "Please upload a valid video file (e.g., MP4, WebM)";
      return;
    }

    // --- Show processing screen ---
    showScreen("processing");
    processingStatus.textContent = "Uploading...";
    videoError.textContent = "";

    const url = URL.createObjectURL(file);
    originalVideo.src = url; // Load original video

    // Simulate upload progress
    simulateProgress("progressBar", 100, 1500, () => {
      // Upload is "done", now wait for metadata
      processingStatus.textContent = "Analyzing video...";
    });

    originalVideo.onloadedmetadata = () => {
      console.log("Metadata loaded");
      // --- Auto-start watermark removal ---
      processingStatus.textContent = "Removing watermark...";

      // Reset progress bar for processing
      document.getElementById("progressBar").style.width = "0%";

      // --- NEW: Check video orientation ---
      const width = originalVideo.videoWidth;
      const height = originalVideo.videoHeight;
      let chosenRegions;

      if (width >= height) {
        console.log(`Video is LANDSCAPE (${width}x${height})`);
        chosenRegions = landscapeRegions;
      } else {
        console.log(`Video is PORTRAIT (${width}x${height})`);
        chosenRegions = portraitRegions;
      }
      // --- End of new logic ---

      // Pass the dynamically chosen regions to the function
      removeWatermark(originalVideo, chosenRegions)
        .then((result) => {
          console.log(
            `Processed ${result.fileExtension} blob size:`,
            result.blob.size,
            "bytes"
          );

          processedBlob = result.blob;
          processedFileExtension = result.fileExtension;

          const processedUrl = URL.createObjectURL(processedBlob);
          processedVideo.src = processedUrl;

          downloadButton.textContent = `Download Processed Video (${processedFileExtension.toUpperCase()})`;
          downloadButton.disabled = false;

          // --- Show final results screen ---
          showScreen("results");
        })
        .catch((error) => {
          // On error, go back to upload screen
          console.error("Watermark removal error:", error);
          showScreen("upload");
          videoError.textContent = `Error: Failed to process video. (${error.message})`;
        });
    };

    originalVideo.onerror = (error) => {
      console.error("Video load error:", error);
      // On error, go back to upload screen
      showScreen("upload");
      videoError.textContent =
        "Error: Failed to load video (invalid format or corrupted file)";
      URL.revokeObjectURL(url);
    };
  }

  // Handle download button click
  downloadButton.addEventListener("click", () => {
    if (processedBlob) {
      const url = URL.createObjectURL(processedBlob);
      const filename = `markfree_processed_video.${processedFileExtension}`;

      chrome.downloads.download(
        {
          url: url,
          filename: filename,
          saveAs: true,
        },
        () => {
          URL.revokeObjectURL(url);
        }
      );
    }
  });
});

// --- (Your removeWatermark function goes here) ---
// PASTE THIS ENTIRE FUNCTION TO REPLACE YOUR OLD ONE

async function removeWatermark(videoElement, regions) {
  // We need to wrap the core logic in a Promise
  return new Promise(async (resolve, reject) => {
    if (isNaN(videoElement.duration) || videoElement.duration <= 0) {
      console.error("Invalid video duration:", videoElement.duration);
      reject(new Error("Invalid video duration"));
      return;
    }

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    canvas.width = videoElement.videoWidth;
    canvas.height = videoElement.videoHeight;

    // --- 1. Set up Web Audio API ---
    // Create an audio context and a "virtual microphone" (destination)
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const audioDestination = audioCtx.createMediaStreamDestination();
    let audioSource = null;
    let audioTracks = [];

    // --- 2. Fetch and Decode Audio ---
    try {
      // Fetch the video data from its object URL
      const response = await fetch(videoElement.src);
      const fileArrayBuffer = await response.arrayBuffer();

      // Decode the audio data from the file
      // We use a *copy* of the buffer for decoding, as some browsers need it
      const audioBuffer = await audioCtx.decodeAudioData(fileArrayBuffer.slice(0));

      // Create a source node to "play" the decoded audio
      audioSource = audioCtx.createBufferSource();
      audioSource.buffer = audioBuffer;

      // Connect the audio source to our virtual microphone
      audioSource.connect(audioDestination);

      // Get the audio track from the virtual microphone's stream
      audioTracks = audioDestination.stream.getAudioTracks();
      console.log("Successfully decoded and captured audio track.");
    } catch (e) {
      console.warn("Could not process audio. Video will be mute.", e);
      // If audio fails, we continue with an empty audioTracks array
    }

    // --- 3. Get Video Stream (from canvas) ---
    const canvasVideoStream = canvas.captureStream(30); // Get video from canvas

    // --- 4. Combine Streams ---
    const combinedStream = new MediaStream([
      ...canvasVideoStream.getVideoTracks(),
      ...audioTracks, // Add the audio tracks (if any)
    ]);

    // --- 5. Check for MP4 Support (Same as your code) ---
    const preferredMimeType = 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"';
    const fallbackMimeType = "video/webm";
    let chosenMimeType = fallbackMimeType;
    let fileExtension = "webm";

    if (MediaRecorder.isTypeSupported(preferredMimeType)) {
      chosenMimeType = preferredMimeType;
      fileExtension = "mp4";
      console.log("Using preferred MIME type: video/mp4");
    } else if (MediaRecorder.isTypeSupported("video/mp4")) {
      chosenMimeType = "video/mp4";
      fileExtension = "mp4";
      console.log("Using general MIME type: video/mp4");
    } else {
      console.warn("video/mp4 not supported, falling back to video/webm.");
    }

    // --- 6. Configure MediaRecorder ---
    const mediaRecorder = new MediaRecorder(combinedStream, {
      mimeType: chosenMimeType,
    });
    const chunks = [];

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    // --- 7. Mute video to prevent echo ---
    // This is CRITICAL. The audio will come from the Web Audio API,
    // not from the <video> element playing.
    videoElement.volume = 0;
    videoElement.muted = true; // Also set muted property

    // Helper to stop recording and clean up
    function stopRecording() {
      if (mediaRecorder.state === "recording") {
        mediaRecorder.stop();
      }
      // Clean up the audio context
      if (audioCtx.state !== "closed") {
        audioCtx.close();
      }
    }

    mediaRecorder.onstop = () => {
      console.log(
        "MediaRecorder stopped, total chunks:",
        chunks.length,
        "final time:",
        videoElement.currentTime
      );

      if (chunks.length === 0) {
        console.error("No chunks captured");
        reject(new Error("No video data captured"));
        return;
      }

      const blob = new Blob(chunks, { type: chosenMimeType });
      resolve({ blob: blob, fileExtension: fileExtension });
    };

    mediaRecorder.onerror = (event) => {
      console.error("MediaRecorder error:", event);
      reject(new Error("MediaRecorder error: " + event.message));
      stopRecording();
    };

    mediaRecorder.start(1000); // Collect chunks every 1s

    videoElement.onended = () => {
      console.log("Video playback ended.");
      stopRecording();
    };

    videoElement.onerror = (error) => {
      console.error("Video element error during processing:", error);
      stopRecording();
      reject(new Error("Video playback error"));
    };

    // --- 8. Draw Frame (USING requestVideoFrameCallback) ---
    // (This is the same as your code, but with the timeupdate listener moved)
    
    // Set up progress bar listener
    const progressBar = document.getElementById("progressBar");
    const updateProgress = () => {
        const progress = (videoElement.currentTime / videoElement.duration) * 100;
        progressBar.style.width = `${progress}%`;
    };
    videoElement.addEventListener("timeupdate", updateProgress);


    function drawFrame(now, metadata) {
      try {
        // 1. Draw the full, normal video frame
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

        // 2. Save state
        ctx.save();

        // 3. Set blur filter
        ctx.filter = "blur(25px)";

        // 4. Apply blur to regions
        regions.forEach((region) => {
          // Apply blur 3 times for a stronger effect
          ctx.drawImage(canvas, region.x, region.y, region.width, region.height, region.x, region.y, region.width, region.height);
          ctx.drawImage(canvas, region.x, region.y, region.width, region.height, region.x, region.y, region.width, region.height);
          ctx.drawImage(canvas, region.x, region.y, region.width, region.height, region.x, region.y, region.width, region.height);
        });

        // 5. Restore state
        ctx.restore();

        // --- Register for the NEXT frame ---
        videoElement.requestVideoFrameCallback(drawFrame);
      } catch (error) {
        console.error("Draw frame error:", error);
        stopRecording();
        reject(error);
      }
    }

    // --- 9. Start Playback ---
    videoElement.currentTime = 0;
    videoElement
      .play()
      .then(() => {
        console.log("Video playback started for processing...");
        
        // Start the canvas drawing loop
        videoElement.requestVideoFrameCallback(drawFrame);
        
        // --- THIS IS THE KEY ---
        // Start the audio source *at the same time*
        if (audioSource) {
          audioSource.start(0);
        }
      })
      .catch((error) => {
        console.error("Video playback failed:", error);
        reject(error);
      });
  });
}