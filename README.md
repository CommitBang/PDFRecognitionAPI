# PDF Recognition API

A Flask-based REST API for PDF document analysis using PaddleOCR for layout detection and text recognition.

## Features

- **PDF Processing**: Convert PDF pages to images for analysis
- **Layout Detection**: Identify different document elements (text, figures, tables, etc.)
- **Text Recognition**: Extract text with bounding box coordinates using OCR
- **REST API**: RESTful endpoints with Swagger documentation
- **GPU Acceleration**: Optional GPU support for faster processing

## System Requirements

### Hardware Requirements
- **Windows 11** (as specified in requirements)
- **NVIDIA RTX 3090** with CUDA 12.9
- **64GB RAM**
- **AMD Ryzen 7 5700X** (8 cores)

### Software Requirements
- **Python 3.9** (recommended for best compatibility)
- **CUDA 12.9** (for GPU acceleration)
- **Anaconda** (recommended for environment management)

## Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd pdfrec
```

### 2. Create Virtual Environment
```bash
# Using Anaconda (recommended)
conda create -n pdfrec python=3.9
conda activate pdfrec

# Or using venv
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

#### Option A: Using setup.py (Recommended)
```bash
python setup.py install
```

#### Option B: Using pip
```bash
pip install -r requirements.txt
```

#### Option C: For CPU-only installation (no GPU)
```bash
# Install CPU-only PyTorch first
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### 4. Environment Configuration (Optional)
Create a `.env` file in the project root:
```env
# Server settings
HOST=0.0.0.0
PORT=5000
DEBUG=False

# File upload settings
MAX_CONTENT_LENGTH=50  # MB
UPLOAD_FOLDER=temp_uploads

# OCR settings
OCR_USE_GPU=True
OCR_LANG=en
DPI=300

# CUDA settings
CUDA_DEVICE=0
```

## Usage

### 1. Start the Server
```bash
python main.py
```

The server will start at `http://localhost:5000`

### 2. API Documentation
Access Swagger documentation at: `http://localhost:5000/api/docs/`

### 3. API Endpoints

#### POST /api/v1/analyze
Upload and analyze a PDF file.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: PDF file (max 50MB)

**Response:**
```json
{
  "metadata": {
    "title": "Document Title",
    "author": "Author Name",
    "pages": 5
  },
  "pages": [
    {
      "index": 0,
      "page_size": [595, 842],
      "blocks": [
        {
          "text": "Extracted text content",
          "bbox": {
            "x": 100,
            "y": 200,
            "width": 150,
            "height": 20
          }
        }
      ],
      "references": []
    }
  ],
  "figures": [
    {
      "bbox": {
        "x": 100,
        "y": 300,
        "width": 200,
        "height": 150
      },
      "page_idx": 0,
      "figure_id": "1.1",
      "type": "figure"
    }
  ]
}
```

### 4. Example Usage with curl
```bash
curl -X POST \
  http://localhost:5000/api/v1/analyze \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@your_document.pdf'
```

### 5. Example Usage with Python
```python
import requests

url = "http://localhost:5000/api/v1/analyze"
files = {"file": open("your_document.pdf", "rb")}

response = requests.post(url, files=files)
result = response.json()

print(f"Detected {len(result['figures'])} figures")
print(f"Extracted text from {len(result['pages'])} pages")
```

## Configuration

All configuration options are available in `config.py` and can be overridden using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| HOST | 0.0.0.0 | Server host |
| PORT | 5000 | Server port |
| DEBUG | False | Debug mode |
| MAX_CONTENT_LENGTH | 50MB | Maximum file upload size |
| OCR_USE_GPU | True | Enable GPU acceleration |
| OCR_LANG | en | OCR language |
| DPI | 300 | Image conversion DPI |

## Troubleshooting

### Common Issues

1. **PyMuPDF Installation Error**
   ```bash
   # If you encounter PyMuPDF errors, try:
   pip install PyMuPDF==1.20.2
   ```

2. **CUDA Out of Memory**
   - Reduce DPI setting in config
   - Process smaller PDF files
   - Use CPU-only mode by setting `OCR_USE_GPU=False`

3. **PaddleOCR Model Download**
   - On first run, PaddleOCR will download models automatically
   - Ensure stable internet connection
   - Models are cached locally after download

4. **Permission Errors**
   - Ensure write permissions for `temp_uploads` directory
   - Check firewall settings for the specified port

### Performance Optimization

1. **GPU Acceleration**: Ensure CUDA is properly installed and GPU memory is sufficient
2. **Memory Usage**: For large PDFs, consider processing page by page
3. **File Size**: Optimize PDF files before upload for better performance

## Development

### Running Tests
```bash
pytest tests/
```

### Adding Features
1. Add new services in `app/services/`
2. Create API endpoints in `app/api/`
3. Update configuration in `config.py`
4. Add tests in `tests/`

## API Response Format

The API returns structured data matching the specified format:

- **Reference**: Text references to figures with bounding boxes
- **Figure**: Detected figures with IDs and locations
- **TextBlock**: Text content with coordinates
- **Page**: Page-level information and content
- **Pdf**: Complete document analysis results

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Create an issue in the repository