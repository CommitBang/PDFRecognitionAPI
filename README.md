# PDF Recognition API

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-3.0+-orange.svg)](https://github.com/PaddlePaddle/PaddleOCR)
[![License](https://img.shields.io/badge/License-APACH-yellow.svg)](LICENSE)

A powerful Flask-based REST API for intelligent PDF document analysis, featuring advanced layout detection, OCR, and AI-powered figure-reference mapping with type awareness.

## 🌟 Key Features

### 📄 **Comprehensive PDF Analysis**
- **Multi-page Processing**: Handle large PDF documents with automatic page-by-page analysis
- **Metadata Extraction**: Extract document metadata (title, author, creation date, etc.)
- **High-Quality Conversion**: Convert PDF pages to images with configurable DPI

### 🔍 **Advanced Layout Detection**
- **Element Recognition**: Detect figures, tables, formulas, algorithms, titles, and captions
- **Intelligent Grouping**: Automatically group related elements (e.g., figure + title + caption)
- **Spatial Analysis**: Use spatial relationships and alignment patterns for accurate grouping
- **Multi-Strategy Approach**: Combine ID-based, pattern-based, and proximity-based grouping

### 📝 **Intelligent Text Processing**
- **High-Accuracy OCR**: Extract text with bounding box coordinates using PaddleOCR
- **Type-Aware Reference Extraction**: Identify and classify references (Fig. 1, Table 2, Eq. (3), etc.)
- **Multi-Language Support**: Support for English and other languages

### 🔗 **AI-Powered Reference Mapping**
- **Graph-Based Mapping**: Use NetworkX for intelligent figure-reference relationship inference
- **Type-Aware Matching**: Match references to figures based on type compatibility
- **Confidence Scoring**: Provide confidence scores for mappings
- **Spatial Context**: Consider document layout and proximity for better accuracy

### 🚀 **Production-Ready API**
- **RESTful Design**: Clean, well-documented API endpoints
- **Interactive Documentation**: Built-in Swagger UI for easy testing
- **GPU Acceleration**: Optional CUDA support for faster processing
- **Error Handling**: Robust error handling and validation
- **Test Interface**: Built-in web interface for testing and visualization

## 🏗️ Architecture

```
PDF Recognition API
├── 📁 app/
│   ├── 📁 api/           # REST API endpoints
│   ├── 📁 services/      # Core processing services
│   │   ├── pdf_processor.py       # Main PDF processing pipeline
│   │   ├── layout_detector.py     # PaddleOCR-based layout detection
│   │   ├── figure_grouper.py      # Intelligent element grouping
│   │   ├── figure_id_generator.py # Figure ID extraction & generation
│   │   ├── reference_extractor.py # Reference detection & classification
│   │   └── figure_mapper.py       # Graph-based figure-reference mapping
│   └── 📁 templates/     # Web interface templates
├── 📄 config.py         # Configuration management
├── 📄 main.py           # Application entry point
└── 📄 requirements.txt  # Dependencies
```

## 🔧 Installation

### Prerequisites

- **Python 3.9+** (3.9-3.11 recommended for best compatibility)
- **CUDA 12.9** (optional, for GPU acceleration)
- **64GB RAM** (recommended for large documents)

### Quick Install with Setup Script

```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-recognition-api.git
cd pdf-recognition-api

# Run automated setup (recommended)
python setup.py
```

### Manual Installation

```bash
# Create virtual environment
conda create -n pdfrec python=3.9
conda activate pdfrec

# Install dependencies
pip install -r requirements.txt

# For GPU support (optional)
pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu123/
```

### Docker Installation (Coming Soon)

```bash
# Build and run with Docker
docker build -t pdf-recognition-api .
docker run -p 5000:5000 pdf-recognition-api
```

## 🚀 Quick Start

### 1. Start the Server

```bash
python main.py
```

The API will be available at `http://localhost:5000`

### 2. Interactive Documentation

Visit `http://localhost:5000/api/docs/` for Swagger UI documentation and testing interface.

### 3. Test Interface

Visit `http://localhost:5000/` for a user-friendly web interface to test PDF analysis with visualization.

### 4. API Usage

#### Upload and Analyze PDF

```bash
curl -X POST \
  http://localhost:5000/api/v1/analyze \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@your_document.pdf'
```

#### Python Example

```python
import requests

# Upload PDF for analysis
url = "http://localhost:5000/api/v1/analyze"
with open("document.pdf", "rb") as file:
    files = {"file": file}
    response = requests.post(url, files=files)

result = response.json()

# Access results
print(f"Document: {result['metadata']['title']}")
print(f"Pages: {len(result['pages'])}")
print(f"Figures detected: {len(result['figures'])}")

# Check mapping statistics
stats = result.get('mapping_statistics', {})
print(f"Reference mapping: {stats['matched_references']}/{stats['total_references']} matched")
```

## 📊 API Response Format

The API returns a comprehensive JSON structure:

```json
{
  "metadata": {
    "title": "Document Title",
    "author": "Author Name",
    "pages": 10
  },
  "pages": [
    {
      "index": 0,
      "page_size": [595, 842],
      "blocks": [
        {
          "text": "Extracted text content",
          "bbox": {"x": 100, "y": 200, "width": 150, "height": 20},
          "confidence": 0.95
        }
      ],
      "references": [
        {
          "text": "Fig. 1",
          "bbox": {"x": 50, "y": 100, "width": 40, "height": 15},
          "figure_id": "1",
          "reference_type": "figure",
          "not_matched": false
        }
      ]
    }
  ],
  "figures": [
    {
      "figure_id": "1",
      "type": "figure",
      "reference_type": "figure",
      "bbox": {"x": 100, "y": 300, "width": 200, "height": 150},
      "page_idx": 0,
      "text": "Figure 1: Sample caption",
      "confidence": 0.92,
      "elements": [...],
      "grouping_method": "multi_strategy"
    }
  ],
  "mapping_statistics": {
    "total_references": 15,
    "matched_references": 13,
    "match_rate": 0.867
  },
  "type_statistics": {
    "figures_by_type": {"figure": 5, "table": 3, "equation": 2},
    "matching_by_type": {
      "figure": {"matched": 4, "total": 5, "rate": 0.8}
    }
  }
}
```

## ⚙️ Configuration

Configure the API through environment variables or `config.py`:

```python
# Server settings
HOST = "0.0.0.0"
PORT = 5000
DEBUG = False

# Processing settings
OCR_USE_GPU = True          # Enable GPU acceleration
DPI = 300                   # Image conversion DPI
MAX_CONTENT_LENGTH = 50     # Max file size (MB)

# PaddleOCR settings
OCR_LANG = "en"            # OCR language
OCR_USE_ANGLE_CLS = True   # Enable text angle detection
```

## 🎯 Use Cases

### Academic Research
- **Paper Analysis**: Extract figures, tables, and equations from research papers
- **Reference Validation**: Verify figure references in academic documents
- **Citation Analysis**: Analyze document structure and references

### Document Processing
- **Technical Documentation**: Process manuals, reports, and specifications
- **Content Migration**: Extract structured content for digital transformation
- **Quality Assurance**: Validate document formatting and references

### Publishing & Editorial
- **Manuscript Review**: Analyze document structure and references
- **Content Extraction**: Extract figures and tables for reuse
- **Format Validation**: Ensure proper figure numbering and referencing

## 🧪 Features

### Type-Aware Processing

The API intelligently recognizes and processes different element types:

- **Figures**: Images, charts, diagrams
- **Tables**: Data tables with captions
- **Equations**: Mathematical formulas with numbering
- **Algorithms**: Pseudocode blocks
- **Examples**: Code snippets and examples

### Intelligent Grouping

Advanced grouping strategies combine multiple approaches:

1. **ID-Based Grouping**: Match elements with same identifier
2. **Pattern Matching**: Recognize common layout patterns
3. **Spatial Analysis**: Use proximity and alignment
4. **Type Compatibility**: Ensure logical element relationships

### Graph-Based Mapping

The reference mapping system uses NetworkX to:
- Model document structure as a graph
- Calculate relationship probabilities
- Perform intelligent inference
- Provide confidence scores

## 🛠️ Development

### Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/yourusername/pdf-recognition-api.git
cd pdf-recognition-api

# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-flask black flake8

# Run tests
pytest tests/

# Format code
black app/
flake8 app/
```

### Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_api.py          # API tests
pytest tests/test_services.py     # Service tests
pytest tests/test_integration.py  # Integration tests

# Run with coverage
pytest --cov=app tests/
```

## 🐛 Troubleshooting

### Common Issues

**1. CUDA Out of Memory**
```bash
# Solution: Use CPU mode or reduce DPI
export OCR_USE_GPU=False
export DPI=150
```

**2. Model Download Issues**
```bash
# Models are downloaded automatically on first run
# Ensure stable internet connection
# Models are cached in ~/.paddlex/
```

**3. PDF Processing Errors**
```bash
# Check file permissions and format
# Ensure PDF is not corrupted or password-protected
# Try reducing DPI for large files
```

**4. Installation Issues**
```bash
# For Python 3.12+ compatibility issues
conda create -n pdfrec python=3.9
conda activate pdfrec

# For PyMuPDF errors
pip install PyMuPDF==1.24.0
```

## 📚 API Documentation

### Endpoints

#### `POST /api/v1/analyze`
Analyze a PDF document and extract structured information.

**Parameters:**
- `file` (required): PDF file to analyze (max 50MB)

**Response:** JSON object with document analysis results

#### `GET /api/docs/`
Interactive Swagger documentation

#### `GET /`
Web-based test interface

### Response Codes

- `200`: Success
- `400`: Bad request (invalid file, size limit exceeded)
- `500`: Server error (processing failure)

## 📄 License

This project is licensed under the APACH License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PaddleOCR Team**: For the excellent OCR framework
- **Flask Community**: For the robust web framework
- **PyMuPDF Developers**: For PDF processing capabilities
- **NetworkX Team**: For graph analysis tools

## 🗺️ Roadmap

### Upcoming Features

- [ ] **Multi-language OCR**: Enhanced support for non-English documents
- [ ] **Table Structure Recognition**: Detailed table cell extraction
- [ ] **Formula Recognition**: Mathematical formula parsing
- [ ] **Batch Processing**: Process multiple PDFs simultaneously
- [ ] **Cloud Storage Integration**: Support for S3, GCS, Azure Blob
- [ ] **Performance Optimization**: Faster processing algorithms
- [ ] **Export Formats**: XML, JSON-LD, CSV export options