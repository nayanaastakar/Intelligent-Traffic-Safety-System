// Global Antigravity / Intelligent Traffic Safety System JS Utilities

document.addEventListener("DOMContentLoaded", () => {
    // 1. Mobile Drawer and Sidebar Toggle
    const toggleBtn = document.getElementById("sidebarToggle");
    const closeBtn = document.getElementById("sidebarCloseBtn");
    const backdrop = document.getElementById("sidebarBackdrop");
    const sidebar = document.getElementById("appSidebar") || document.querySelector(".app-sidebar");
    const main = document.querySelector(".app-main");

    function openMobileDrawer() {
        if (!sidebar) return;
        sidebar.classList.add("show-drawer");
        if (backdrop) backdrop.classList.add("show");
        document.body.classList.add("drawer-open");
    }

    function closeMobileDrawer() {
        if (!sidebar) return;
        sidebar.classList.remove("show-drawer");
        if (backdrop) backdrop.classList.remove("show");
        document.body.classList.remove("drawer-open");
    }

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (window.innerWidth <= 992) {
                if (sidebar.classList.contains("show-drawer")) {
                    closeMobileDrawer();
                } else {
                    openMobileDrawer();
                }
            } else {
                sidebar.classList.toggle("collapsed");
                if (main) {
                    main.classList.toggle("sidebar-collapsed");
                }
            }
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            closeMobileDrawer();
        });
    }

    if (backdrop) {
        backdrop.addEventListener("click", closeMobileDrawer);
    }

    // Auto-close drawer on route link click on mobile
    const navLinks = sidebar ? sidebar.querySelectorAll(".nav-item-link") : [];
    navLinks.forEach(link => {
        link.addEventListener("click", () => {
            if (window.innerWidth <= 992) {
                closeMobileDrawer();
            }
        });
    });

    // Handle screen resize
    window.addEventListener("resize", () => {
        if (window.innerWidth > 992) {
            closeMobileDrawer();
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

// Global Toast Notifications (Responsive positioning)
window.showToast = function(message, type = "info") {
    let container = document.getElementById("toastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "toastContainer";
        container.className = "toast-notifications-container";
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

    toast.className = "surv-toast-item";
    toast.style.backgroundColor = c.bg;
    toast.style.borderColor = c.border;
    toast.style.color = c.text;
    toast.innerHTML = `<strong>${c.icon}</strong> <span>${message}</span>`;
    container.appendChild(toast);

    if (type === "error" || type === "warning") {
        window.playWebBeep(type === "error" ? 1000 : 700, 300);
    }

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 350);
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
                <div style="padding: 14px 18px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
                    <h5 id="evidenceModalTitle" style="margin: 0; color: #fff; font-size: 0.95rem; font-weight: 700;">Evidence Frame</h5>
                    <button type="button" onclick="closeEvidenceModal()" style="background: none; border: none; color: #94a3b8; font-size: 1.4rem; cursor: pointer; line-height: 1;" aria-label="Close">&times;</button>
                </div>
                <div style="padding: 16px; text-align: center; max-height: 70vh; overflow-y: auto;">
                    <img id="evidenceModalImg" src="" style="max-width: 100%; height: auto; border-radius: 8px; border: 1px solid var(--border-subtle);" alt="Evidence Snapshot" />
                </div>
                <div style="padding: 12px 18px; border-top: 1px solid var(--border-subtle); display: flex; justify-content: flex-end; gap: 10px;">
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