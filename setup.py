#!/usr/bin/env python3
"""
Setup script for PDF Layout Analysis API
"""

import os
import sys
import subprocess

def create_directories():
    """Create necessary directories"""
    directories = [
        'uploads',
        'temp',
        'models'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

def download_yolo_model():
    """Download YOLO-DocLayout model"""
    print("Note: You need to manually download the YOLO-DocLayout model")
    print("Visit: https://github.com/opendatalab/DocLayout-YOLO")
    print("Download the model and place it in the 'models' directory as 'yolo_doclayout_model.pt'")

def install_requirements():
    """Install Python requirements"""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")

def main():
    print("Setting up PDF Layout Analysis API...")
    
    # Create directories
    create_directories()
    
    # Install requirements
    install_requirements()
    
    # Model download instructions
    download_yolo_model()
    
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("Created .env file from .env.example")
        else:
            print("Please create a .env file based on .env.example")
    
    print("\nSetup completed!")
    print("To run the application:")
    print("python main.py")
    print("\nAPI will be available at:")
    print("- Test page: http://localhost:5000/")
    print("- Swagger UI: http://localhost:5000/swagger/")

if __name__ == '__main__':
    main()