import fitz
import os
import io
from PIL import Image
from typing import List, Dict, Any
from paddleocr import PPStructureV3
import tempfile
import shutil
from app.services.layout_detector import LayoutDetector
from app.services.figure_id_generator import FigureIDGenerator
from app.services.reference_extractor import ReferenceExtractor
from app.services.figure_mapper import FigureMapper

# Global PP-Structure instance to avoid reloading models
_pp_structure_instance = None

def get_pp_structure_instance(use_gpu: bool = True):
    """Get or create global PP-Structure instance"""
    global _pp_structure_instance
    if _pp_structure_instance is None:
        # Check if models are already cached
        cache_dir = os.path.expanduser("~/.paddlex/official_models")
        if os.path.exists(cache_dir):
            print(f"Models cache found at: {cache_dir}")
            model_files = os.listdir(cache_dir)
            print(f"Cached models: {len(model_files)} files")
        else:
            print("No model cache found - models will be downloaded")
        
        print("Initializing PP-StructureV3 with lightweight models...")
        
        # Option 1: Ultra-lightweight configuration (fastest)
        config_ultra_light = {
            # Disable heavy features for speed
            'use_doc_orientation_classify': False,
            'use_doc_unwarping': False,
            'use_textline_orientation': False,
            'use_seal_recognition': False,
            'use_chart_recognition': False,
            'use_table_recognition': False,
            'use_formula_recognition': False,
            
            # Device setting
            'device': 'gpu' if use_gpu else 'cpu',
        }
        
        # Option 2: Balanced configuration (good speed + accuracy)
        config_balanced = {
            'layout_detection_model_name': 'PP-DocLayout-M',        # 75.2% mAP@0.5, 12.7ms/page
            'text_detection_model_name': 'PP-OCRv4_server_det',     # Standard detection
            'text_recognition_model_name': 'PP-OCRv4_server_rec',   # Standard recognition
            
            'use_doc_orientation_classify': False,
            'use_doc_unwarping': False,
            'use_textline_orientation': False,
            'use_seal_recognition': False,
            'use_chart_recognition': False,
            'use_table_recognition': False,   # Keep table recognition
            'use_formula_recognition': False, # Keep formula recognition
            
            'device': 'gpu' if use_gpu else 'cpu',
        }
        
        # Use ultra-lightweight configuration for maximum speed
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
        self.figure_id_generator = FigureIDGenerator()
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
                'temp_image_paths': []
            }
            
            # Process each page
            for page_idx, image in enumerate(images):
                page_size = image.size  # Use actual image size that goes into LayoutDetector
                temp_image_path = self.save_temp_image(image, f"page_{page_idx}_")
                
                if temp_image_path:
                    result['temp_image_paths'].append(temp_image_path)
                
                # Step 2: Detect layout and text from current page
                detection_result = self.layout_detector.detect_layout_and_text(temp_image_path)
                text_blocks = detection_result.get('text_blocks', [])
                layout_blocks = detection_result.get('layout_blocks', [])
                
                # Step 3: Generate figure IDs for layout blocks and save to figures
                for layout_block in layout_blocks:
                    figure_info = self.figure_id_generator.generate_figure_info(
                        layout_block, 
                        page_idx
                    )
                    result['figures'].append(figure_info)
                
                # Step 4: Extract references from text blocks
                references = self.reference_extractor.extract_references(text_blocks)
                
                # Step 5-7: Map references to figures (all figures collected so far)
                mapped_references = self.figure_mapper.map_references_to_figures(
                    references, 
                    result['figures']
                )
                
                # Create page data with processed information
                page_data = {
                    'index': page_idx,
                    'page_size': page_size,
                    'image_path': temp_image_path,
                    'blocks': text_blocks,
                    'references': mapped_references
                }
                
                result['pages'].append(page_data)
            
            return result
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return {'error': str(e)}