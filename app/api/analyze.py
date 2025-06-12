from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import os
import tempfile
from typing import Dict, Any
from config import Config
from app.services.pdf_processor import PDFProcessor
from app.services.layout_detector import LayoutDetector
from app.services.reference_extractor import ReferenceExtractor

api = Namespace('analyze', description='PDF analysis operations')

# API Models for Swagger documentation
bbox_model = api.model('BoundingBox', {
    'x': fields.Integer(description='X coordinate'),
    'y': fields.Integer(description='Y coordinate'),
    'width': fields.Integer(description='Width'),
    'height': fields.Integer(description='Height')
})

text_block_model = api.model('TextBlock', {
    'text': fields.String(description='Extracted text'),
    'bbox': fields.Nested(bbox_model, description='Bounding box coordinates')
})

reference_model = api.model('Reference', {
    'bbox': fields.Nested(bbox_model, description='Bounding box coordinates'),
    'text': fields.String(description='Reference text'),
    'figure_id': fields.String(description='Referenced figure ID')
})

figure_model = api.model('Figure', {
    'bbox': fields.Nested(bbox_model, description='Bounding box coordinates'),
    'page_idx': fields.Integer(description='Page index'),
    'figure_id': fields.String(description='Figure ID'),
    'type': fields.String(description='Figure type')
})

page_model = api.model('Page', {
    'index': fields.Integer(description='Page index'),
    'page_size': fields.List(fields.Integer, description='Page size (width, height)'),
    'blocks': fields.List(fields.Nested(text_block_model), description='Text blocks'),
    'references': fields.List(fields.Nested(reference_model), description='References')
})

metadata_model = api.model('Metadata', {
    'title': fields.String(description='Document title'),
    'author': fields.String(description='Document author'),
    'pages': fields.Integer(description='Number of pages')
})

pdf_result_model = api.model('PDFResult', {
    'metadata': fields.Nested(metadata_model, description='PDF metadata'),
    'pages': fields.List(fields.Nested(page_model), description='Pages'),
    'figures': fields.List(fields.Nested(figure_model), description='Figures')
})

upload_parser = api.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='PDF file to analyze')

@api.route('/analyze')
class AnalyzeAPI(Resource):
    @api.expect(upload_parser)
    @api.marshal_with(pdf_result_model)
    @api.doc('analyze_pdf')
    @api.response(200, 'Success')
    @api.response(400, 'Bad Request - Invalid file format or size')
    @api.response(500, 'Internal Server Error')
    def post(self):
        """Analyze PDF file for layout, OCR, and figure-reference mapping"""
        try:
            # Validate file upload
            if 'file' not in request.files:
                api.abort(400, 'No file provided')
            
            file = request.files['file']
            if file.filename == '':
                api.abort(400, 'No file selected')
            
            # Validate file extension
            if not self._allowed_file(file.filename):
                api.abort(400, 'Only PDF files are allowed')
            
            # Validate file size
            if not self._validate_file_size(file):
                api.abort(400, f'File size exceeds {Config.MAX_CONTENT_LENGTH // (1024*1024)}MB limit')
            
            # Save uploaded file temporarily
            temp_pdf_path = self._save_temp_file(file)
            
            try:
                # Process PDF
                result = self._process_pdf(temp_pdf_path)
                
                # Cleanup temporary files
                self._cleanup_files([temp_pdf_path] + result.get('temp_image_paths', []))
                
                # Remove temp paths from result before returning
                if 'temp_image_paths' in result:
                    del result['temp_image_paths']
                
                return result, 200
                
            except Exception as e:
                # Cleanup on error
                self._cleanup_files([temp_pdf_path])
                api.abort(500, f'Processing error: {str(e)}')
                
        except Exception as e:
            api.abort(500, f'Server error: {str(e)}')
    
    def _allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    
    def _validate_file_size(self, file: FileStorage) -> bool:
        """Validate file size"""
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        return size <= Config.MAX_CONTENT_LENGTH
    
    def _save_temp_file(self, file: FileStorage) -> str:
        """Save uploaded file to temporary location"""
        filename = secure_filename(file.filename)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        file.save(temp_file.name)
        return temp_file.name
    
    def _process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Process PDF file and return structured results"""
        # Initialize services
        pdf_processor = PDFProcessor(dpi=Config.DPI)
        layout_detector = LayoutDetector(
            use_gpu=Config.OCR_USE_GPU,
            lang=Config.OCR_LANG
        )
        reference_extractor = ReferenceExtractor()
        
        # Process PDF to get pages and images
        pdf_result = pdf_processor.process_pdf(pdf_path)
        
        if 'error' in pdf_result:
            raise Exception(pdf_result['error'])
        
        # Process each page for layout and text detection
        for page in pdf_result['pages']:
            if page['image_path']:
                # Detect layout and extract text
                detection_result = layout_detector.detect_layout_and_text(page['image_path'])
                
                # Update page with detection results
                page['blocks'] = detection_result.get('text_blocks', [])
                
                # Extract references from text blocks
                references = reference_extractor.extract_references(page['blocks'])
                page['references'] = references
                
                # Extract figures from layout blocks
                layout_blocks = detection_result.get('layout_blocks', [])
                page_figures = self._extract_figures_from_layout(layout_blocks, page['index'])
                pdf_result['figures'].extend(page_figures)
        
        return pdf_result
    
    def _extract_figures_from_layout(self, layout_blocks: list, page_idx: int) -> list:
        """Extract figure information from layout blocks"""
        figures = []
        figure_types = ['figure', 'image', 'chart', 'graph']
        
        for block in layout_blocks:
            if block.get('type', '').lower() in figure_types:
                figure = {
                    'bbox': block['bbox'],
                    'page_idx': page_idx,
                    'figure_id': self._extract_figure_id(block.get('text', '')),
                    'type': block['type']
                }
                figures.append(figure)
        
        return figures
    
    def _extract_figure_id(self, text: str) -> str:
        """Extract figure ID from text"""
        import re
        if not text:
            return ""
        
        patterns = [
            r'fig\.?(?:ure)?\s*(\d+(?:\.\d+)*)',
            r'图\s*(\d+(?:\.\d+)*)'
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1)
        
        return ""
    
    def _cleanup_files(self, file_paths: list):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting file {file_path}: {str(e)}")