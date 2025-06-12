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
from app.services.figure_id_generator import FigureIDGenerator
from app.services.figure_mapper import FigureMapper

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
    'figure_id': fields.String(description='Referenced figure ID', required=False),
    'not_matched': fields.Boolean(description='True if reference not matched to any figure', required=False)
})

figure_model = api.model('Figure', {
    'bbox': fields.Nested(bbox_model, description='Bounding box coordinates'),
    'page_idx': fields.Integer(description='Page index'),
    'figure_id': fields.String(description='Figure ID'),
    'type': fields.String(description='Figure type'),
    'text': fields.String(description='Figure caption or text')
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
                
                # Remove temp paths and pp_structure from result before returning
                if 'temp_image_paths' in result:
                    del result['temp_image_paths']
                if 'pp_structure' in result:
                    del result['pp_structure']
                
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
        """Process PDF file using refactored logic"""
        # Step 1: Initialize PDF processor with PP-StructureV3
        pdf_processor = PDFProcessor(
            dpi=Config.DPI,
            use_gpu=Config.OCR_USE_GPU
        )
        
        # Process PDF to get pages and PP-StructureV3 instance
        pdf_result = pdf_processor.process_pdf(pdf_path)
        
        if 'error' in pdf_result:
            raise Exception(pdf_result['error'])
        
        # Get PP-StructureV3 instance
        pp_structure = pdf_result.get('pp_structure')
        
        # Initialize services
        layout_detector = LayoutDetector(pp_structure)
        figure_id_generator = FigureIDGenerator()
        reference_extractor = ReferenceExtractor()
        figure_mapper = FigureMapper()
        
        # Collect all figures
        all_figures = []
        
        # Process each page
        for page in pdf_result['pages']:
            if not page['image_path']:
                continue
            
            # Step 2: Detect layout and text
            detection_result = layout_detector.detect_layout_and_text(page['image_path'])
            text_blocks = detection_result.get('text_blocks', [])
            layout_blocks = detection_result.get('layout_blocks', [])
            
            # Update page with text blocks
            page['blocks'] = text_blocks
            
            # Step 3: Generate figure IDs for layout blocks
            for layout_block in layout_blocks:
                figure_info = figure_id_generator.generate_figure_info(
                    layout_block, 
                    page['index']
                )
                all_figures.append(figure_info)
            
            # Step 4: Extract references from text blocks
            references = reference_extractor.extract_references(text_blocks)
            
            # Step 5-7: Map references to figures
            mapped_references = figure_mapper.map_references_to_figures(
                references, 
                all_figures
            )
            
            page['references'] = mapped_references
        
        # Add all figures to result
        pdf_result['figures'] = all_figures
        
        return pdf_result
    
    def _cleanup_files(self, file_paths: list):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting file {file_path}: {str(e)}")