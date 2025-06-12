# PDF Layout Analysis API

A Flask-based API for PDF layout analysis using YOLO-DocLayout. This application can detect and visualize different document elements like text, tables, figures, captions, and more.

## Features

- **Layout Detection**: Uses YOLO-DocLayout to detect various document elements
- **PDF Processing**: Converts PDF pages to images for analysis
- **Visualization**: Creates annotated images with bounding boxes and labels
- **REST API**: Flask-RESTX powered API with Swagger documentation
- **Web Interface**: Simple HTML test page for easy testing

## Detected Elements

The system can detect the following layout elements:
- Caption
- Footnote
- Formula
- List-item
- Page-footer
- Page-header
- Picture
- Section-header
- Table
- Text
- Title

## Installation

1. **Clone or download the project**
2. **Install Python dependencies with GPU support**:
   ```bash
   # For CUDA 12.1 (RTX 3090 compatible)
   pip install --extra-index-url https://download.pytorch.org/whl/cu121 -r requirements.txt
   ```
   Or use the setup script:
   ```bash
   python setup.py
   ```
3. **Download YOLO-DocLayout model**:
   - Visit: https://github.com/opendatalab/DocLayout-YOLO
   - Download the model file and place it in the `models/` directory as `yolo_doclayout_model.pt`

## Configuration

Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
```

Key configuration options:
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 5000)
- `DEVICE`: Processing device (cuda/cpu)
- `YOLO_MODEL_PATH`: Path to YOLO model file

## Usage

### Start the Server

```bash
python main.py
```

The server will start on `http://localhost:5000`

### API Endpoints

#### 1. Upload and Analyze PDF
```
POST /api/v1/analyze/upload
```

**Parameters:**
- `file`: PDF file (multipart/form-data)
- `page_index`: Optional page index to analyze specific page

**Response:**
```json
{
  "success": true,
  "message": "PDF analyzed successfully",
  "pdf_metadata": {
    "title": "Document Title",
    "page_count": 10
  },
  "pages": [
    {
      "page_index": 0,
      "width": 595.0,
      "height": 842.0,
      "detections": [
        {
          "bbox": {"x": 100, "y": 200, "width": 300, "height": 50},
          "confidence": 0.95,
          "class_name": "Text",
          "type": "Text"
        }
      ],
      "visualization_image": "data:image/png;base64,..."
    }
  ]
}
```

#### 2. Health Check
```
GET /api/v1/analyze/health
```

### Web Interface

- **Test Page**: `http://localhost:5000/` - Upload and test PDFs
- **Swagger UI**: `http://localhost:5000/swagger/` - API documentation

## Project Structure

```
pdfrec/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── api/
│   │   ├── __init__.py
│   │   └── analyze.py           # API endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pdf_processor.py     # PDF processing
│   │   ├── layout_detector.py   # YOLO layout detection
│   │   └── visualizer.py        # Visualization functions
│   └── templates/
│       └── test.html            # Test page
├── models/                      # Model files directory
├── uploads/                     # Temporary upload directory
├── temp/                       # Temporary processing files
├── config.py                   # Configuration
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── setup.py                    # Setup script
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## Requirements

### System Requirements
- Python 3.10+
- CUDA 12.9 (for GPU acceleration)
- 8GB+ RAM recommended

### Python Dependencies
- Flask 2.3.3
- flask-restx 1.2.0
- PyMuPDF 1.23.8
- Pillow 10.1.0
- opencv-python 4.8.1.78
- ultralytics 8.0.206
- torch 2.0.1
- transformers 4.35.2

## API Usage Examples

### Using curl
```bash
# Analyze entire PDF
curl -X POST -F "file=@document.pdf" http://localhost:5000/api/v1/analyze/upload

# Analyze specific page (page 0)
curl -X POST -F "file=@document.pdf" -F "page_index=0" http://localhost:5000/api/v1/analyze/upload
```

### Using Python requests
```python
import requests

# Upload and analyze PDF
with open('document.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:5000/api/v1/analyze/upload', files=files)
    result = response.json()
    
if result['success']:
    print(f"Analyzed {len(result['pages'])} pages")
    for page in result['pages']:
        print(f"Page {page['page_index']}: {len(page['detections'])} elements detected")
```

## Troubleshooting

1. **Model not found error**: Download the YOLO-DocLayout model and place it in `models/yolo_doclayout_model.pt`
2. **CUDA out of memory**: Set `DEVICE=cpu` in `.env` file
3. **File upload errors**: Check file size limit (50MB default)
4. **Permission errors**: Ensure write permissions for `uploads/` and `temp/` directories

## License

This project is for educational and research purposes.