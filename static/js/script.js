const moduleInputs = {
    traffic: {
        selectId: 'traffic-video-select',
        fileId: 'traffic-video',
        acceptsUpload: 'video',
    },
    accident: {
        selectId: 'accident-video-select',
        fileId: 'accident-video',
        acceptsUpload: 'video',
    },
    vehicle: {
        selectId: 'vehicle-video-select',
        fileId: 'vehicle-input',
        acceptsUpload: 'media',
    },
    overspeed: {
        selectId: 'overspeed-video-select',
        fileId: 'overspeed-input',
        acceptsUpload: 'media',
    },
    drowsiness: {
        selectId: 'drowsiness-video-select',
        fileId: 'drowsiness-video',
        acceptsUpload: 'video',
    },
};

let uploadedVideos = [];
let assignments = {};

function setStatus(message, state = 'ready') {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = 'status-pill';
    if (state === 'busy') {
        statusEl.classList.add('busy');
    } else if (state === 'error') {
        statusEl.classList.add('error');
    }
}

function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = isError ? 'toast error' : 'toast';
    toast.hidden = false;
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => {
        toast.hidden = true;
    }, 4000);
}

function formatBytes(bytes) {
    if (bytes === 0) {
        return '0 B';
    }
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    return `${(bytes / Math.pow(1024, index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function renderAssignments(modules) {
    const grid = document.getElementById('assignments-grid');
    grid.innerHTML = '';

    Object.values(modules).forEach((item) => {
        const card = document.createElement('article');
        card.className = `assignment-card ${item.selected_video ? 'ready' : 'missing'}`;
        card.innerHTML = `
            <h4>${item.label}</h4>
            <p class="video-name">${item.selected_video || item.video}</p>
            <p class="status-text">${item.selected_video ? 'Ready to run' : 'Missing or empty - add to uploads folder'}</p>
        `;
        grid.appendChild(card);
    });
}

function updateReadyBadges(modules) {
    document.querySelectorAll('[data-ready-for]').forEach((badge) => {
        const module = badge.dataset.readyFor;
        const info = modules[module];
        if (!info) {
            badge.textContent = '-';
            badge.className = 'ready-badge';
            return;
        }
        if (info.selected_video) {
            badge.textContent = 'Ready';
            badge.className = 'ready-badge ok';
        } else {
            badge.textContent = 'Missing';
            badge.className = 'ready-badge warn';
        }
    });
}

function renderUploads(files) {
    const list = document.getElementById('uploads-list');
    list.innerHTML = '';

    if (!files.length) {
        const empty = document.createElement('span');
        empty.className = 'upload-chip empty';
        empty.innerHTML = '<span class="dot"></span> No files in uploads folder';
        list.appendChild(empty);
        return;
    }

    files.forEach((file) => {
        const chip = document.createElement('span');
        chip.className = file.usable ? 'upload-chip' : 'upload-chip empty';
        const modules = file.assigned_to && file.assigned_to.length
            ? ` -> ${file.assigned_to.join(', ')}`
            : '';
        chip.innerHTML = `<span class="dot"></span>${file.name} (${formatBytes(file.size)})${modules}`;
        list.appendChild(chip);
    });
}

function preferredVideoForModule(module) {
    const cfg = assignments[module];
    if (cfg && cfg.selected_video) {
        return cfg.selected_video;
    }
    if (cfg && cfg.ready && cfg.actual_name) {
        return cfg.actual_name;
    }
    if (cfg && cfg.video) {
        const match = uploadedVideos.find(
            (v) => v.name.toLowerCase() === cfg.video.toLowerCase() && v.usable,
        );
        if (match) {
            return match.name;
        }
    }
    return '';
}

function populateSelects() {
    Object.entries(moduleInputs).forEach(([module, config]) => {
        const select = document.getElementById(config.selectId);
        select.innerHTML = '';

        const none = document.createElement('option');
        none.value = '';
        none.textContent = module === 'drowsiness' ? 'Use webcam instead' : 'Choose a video...';
        select.appendChild(none);

        uploadedVideos.forEach((video) => {
            const option = document.createElement('option');
            option.value = video.name;
            option.textContent = `${video.name} (${formatBytes(video.size)})`;
            option.disabled = !video.usable;
            select.appendChild(option);
        });

        const preferred = preferredVideoForModule(module);
        if (preferred) {
            select.value = preferred;
        }
    });
}

function selectedUpload(module) {
    const config = moduleInputs[module];
    const select = document.getElementById(config.selectId);
    return select ? select.value : '';
}

function selectedFile(module) {
    const config = moduleInputs[module];
    const input = document.getElementById(config.fileId);
    return input && input.files.length ? input.files[0] : null;
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
    });

    const data = await response.json();
    if (data.status !== 'success') {
        throw new Error(data.message);
    }
    return data.filename;
}

function applyFileToPayload(module, filename, fileType, payload) {
    if (module === 'vehicle' || module === 'overspeed') {
        if (fileType.startsWith('image/')) {
            payload.image = filename;
        } else {
            payload.video = filename;
        }
        return;
    }
    payload.video = filename;
}

async function runModule(module) {
    const buttons = document.querySelectorAll('button');
    buttons.forEach((button) => {
        button.disabled = true;
    });

    try {
        setStatus(`Starting ${module}...`, 'busy');
        const payload = {};
        const uploadName = selectedUpload(module);
        const file = selectedFile(module);

        if (file) {
            const uploadedFilename = await uploadFile(file);
            applyFileToPayload(module, uploadedFilename, file.type, payload);
        } else if (uploadName) {
            payload.video = uploadName;
        } else if (module !== 'drowsiness') {
            const fallback = preferredVideoForModule(module);
            if (fallback) {
                payload.video = fallback;
            } else {
                throw new Error(`Select a video or add the assigned file to uploads (see library panel).`);
            }
        }

        if (module === 'overspeed') {
            payload.speed = document.getElementById('speed-input').value || 0;
        }

        if (module === 'drowsiness' && !payload.video) {
            payload.camera = document.getElementById('camera-input').value || 0;
        }

        const response = await fetch(`/api/run/${module}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (data.status !== 'success') {
            throw new Error(data.message);
        }

        const videoLabel = payload.video ? ` on ${payload.video}` : ' (camera)';
        setStatus(`${module} running${videoLabel}`, 'busy');
        showToast(`${module} started - press Esc or Q in the window to stop.`);
        setTimeout(() => setStatus('System ready'), 5000);
    } catch (error) {
        setStatus(error.message, 'error');
        showToast(error.message, true);
    } finally {
        buttons.forEach((button) => {
            button.disabled = false;
        });
    }
}

