import time

import cv2


EXIT_KEYS = {27, ord("q"), ord("Q")}


class BeepLimiter:
    def __init__(self, interval_seconds=2.0):
        self.interval_seconds = interval_seconds
        self.last_beep_at = 0.0

    def ready(self):
        now = time.monotonic()
        if now - self.last_beep_at < self.interval_seconds:
            return False
        self.last_beep_at = now
        return True


def should_exit(delay=1):
    return cv2.waitKey(delay) & 0xFF in EXIT_KEYS


def show_exit_hint(frame):
    height = frame.shape[0]
    cv2.putText(
        frame,
        "ESC/Q: exit",
        (12, height - 16),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )
    return frame
