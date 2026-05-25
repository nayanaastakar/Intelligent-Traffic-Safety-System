import os
import urllib.request

ASSETS = {
    "coco.names": "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names",
    "yolov3-tiny.cfg": "https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg",
    "yolov3-tiny.weights": "https://pjreddie.com/media/files/yolov3-tiny.weights",
}


def download_asset(name, url):
    destination = os.path.join(os.path.dirname(__file__), name)
    if os.path.exists(destination):
        print(f"Skipping existing file: {name}")
        return
    print(f"Downloading {name}...")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request) as response:
        with open(destination, "wb") as out_file:
            out_file.write(response.read())
    print(f"Saved {name}")


def main():
    for name, url in ASSETS.items():
        download_asset(name, url)
    print("All assets downloaded. You can now run the YOLO scripts.")


if __name__ == "__main__":
    main()
