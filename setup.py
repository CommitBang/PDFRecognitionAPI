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
    print("\nSetting up YOLO models...")
    try:
        subprocess.check_call([sys.executable, 'download_model.py'])
    except subprocess.CalledProcessError as e:
        print(f"Error running model download script: {e}")
        print("You can manually run: python download_model.py")
    except FileNotFoundError:
        print("download_model.py not found. Skipping model download.")
        print("Note: The system will auto-download YOLOv8 as fallback when first used.")

def install_requirements():
    """Install Python requirements"""
    try:
        # Install PyTorch with CUDA support first
        print("Installing PyTorch with CUDA 12.1 support...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 
            'torch==2.1.0', 'torchvision==0.16.0', 'torchaudio==2.1.0',
            '--index-url', 'https://download.pytorch.org/whl/cu121'
        ])
        print("PyTorch with CUDA installed successfully")
        
        # Install other requirements
        print("Installing other requirements...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("All requirements installed successfully")
        
    except subprocess.CalledProcessError as e:
        print(f"Error installing PyTorch with CUDA: {e}")
        print("Trying fallback to CPU version...")
        try:
            # Fallback to CPU version if GPU installation fails
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'torch', 'torchvision', 'torchaudio'])
            # Install other requirements
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            print("Fallback CPU installation completed")
        except subprocess.CalledProcessError as e2:
            print(f"Fallback installation also failed: {e2}")

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