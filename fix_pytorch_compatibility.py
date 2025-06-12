#!/usr/bin/env python3
"""
Fix PyTorch compatibility issues for YOLO models
"""

import subprocess
import sys

def fix_compatibility():
    """Fix PyTorch/YOLO compatibility"""
    print("Fixing PyTorch/YOLO compatibility issues...")
    
    try:
        # Update ultralytics to latest compatible version
        print("Updating ultralytics...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 
            'ultralytics==8.2.0', '--upgrade'
        ])
        
        # Reinstall PyTorch with CUDA support
        print("Reinstalling PyTorch with CUDA support...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 
            'torch==2.1.0', 'torchvision==0.16.0', 'torchaudio==2.1.0',
            '--index-url', 'https://download.pytorch.org/whl/cu121',
            '--force-reinstall'
        ])
        
        print("Compatibility fix completed!")
        print("Please restart the server: python main.py")
        
    except subprocess.CalledProcessError as e:
        print(f"Error fixing compatibility: {e}")
        print("Manual fix:")
        print("1. pip install ultralytics==8.2.0 --upgrade")
        print("2. pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121 --force-reinstall")

if __name__ == '__main__':
    fix_compatibility()