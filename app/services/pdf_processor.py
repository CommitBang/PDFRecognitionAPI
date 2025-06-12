import fitz  # PyMuPDF
from PIL import Image
import numpy as np
from typing import List, Tuple
from config import Config
import os
import tempfile
import io

class PDFProcessor:
    def __init__(self):
        self.dpi = Config.DPI
    
    def pdf_to_images(self, pdf_path: str) -> List[Tuple[np.ndarray, dict]]:
        """
        Convert PDF pages to images
        Returns list of (image_array, page_info) tuples
        """
        try:
            doc = fitz.open(pdf_path)
            images = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Get page dimensions
                page_rect = page.rect
                page_info = {
                    'page_index': page_num,
                    'width': page_rect.width,
                    'height': page_rect.height
                }
                
                # Convert to image
                mat = fitz.Matrix(self.dpi/72, self.dpi/72)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Convert to PIL Image and then to numpy array
                pil_image = Image.open(io.BytesIO(img_data))
                img_array = np.array(pil_image)
                
                images.append((img_array, page_info))
                
            doc.close()
            return images
            
        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")
    
    def get_pdf_metadata(self, pdf_path: str) -> dict:
        """Extract PDF metadata"""
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            page_count = len(doc)
            doc.close()
            
            return {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'creator': metadata.get('creator', ''),
                'producer': metadata.get('producer', ''),
                'page_count': page_count
            }
        except Exception as e:
            raise Exception(f"Error extracting PDF metadata: {str(e)}")
    
    def save_page_image(self, image_array: np.ndarray, page_index: int, output_dir: str) -> str:
        """Save page image to file"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            filename = f"page_{page_index}.png"
            filepath = os.path.join(output_dir, filename)
            
            image = Image.fromarray(image_array)
            image.save(filepath, 'PNG')
            
            return filepath
        except Exception as e:
            raise Exception(f"Error saving page image: {str(e)}")