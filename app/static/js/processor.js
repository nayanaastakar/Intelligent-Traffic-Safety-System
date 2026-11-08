// Video & Media Processor Job Poller

window.pollJobStatus = function(jobId, onProgress, onComplete, onError) {
    const pollInterval = setInterval(async () => {
        try {
            const resp = await fetch(`/api/jobs/${jobId}`);
            if (!resp.ok) {
                clearInterval(pollInterval);
                if (onError) onError("Failed to query job status");
                return;
            }
            const data = await resp.json();
            if (!data.success) {
                clearInterval(pollInterval);
                if (onError) onError(data.error || "Job failed");
                return;
            }

            const job = data.job;
            if (onProgress) {
                onProgress(job.progress_percent, job.message, job);
            }

            if (job.status === "COMPLETED") {
                clearInterval(pollInterval);
                // Fetch full session result
                const resResp = await fetch(`/api/jobs/${jobId}/result`);
                const resData = await resResp.json();
                if (onComplete) {
                    onComplete(resData.session || job.result);
                }
            } else if (job.status === "FAILED") {
                clearInterval(pollInterval);
                if (onError) {
                    onError(job.message || "Video processing failed");
                }
            }
        } catch (err) {
            clearInterval(pollInterval);
            if (onError) onError(err.message);
        }
    }, 800);
};

// Drag and drop setup helper
window.setupDropzone = function(dropzoneId, fileInputId, previewContainerId) {
    const dropzone = document.getElementById(dropzoneId);
    const fileInput = document.getElementById(fileInputId);
    const previewContainer = document.getElementById(previewContainerId);

    if (!dropzone || !fileInput) return;

    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("drag-active");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("drag-active");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("drag-active");
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelection(fileInput.files[0], previewContainer);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleFileSelection(fileInput.files[0], previewContainer);
        }
    });
};

function handleFileSelection(file, previewContainer) {
    if (!previewContainer) return;
    previewContainer.innerHTML = "";

    const infoBox = document.createElement("div");
    infoBox.style.cssText = "margin-top: 12px; padding: 10px 14px; background: #0b1220; border-radius: 8px; border: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: space-between;";
    infoBox.innerHTML = `
        <div style="font-size: 0.85rem; color: #fff;">
            <strong>${file.name}</strong> 
            <span style="color: var(--text-muted); font-size: 0.75rem;">(${(file.size / (1024 * 1024)).toFixed(2)} MB)</span>
        </div>
        <span style="font-size: 0.75rem; color: #38bdf8; text-transform: uppercase;">Ready to process</span>
    `;
    previewContainer.appendChild(infoBox);

    // If image, show mini preview
    if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = document.createElement("img");
            img.src = e.target.result;
            img.style.cssText = "max-height: 180px; max-width: 100%; border-radius: 8px; margin-top: 10px; border: 1px solid var(--border-subtle);";
            previewContainer.appendChild(img);
        };
        reader.readAsDataURL(file);
    }
}
