import fitz
import os
from PIL import Image
from typing import List, Dict, Any
from pdf2image import convert_from_path
import tempfile
import shutil

class PDFProcessor:
    def __init__(self, dpi: int = 300):
        self.dpi = dpi
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF file"""
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            doc.close()
            
            return {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'creator': metadata.get('creator', ''),
                'producer': metadata.get('producer', ''),
                'creation_date': metadata.get('creationDate', ''),
                'modification_date': metadata.get('modDate', ''),
                'pages': doc.page_count if 'doc' in locals() else 0
            }
        except Exception as e:
            print(f"Error extracting metadata: {str(e)}")
            return {}
    
    def pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """Convert PDF pages to PIL Images"""
        try:
            images = convert_from_path(
                pdf_path,
                dpi=self.dpi,
                fmt='RGB'
            )
            return images
        except Exception as e:
            print(f"Error converting PDF to images: {str(e)}")
            return []
    
    def get_page_size(self, pdf_path: str, page_num: int) -> tuple:
        """Get page size for specific page"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            rect = page.rect
            doc.close()
            return (int(rect.width), int(rect.height))
        except Exception as e:
            print(f"Error getting page size: {str(e)}")
            return (0, 0)
    
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
            # Extract metadata
            metadata = self.extract_metadata(pdf_path)
            
            # Convert to images
            images = self.pdf_to_images(pdf_path)
            
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
                page_size = self.get_page_size(pdf_path, page_idx)
                temp_image_path = self.save_temp_image(image, f"page_{page_idx}_")
                
                if temp_image_path:
                    result['temp_image_paths'].append(temp_image_path)
                
                page_data = {
                    'index': page_idx,
                    'page_size': page_size,
                    'image_path': temp_image_path,
                    'blocks': [],
                    'references': []
                }
                
                result['pages'].append(page_data)
            
            return result
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return {'error': str(e)}