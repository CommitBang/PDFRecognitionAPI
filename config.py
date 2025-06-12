import os

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Server settings
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT') or 5000)
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH') or 50) * 1024 * 1024  # 50MB default
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'temp_uploads'
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Model settings
    OCR_MODEL = os.environ.get('OCR_MODEL') or 'paddleocr'
    LAYOUT_MODEL = os.environ.get('LAYOUT_MODEL') or 'paddleocr'
    CLASSIFICATION_MODEL = os.environ.get('CLASSIFICATION_MODEL') or 'microsoft/layoutlmv2-base-uncased'
    
    # PaddleOCR settings
    OCR_USE_ANGLE_CLS = os.environ.get('OCR_USE_ANGLE_CLS', 'True').lower() == 'true'
    OCR_LANG = os.environ.get('OCR_LANG') or 'en'
    OCR_USE_GPU = os.environ.get('OCR_USE_GPU', 'True').lower() == 'true'
    
    # Processing settings
    DPI = int(os.environ.get('DPI') or 300)
    IMAGE_FORMAT = os.environ.get('IMAGE_FORMAT') or 'RGB'
    
    # CUDA settings
    CUDA_DEVICE = os.environ.get('CUDA_DEVICE') or '0'
    
    @staticmethod
    def init_app(app):
        pass