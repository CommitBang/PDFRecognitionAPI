import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Server Configuration
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'pdf'}
    UPLOAD_FOLDER = 'uploads'
    TEMP_FOLDER = 'temp'
    
    # Model Configuration
    YOLO_MODEL_PATH = os.getenv('YOLO_MODEL_PATH', 'yolo_doclayout_model.pt')
    TROCR_MODEL_NAME = os.getenv('TROCR_MODEL_NAME', 'microsoft/trocr-base-printed')
    LAYOUTLM_MODEL_NAME = os.getenv('LAYOUTLM_MODEL_NAME', 'microsoft/layoutlmv2-base-uncased')
    
    # Processing Configuration
    DPI = int(os.getenv('DPI', 300))
    DEVICE = os.getenv('DEVICE', 'cuda' if os.path.exists('/usr/local/cuda') else 'cpu')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')