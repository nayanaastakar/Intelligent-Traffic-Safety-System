# Intelligent Traffic Safety System

This repository contains several Python scripts for traffic safety monitoring using computer vision.

## Project Modules

- `traffic.py`: traffic density detection using YOLO object detection.
- `accident.py`: accident likelihood detection based on object proximity.
- `vehicle_name.py`: vehicle detection and object name display on images.
- `overspeed.py`: speed overlay and warning message for a car image.
- `drowsiness.py`: driver drowsiness detection using MediaPipe face landmarks.
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

If no `--video` is provided, the default webcam is used.

### Accident Detection

```bash
py -3 accident.py --video path/to/accident_video.mp4
```

### Vehicle Detection on Image

```bash
py -3 vehicle_name.py --image path/to/image.png
```

### Overspeed Overlay

```bash
py -3 overspeed.py --image path/to/car_image.jpg --speed 75
```

### Drowsiness Detection

```bash
py -3 drowsiness.py
```

Press `q` in any video window to exit.

## Notes

- `drowsiness.py` uses the webcam by default.
- `winsound` is used for sound alerts on Windows.
- The project is designed to be run from the repo root.

## Contribution

If you want to add dataset examples or input videos, place them in a `data/` folder and update the example commands.
