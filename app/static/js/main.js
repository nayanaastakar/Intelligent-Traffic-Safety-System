// Global Antigravity / Intelligent Traffic Safety System JS Utilities

document.addEventListener("DOMContentLoaded", () => {
    // 1. Mobile Drawer and Sidebar Toggle
    const toggleBtn = document.getElementById("sidebarToggle");
    const sidebar = document.querySelector(".app-sidebar");
    
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener("click", () => {
            if (window.innerWidth <= 992) {
                sidebar.classList.toggle("show-drawer");
            } else {
                sidebar.classList.toggle("collapsed");
                const main = document.querySelector(".app-main");
                if (main) {
                    if (sidebar.classList.contains("collapsed")) {
                        sidebar.style.width = "78px";
                        main.style.marginLeft = "78px";
                    } else {
                        sidebar.style.width = "270px";
                        main.style.marginLeft = "270px";
                    }
                }
            }
        });
    }

    // Close drawer when clicking outside on mobile
    document.addEventListener("click", (e) => {
        if (window.innerWidth <= 992 && sidebar && sidebar.classList.contains("show-drawer")) {
            if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                sidebar.classList.remove("show-drawer");
            }
        }
    });
});

// Web Audio API beep generator for in-browser sound alerts
window.playWebBeep = function(freq = 880, durationMs = 250) {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sine";
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + (durationMs / 1000));
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + (durationMs / 1000));
    } catch (e) {
        console.warn("AudioContext not permitted or supported:", e);
    }
};

// Global Toast Notifications
window.showToast = function(message, type = "info") {
    let container = document.getElementById("toastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "toastContainer";
        container.style.cssText = "position: fixed; bottom: 24px; right: 24px; z-index: 1090; display: flex; flex-direction: column; gap: 10px;";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    const colors = {
        success: { bg: "#064e3b", border: "#10b981", text: "#6ee7b7", icon: "✓" },
        error: { bg: "#7f1d1d", border: "#ef4444", text: "#fca5a5", icon: "⚠" },
        warning: { bg: "#78350f", border: "#f59e0b", text: "#fde68a", icon: "!" },
        info: { bg: "#1e293b", border: "#38bdf8", text: "#bae6fd", icon: "ℹ" }
    };
    const c = colors[type] || colors.info;

    toast.style.cssText = `
        background-color: ${c.bg};
        border: 1px solid ${c.border};
        color: ${c.text};
        padding: 12px 18px;
        border-radius: 8px;
        font-size: 0.85rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 260px;
        max-width: 400px;
        animation: slideInToast 0.3s ease;
    `;
    toast.innerHTML = `<strong>${c.icon}</strong> <span>${message}</span>`;
    container.appendChild(toast);

    if (type === "error" || type === "warning") {
        window.playWebBeep(type === "error" ? 1000 : 700, 300);
    }

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.4s";
        setTimeout(() => toast.remove(), 400);
    }, 4000);
};

// Open Evidence Modal
window.openEvidenceModal = function(imageSrc, title = "Incident Evidence Frame") {
    let modal = document.getElementById("evidenceModal");
    if (!modal) {
        modal = document.createElement("div");
        modal.id = "evidenceModal";
        modal.className = "modal-backdrop-custom";
        modal.innerHTML = `
            <div class="modal-content-custom">
                <div style="padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
                    <h5 id="evidenceModalTitle" style="margin: 0; color: #fff; font-size: 1rem;">Evidence Frame</h5>
                    <button type="button" onclick="closeEvidenceModal()" style="background: none; border: none; color: #94a3b8; font-size: 1.4rem; cursor: pointer;">&times;</button>
                </div>
                <div style="padding: 20px; text-align: center;">
                    <img id="evidenceModalImg" src="" style="max-width: 100%; border-radius: 8px; border: 1px solid var(--border-subtle);" />
                </div>
                <div style="padding: 14px 20px; border-top: 1px solid var(--border-subtle); display: flex; justify-content: flex-end; gap: 10px;">
                    <a id="evidenceDownloadBtn" href="" download class="btn-primary-surv" style="font-size: 0.8rem; padding: 6px 14px;">Download Frame</a>
                    <button type="button" onclick="closeEvidenceModal()" class="btn-secondary-surv" style="font-size: 0.8rem; padding: 6px 14px;">Close</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    const titleElem = document.getElementById("evidenceModalTitle");
    const imgElem = document.getElementById("evidenceModalImg");
    const dlBtn = document.getElementById("evidenceDownloadBtn");

    if (titleElem) titleElem.innerText = title;
    if (imgElem) imgElem.src = imageSrc;
    if (dlBtn) dlBtn.href = imageSrc;

    modal.classList.add("show");
};

window.closeEvidenceModal = function() {
    const modal = document.getElementById("evidenceModal");
    if (modal) modal.classList.remove("show");
};
