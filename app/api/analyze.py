from flask import request, jsonify, send_file
from flask_restx import Namespace, Resource, fields
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import os
import tempfile
import uuid
from typing import Dict, Any

from app.services.pdf_processor import PDFProcessor
from app.services.layout_detector import LayoutDetector
from app.services.visualizer import LayoutVisualizer
from config import Config

# Create namespace
api = Namespace('analyze', description='PDF Layout Analysis Operations')

# Define models for Swagger documentation
bbox_model = api.model('BoundingBox', {
    'x': fields.Integer(required=True, description='X coordinate'),
    'y': fields.Integer(required=True, description='Y coordinate'),
    'width': fields.Integer(required=True, description='Width'),
    'height': fields.Integer(required=True, description='Height')
})

detection_model = api.model('Detection', {
    'bbox': fields.Nested(bbox_model, required=True, description='Bounding box'),
    'confidence': fields.Float(required=True, description='Detection confidence'),
    'class_id': fields.Integer(required=True, description='Class ID'),
    'class_name': fields.String(required=True, description='Class name'),
    'type': fields.String(required=True, description='Element type')
})

page_info_model = api.model('PageInfo', {
    'page_index': fields.Integer(required=True, description='Page index'),
    'width': fields.Float(required=True, description='Page width'),
    'height': fields.Float(required=True, description='Page height'),
    'detections': fields.List(fields.Nested(detection_model), description='Layout detections'),
    'visualization_image': fields.String(description='Base64 encoded visualization image')
})

analysis_result_model = api.model('AnalysisResult', {
    'success': fields.Boolean(required=True, description='Success status'),
    'message': fields.String(description='Status message'),
    'pdf_metadata': fields.Raw(description='PDF metadata'),
    'pages': fields.List(fields.Nested(page_info_model), description='Page analysis results'),
    'total_pages': fields.Integer(description='Total number of pages')
})

error_model = api.model('Error', {
    'success': fields.Boolean(required=True, description='Success status'),
    'error': fields.String(required=True, description='Error message')
})

# File upload parser
upload_parser = api.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='PDF file to analyze')
upload_parser.add_argument('page_index', type=int, required=False, help='Specific page to analyze (optional)')

@api.route('/upload')
class PDFUpload(Resource):
    @api.expect(upload_parser)
    @api.doc('upload_pdf')
    @api.response(200, 'Success', analysis_result_model)
    @api.response(400, 'Bad Request', error_model)
    @api.response(500, 'Internal Server Error', error_model)
    def post(self):
        """
        Upload and analyze PDF file
        """
        try:
            # Check if file is present
            if 'file' not in request.files:
                return {'success': False, 'error': 'No file provided'}, 400
            
            file = request.files['file']
            if file.filename == '':
                return {'success': False, 'error': 'No file selected'}, 400
            
            # Validate file extension
            if not self._allowed_file(file.filename):
                return {'success': False, 'error': 'Only PDF files are allowed'}, 400
            
            # Get optional page index
            page_index = request.form.get('page_index')
            if page_index is not None:
                try:
                    page_index = int(page_index)
                except ValueError:
                    return {'success': False, 'error': 'Invalid page index'}, 400
            
            # Save uploaded file
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            upload_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
            file.save(upload_path)
            
            try:
                # Initialize services
                pdf_processor = PDFProcessor()
                layout_detector = LayoutDetector()
                visualizer = LayoutVisualizer()
                
                # Process PDF
                result = self._analyze_pdf(
                    upload_path, 
                    pdf_processor, 
                    layout_detector, 
                    visualizer,
                    page_index
                )
                
                return result, 200
                
            finally:
                # Clean up uploaded file
                if os.path.exists(upload_path):
                    os.remove(upload_path)
                    
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500
    
    def _allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    
    def _analyze_pdf(self, pdf_path: str, pdf_processor: PDFProcessor, 
                    layout_detector: LayoutDetector, visualizer: LayoutVisualizer,
                    specific_page: int = None) -> Dict[str, Any]:
        """Analyze PDF and return results"""
        
        # Get PDF metadata
        metadata = pdf_processor.get_pdf_metadata(pdf_path)
        
        # Convert PDF to images
        page_images = pdf_processor.pdf_to_images(pdf_path)
        
        # Filter to specific page if requested
        if specific_page is not None:
            if specific_page < 0 or specific_page >= len(page_images):
                raise ValueError(f"Page index {specific_page} out of range. PDF has {len(page_images)} pages.")
            page_images = [page_images[specific_page]]
        
        pages_result = []
        
        for image_array, page_info in page_images:
            # Detect layout
            detections = layout_detector.detect_layout(image_array)
            
            # Create visualization
            viz_image = visualizer.draw_bounding_boxes(image_array, detections)
            viz_base64 = visualizer.image_to_base64(viz_image)
            
            page_result = {
                'page_index': page_info['page_index'],
                'width': page_info['width'],
                'height': page_info['height'],
                'detections': detections,
                'visualization_image': viz_base64,
                'detection_summary': visualizer.create_visualization_summary(detections)
            }
            
            pages_result.append(page_result)
        
        return {
            'success': True,
            'message': 'PDF analyzed successfully',
            'pdf_metadata': metadata,
            'pages': pages_result,
            'total_pages': metadata['page_count'],
            'analyzed_pages': len(pages_result)
        }

@api.route('/health')
class Health(Resource):
    @api.doc('health_check')
    def get(self):
        """Health check endpoint"""
        return {'status': 'healthy', 'message': 'PDF Layout Analysis API is running'}