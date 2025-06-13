# app/services/pdf_processor.py - Updated version
import fitz
import os
import io
from PIL import Image
from typing import List, Dict, Any
from paddleocr import PPStructureV3
import tempfile
import shutil
from app.services.layout_detector import LayoutDetector
from app.services.figure_grouper import FigureGrouper
from app.services.reference_extractor import ReferenceExtractor
from app.services.figure_mapper import FigureMapper

# Global PP-Structure instance to avoid reloading models
_pp_structure_instance = None

def get_pp_structure_instance(use_gpu: bool = True):
    """Get or create global PP-Structure instance"""
    global _pp_structure_instance
    if _pp_structure_instance is None:
        cache_dir = os.path.expanduser("~/.paddlex/official_models")
        if os.path.exists(cache_dir):
            print(f"Models cache found at: {cache_dir}")
            model_files = os.listdir(cache_dir)
            print(f"Cached models: {len(model_files)} files")
        else:
            print("No model cache found - models will be downloaded")
        
        print("Initializing PP-StructureV3 with lightweight models...")
        
        config_balanced = {
            'layout_detection_model_name': 'PP-DocLayout-M',
            'text_detection_model_name': 'PP-OCRv4_server_det',
            'text_recognition_model_name': 'PP-OCRv4_server_rec',
            
            'use_doc_orientation_classify': False,
            'use_doc_unwarping': False,
            'use_textline_orientation': False,
            'use_seal_recognition': False,
            'use_chart_recognition': False,
            'use_table_recognition': True,   # Keep for better table detection
            'use_formula_recognition': True,  # Keep for better formula detection
            
            'device': 'gpu' if use_gpu else 'cpu',
        }
        
        _pp_structure_instance = PPStructureV3(**config_balanced)
        print("PP-StructureV3 models loaded successfully!")
    else:
        print("Using cached PP-StructureV3 instance")
    return _pp_structure_instance

class PDFProcessor:
    def __init__(self, dpi: int = 150, use_gpu: bool = True, lang: str = 'en'):
        self.dpi = dpi
        # Use global PP-Structure instance to avoid reloading models
        self.pp_structure = get_pp_structure_instance(use_gpu)
        
        # Initialize services
        self.layout_detector = LayoutDetector(self.pp_structure)
        self.figure_grouper = FigureGrouper()
        self.reference_extractor = ReferenceExtractor()
        self.figure_mapper = FigureMapper()
    
    def extract_pdf_data(self, pdf_path: str) -> tuple[Dict[str, Any], List[Image.Image]]:
        """Extract metadata and convert PDF to images in single operation"""
        try:
            doc = fitz.open(pdf_path)
            
            # Extract metadata
            metadata = doc.metadata
            page_count = doc.page_count
            
            metadata_dict = {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'creator': metadata.get('creator', ''),
                'producer': metadata.get('producer', ''),
                'creation_date': metadata.get('creationDate', ''),
                'modification_date': metadata.get('modDate', ''),
                'pages': page_count
            }
            
            # Convert to images
            images = []
            # Calculate zoom factor from DPI
            zoom = self.dpi / 72.0  # 72 DPI is default
            mat = fitz.Matrix(zoom, zoom)
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                images.append(img)
                pix = None  # Free memory
            
            doc.close()
            return metadata_dict, images
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return {}, []
    
    def save_temp_image(self, image: Image.Image, prefix: str = "page_") -> str:
        """Save PIL Image to temporary file and return path"""
        try:
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='.png', 
                prefix=prefix
            )
            image.save(temp_file.name, 'PNG')
            return temp_file.name
        except Exception as e:
            print(f"Error saving temporary image: {str(e)}")
            return ""
    
    def cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting temporary file {file_path}: {str(e)}")
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Main method to process PDF and return structured data"""
        try:
            # Extract metadata and convert to images in single operation
            metadata, images = self.extract_pdf_data(pdf_path)
            
            if not images:
                raise Exception("Failed to convert PDF to images")
            
            # Prepare result structure
            result = {
                'metadata': metadata,
                'pages': [],
                'figures': [],
                'temp_image_paths': [],
                'processing_info': {
                    'total_layout_blocks': 0,
                    'grouped_figures': 0,
                    'matched_references': 0,
                    'unmatched_references': 0
                }
            }
            
            # Track page mapping for references
            page_mapping = {}  # Maps page_idx to figure indices on that page
            
            # Process each page
            for page_idx, image in enumerate(images):
                page_size = image.size
                temp_image_path = self.save_temp_image(image, f"page_{page_idx}_")
                
                if temp_image_path:
                    result['temp_image_paths'].append(temp_image_path)
                
                # Step 1: Detect layout and text from current page
                detection_result = self.layout_detector.detect_layout_and_text(temp_image_path)
                text_blocks = detection_result.get('text_blocks', [])
                layout_blocks = detection_result.get('layout_blocks', [])
                
                result['processing_info']['total_layout_blocks'] += len(layout_blocks)
                
                # Step 2: Group related layout elements into complete figures
                grouped_figures = self.figure_grouper.group_figure_elements(layout_blocks, page_idx)
                result['processing_info']['grouped_figures'] += len(grouped_figures)
                
                # Track figure indices for this page
                page_figure_indices = []
                for figure in grouped_figures:
                    page_figure_indices.append(len(result['figures']))
                    result['figures'].append(figure)
                
                page_mapping[page_idx] = page_figure_indices
                
                # Step 3: Extract references from text blocks
                references = self.reference_extractor.extract_references(text_blocks)
                
                # Step 4: Map references to figures with enhanced mapping
                mapped_references = self.figure_mapper.map_references_to_figures(
                    references, 
                    result['figures'],
                    page_mapping
                )
                
                # Update processing stats
                for ref in mapped_references:
                    if ref.get('not_matched', False):
                        result['processing_info']['unmatched_references'] += 1
                    else:
                        result['processing_info']['matched_references'] += 1
                
                # Create page data with processed information
                page_data = {
                    'index': page_idx,
                    'page_size': page_size,
                    'image_path': temp_image_path,
                    'blocks': text_blocks,
                    'references': mapped_references,
                    'figure_count': len(page_figure_indices)
                }
                
                result['pages'].append(page_data)
            
            # Post-processing: Add figure relationships
            self._add_figure_relationships(result['figures'], result['pages'])
            
            return result
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    def _add_figure_relationships(self, figures: List[Dict[str, Any]], pages: List[Dict[str, Any]]):
        """Add relationship information between figures"""
        # Group figures by type and page
        figures_by_page = {}
        for fig in figures:
            page_idx = fig.get('page_idx', 0)
            if page_idx not in figures_by_page:
                figures_by_page[page_idx] = []
            figures_by_page[page_idx].append(fig)
        
        # Add sequential numbering within each type
        for page_idx, page_figures in figures_by_page.items():
            # Sort by vertical position
            page_figures.sort(key=lambda f: f['bbox']['y'])
            
            # Group by type
            by_type = {}
            for fig in page_figures:
                fig_type = fig.get('type', 'unknown')
                if fig_type not in by_type:
                    by_type[fig_type] = []
                by_type[fig_type].append(fig)
            
            # Add sequential info
            for fig_type, figs in by_type.items():
                for idx, fig in enumerate(figs):
                    fig['sequence_in_page'] = idx + 1
                    fig['total_in_page'] = len(figs)