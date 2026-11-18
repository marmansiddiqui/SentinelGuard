
from pathlib import Path
from urllib.request import urlretrieve

MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

models = {
    "face_detection_yunet_2023mar.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",

    "face_recognition_sface_2021dec.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
}

for filename, url in models.items():

    destination = MODEL_DIR / filename

    if destination.exists() and destination.stat().st_size > 100000:
        print(f"Already downloaded: {filename}")
        continue

    print(f"Downloading: {filename}")

    urlretrieve(url, destination)

    if destination.stat().st_size < 100000:
        raise RuntimeError(f"Invalid model download: {filename}")

    print(f"Downloaded successfully: {filename}")

print("\nAll models downloaded!")