async function loadDashboard() {
    try {
        const [uploadsRes, assignmentsRes] = await Promise.all([
            fetch('/api/uploads'),
            fetch('/api/assignments'),
        ]);

        const files = await uploadsRes.json();
        const assignmentData = await assignmentsRes.json();

        uploadedVideos = files.filter((file) => file.kind === 'video');
        assignments = assignmentData.modules || {};

        renderUploads(files);
        renderAssignments(assignments);
        updateReadyBadges(assignments);
        populateSelects();
    } catch (error) {
        setStatus(`Unable to load dashboard: ${error.message}`, 'error');
        showToast(error.message, true);
    }
}

async function stopModules() {
    try {
        const response = await fetch('/api/stop-all', { method: 'POST' });
        const data = await response.json();
        if (data.status !== 'success') {
            throw new Error(data.message || 'Unable to stop modules');
        }
        const count = data.stopped ? data.stopped.length : 0;
        setStatus(count ? `Stopped ${count} module(s)` : 'No modules running');
        showToast(count ? `Stopped ${count} running module(s).` : 'No modules were running.');
    } catch (error) {
        setStatus(error.message, 'error');
        showToast(error.message, true);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-run]').forEach((button) => {
        button.addEventListener('click', () => runModule(button.dataset.run));
    });

    document.getElementById('refresh-uploads').addEventListener('click', loadDashboard);
    document.getElementById('stop-modules').addEventListener('click', stopModules);

    document.querySelectorAll('.nav-link').forEach((link) => {
        link.addEventListener('click', () => {
            document.querySelectorAll('.nav-link').forEach((l) => l.classList.remove('active'));
            link.classList.add('active');
        });
    });

    loadDashboard();
});
