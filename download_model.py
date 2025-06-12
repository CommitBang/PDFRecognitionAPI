#!/usr/bin/env python3
"""
Download YOLO-DocLayout model
"""

import os
import requests
import sys
from pathlib import Path

def download_file(url, filename, chunk_size=8192):
    """Download file with progress indicator"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\rDownloading: {progress:.1f}%", end='', flush=True)
        
        print(f"\nDownloaded: {filename}")
        return True
        
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def main():
    # Create models directory
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    model_path = models_dir / "yolo_doclayout_model.pt"
    
    if model_path.exists():
        print(f"Model already exists at {model_path}")
        return
    
    print("Downloading YOLO-DocLayout model...")
    
    # Try different sources for the model
    model_urls = [
        # HuggingFace model hub
        "https://huggingface.co/opendatalab/DocLayout-YOLO/resolve/main/doclayout_yolo.pt",
        # Alternative GitHub release
        "https://github.com/opendatalab/DocLayout-YOLO/releases/download/v1.0/doclayout_yolo.pt"
    ]
    
    success = False
    for url in model_urls:
        print(f"Trying to download from: {url}")
        if download_file(url, model_path):
            success = True
            break
        print(f"Failed to download from {url}")
    
    if not success:
        print("\nAutomatic download failed. Please manually download the model:")
        print("1. Visit: https://github.com/opendatalab/DocLayout-YOLO")
        print("2. Download the model file")
        print(f"3. Place it at: {model_path}")
        print("\nAlternatively, you can use a pre-trained YOLOv8 model:")
        print("The system will fallback to yolov8n.pt if DocLayout model is not found")
        
        # Download YOLOv8 as fallback
        print("\nDownloading YOLOv8 fallback model...")
        yolo_url = "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt"
        fallback_path = models_dir / "yolov8n.pt"
        if download_file(yolo_url, fallback_path):
            print("YOLOv8 fallback model downloaded successfully")
    else:
        print(f"\nYOLO-DocLayout model downloaded successfully to {model_path}")

if __name__ == '__main__':
    main()