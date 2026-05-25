# Intelligent Traffic Safety System

This repository contains several Python scripts for traffic safety monitoring using computer vision.

## Project Modules

- `traffic.py`: traffic density detection using YOLO object detection.
- `accident.py`: accident detection with delayed confirmation and alert display.
- `vehicle_name.py`: vehicle detection and object name display on images or videos.
- `overspeed.py`: speed overlay and warning message for images or videos.
- `drowsiness.py`: driver drowsiness detection from camera or video.
- `app.py`: browser-based dashboard for running all modules.
- `download_assets.py`: download the YOLO asset files required to run the object detection modules.

## Requirements

Install dependencies with:

```bash
py -3 -m pip install -r requirements.txt
```

## Download Required Assets

The YOLO object detection scripts require these files in the repository root:

- `coco.names`
- `yolov3-tiny.cfg`
- `yolov3-tiny.weights`

You can download them with:

```bash
py -3 download_assets.py
```

If you want to use the full YOLOv3 model instead, place `yolov3.cfg` and `yolov3.weights` in the repo root.

## Run the Scripts

### Traffic Density

```bash
py -3 traffic.py --video path/to/traffic_video.mp4
```

### Accident Detection

```bash
py -3 accident.py --video path/to/accident_video.mp4
```

### Vehicle Detection

Process a single image:
```bash
py -3 vehicle_name.py --image path/to/image.png
```

Process a video:
```bash
py -3 vehicle_name.py --video path/to/video.mp4
```

### Overspeed Overlay

Overlay speed on a single image:
```bash
py -3 overspeed.py --image path/to/car_image.jpg --speed 75
```

Overlay speed on a video:
```bash
py -3 overspeed.py --video path/to/video.mp4 --speed 85
```

### Drowsiness Detection

```bash
py -3 drowsiness.py
```

To use an alternate camera device (if multiple cameras are available):
```bash
py -3 drowsiness.py --camera 1
```

To process a driver video:
```bash
py -3 drowsiness.py --video path/to/driver_video.mp4
```

The drowsiness module uses MediaPipe when available and falls back to OpenCV Haar face/eye detection when needed.

### Unified Web Interface

Start the browser-based control center with:

```bash
py -3 main.py web
```

Or:

```bash
py -3 app.py
```

Then open `http://127.0.0.1:5000` in your browser to access the Traffic Safety dashboard.

#### Uploaded videos

Place these files in the `uploads/` folder:

| File | Module |
|------|--------|
| `video1.mp4` | Traffic density and vehicle classification |
| `video4.mp4` | Overspeed alert |
| `video5.mp4` | Drowsiness detection |
| `video6.mp4` | Accident detection |

The dashboard auto-selects the correct video for each module. Press `Esc` or `q` in any detection window to exit.

Sample copies of the usable videos are included in `sample_videos/`. If you need to restore the local inputs later, copy them from `sample_videos/` into `uploads/` using the same filenames.

## Notes

- `drowsiness.py` uses the webcam by default and falls back to `uploads/video5.mp4` if the camera cannot open.
- `winsound` is used for sound alerts on Windows.
- The project is designed to be run from the repo root.

## Contribution

If you want to add dataset examples or input videos, place them in a `data/` folder and update the example commands.
