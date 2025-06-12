#!/usr/bin/env python3
"""
PDF Recognition API Setup Script

This setup script provides an easy way to install the PDF Recognition API
with all required dependencies for Python 3.9 compatibility.
"""

import sys
import subprocess
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    
    if sys.version_info >= (3, 12):
        print("Warning: Python 3.12+ may have compatibility issues with some dependencies")
        print("Python 3.9-3.11 is recommended for best compatibility")

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*50}")
    print(f"STEP: {description}")
    print(f"Running: {command}")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False

def check_cuda():
    """Check if CUDA is available"""
    try:
        result = subprocess.run("nvidia-smi", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("CUDA detected - GPU acceleration will be available")
            return True
        else:
            print("CUDA not detected - will use CPU-only installation")
            return False
    except:
        print("Could not check CUDA availability - will use CPU-only installation")
        return False

def install_pytorch(use_gpu=True):
    """Install PyTorch with appropriate backend"""
    if use_gpu:
        print("Installing PyTorch with CUDA support...")
        command = "pip install torch==2.2.1 torchvision==0.17.1 torchaudio==2.2.1 --index-url https://download.pytorch.org/whl/cu118"
    else:
        print("Installing PyTorch CPU-only version...")
        command = "pip install torch==2.2.1 torchvision==0.17.1 torchaudio==2.2.1 --index-url https://download.pytorch.org/whl/cpu"
    
    return run_command(command, "Installing PyTorch")

def install_paddlepaddle(use_gpu=True):
    """Install PaddlePaddle with appropriate backend"""
    if use_gpu:
        print("Installing PaddlePaddle with GPU support...")
        command = "pip install paddlepaddle-gpu==3.0.0"
    else:
        print("Installing PaddlePaddle CPU-only version...")
        command = "pip install paddlepaddle==3.0.0"
    
    return run_command(command, "Installing PaddlePaddle")

def install_requirements():
    """Install remaining requirements"""
    # Create requirements without PyTorch and PaddlePaddle (already installed)
    requirements_without_torch = [
        "Flask==2.3.3",
        "flask-restx==1.3.0", 
        "Werkzeug==2.3.7",
        "PyMuPDF==1.20.2",
        "pdf2image==1.16.3",
        "Pillow==10.0.1",
        "paddlex[ocr]==3.0.1",
        "opencv-python==4.6.0.66",
        "numpy==1.24.4",
        "requests==2.31.0",
        "python-dotenv==1.0.0",
        "gunicorn==21.2.0",
        "pytest==7.4.3",
        "pytest-flask==1.3.0"
    ]
    
    temp_requirements = "temp_requirements.txt"
    with open(temp_requirements, 'w') as f:
        f.write('\n'.join(requirements_without_torch))
    
    success = run_command(f"pip install -r {temp_requirements}", "Installing remaining dependencies")
    
    # Clean up temp file
    if os.path.exists(temp_requirements):
        os.remove(temp_requirements)
    
    return success

def create_directories():
    """Create necessary directories"""
    directories = [
        "temp_uploads",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"Created directory: {directory}")

def download_models():
    """Download PaddleOCR models"""
    print("\nDownloading PaddleOCR models (this may take a while)...")
    test_script = """
import sys
sys.path.append('.')
try:
    from paddleocr import PaddleOCR
    print("Initializing PaddleOCR to download models...")
    ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)
    print("PaddleOCR models downloaded successfully!")
except Exception as e:
    print(f"Warning: Could not download models: {e}")
    print("Models will be downloaded on first API call")
"""
    
    with open("test_models.py", "w") as f:
        f.write(test_script)
    
    run_command("python test_models.py", "Downloading PaddleOCR models")
    
    # Clean up test file
    if os.path.exists("test_models.py"):
        os.remove("test_models.py")

def test_installation():
    """Test the installation"""
    print("\nTesting installation...")
    test_script = """
import sys
sys.path.append('.')
try:
    from app import create_app
    app = create_app()
    print("✓ Flask app creation successful")
    
    from app.services.pdf_processor import PDFProcessor
    print("✓ PDF processor import successful")
    
    from app.services.layout_detector import LayoutDetector
    print("✓ Layout detector import successful")
    
    print("✓ All imports successful - installation appears to be working!")
except Exception as e:
    print(f"✗ Installation test failed: {e}")
    sys.exit(1)
"""
    
    with open("test_install.py", "w") as f:
        f.write(test_script)
    
    success = run_command("python test_install.py", "Testing installation")
    
    # Clean up test file
    if os.path.exists("test_install.py"):
        os.remove("test_install.py")
    
    return success

def main():
    """Main installation function"""
    print("PDF Recognition API Setup")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Check for CUDA
    use_gpu = check_cuda()
    
    # Ask user preference for GPU usage
    if use_gpu:
        choice = input("\nGPU detected. Install with GPU support? (y/n) [y]: ").lower()
        use_gpu = choice != 'n'
    
    print(f"\nInstalling with {'GPU' if use_gpu else 'CPU'} support...")
    
    # Update pip
    print("\nUpdating pip...")
    run_command("python -m pip install --upgrade pip", "Updating pip")
    
    # Install PyTorch first
    if not install_pytorch(use_gpu):
        print("Failed to install PyTorch. Aborting.")
        sys.exit(1)
    
    # Install PaddlePaddle
    if not install_paddlepaddle(use_gpu):
        print("Failed to install PaddlePaddle. Aborting.")
        sys.exit(1)
    
    # Install other requirements
    if not install_requirements():
        print("Failed to install some dependencies. Please check the output above.")
        sys.exit(1)
    
    # Create necessary directories
    create_directories()
    
    # Download models (optional)
    download_choice = input("\nDownload PaddleOCR models now? (y/n) [y]: ").lower()
    if download_choice != 'n':
        download_models()
    
    # Test installation
    if test_installation():
        print("\n" + "=" * 50)
        print("INSTALLATION SUCCESSFUL!")
        print("=" * 50)
        print("\nTo start the server, run:")
        print("  python main.py")
        print("\nAPI documentation will be available at:")
        print("  http://localhost:5000/api/docs/")
        print("\nFor troubleshooting, see README.md")
    else:
        print("\nInstallation completed with warnings. Check the output above.")

if __name__ == "__main__":
    main()