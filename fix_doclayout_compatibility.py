#!/usr/bin/env python3
"""
Fix doclayout-yolo compatibility issues
"""

import subprocess
import sys

def fix_doclayout_compatibility():
    """Fix doclayout-yolo compatibility with huggingface-hub"""
    print("Fixing doclayout-yolo compatibility issues...")
    
    try:
        # Uninstall conflicting packages
        print("Uninstalling potentially conflicting packages...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'uninstall', 
            'doclayout-yolo', 'huggingface-hub', '-y'
        ])
        
        # Install compatible versions
        print("Installing compatible versions...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 
            'huggingface-hub==0.16.4'
        ])
        
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 
            'doclayout-yolo==0.0.4'
        ])
        
        print("Compatibility fix completed!")
        print("Please restart the server: python main.py")
        
    except subprocess.CalledProcessError as e:
        print(f"Error fixing compatibility: {e}")
        print("\nManual fix:")
        print("1. pip uninstall doclayout-yolo huggingface-hub -y")
        print("2. pip install huggingface-hub==0.16.4")
        print("3. pip install doclayout-yolo==0.0.4")
        print("\nIf issues persist, the system will use ultralytics YOLO as fallback.")

def test_import():
    """Test if doclayout-yolo can be imported"""
    try:
        from doclayout_yolo import YOLOv10
        print("✓ doclayout-yolo imported successfully")
        return True
    except Exception as e:
        print(f"✗ doclayout-yolo import failed: {e}")
        return False

if __name__ == '__main__':
    print("Testing current doclayout-yolo installation...")
    if not test_import():
        fix_doclayout_compatibility()
        print("\nTesting after fix...")
        test_import()
    else:
        print("doclayout-yolo is working correctly!")