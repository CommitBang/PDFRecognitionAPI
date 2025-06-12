import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Tuple
import io
import base64

class LayoutVisualizer:
    def __init__(self):
        # Color scheme for different layout types
        self.colors = {
            'Caption': (255, 0, 0),      # Red
            'Footnote': (0, 255, 0),     # Green
            'Formula': (0, 0, 255),      # Blue
            'List-item': (255, 255, 0),  # Yellow
            'Page-footer': (255, 0, 255), # Magenta
            'Page-header': (0, 255, 255), # Cyan
            'Picture': (128, 0, 128),    # Purple
            'Section-header': (255, 128, 0), # Orange
            'Table': (128, 255, 128),    # Light Green
            'Text': (128, 128, 128),     # Gray
            'Title': (0, 128, 255)       # Light Blue
        }
        
        # Default color for unknown types
        self.default_color = (200, 200, 200)
    
    def draw_bounding_boxes(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        Draw bounding boxes with labels on image
        """
        try:
            # Convert numpy array to PIL Image for better text rendering
            if image.dtype != np.uint8:
                image = (image * 255).astype(np.uint8)
            
            pil_image = Image.fromarray(image)
            draw = ImageDraw.Draw(pil_image)
            
            # Try to load a font, fallback to default if not available
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            for detection in detections:
                bbox = detection['bbox']
                class_name = detection['class_name']
                confidence = detection.get('confidence', 0.0)
                
                # Get coordinates
                x1, y1 = bbox['x'], bbox['y']
                x2, y2 = x1 + bbox['width'], y1 + bbox['height']
                
                # Get color for this class
                color = self.colors.get(class_name, self.default_color)
                
                # Draw bounding box
                draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
                
                # Prepare label text
                label = f"{class_name} ({confidence:.2f})"
                
                # Get text size for background
                bbox_text = draw.textbbox((0, 0), label, font=font)
                text_width = bbox_text[2] - bbox_text[0]
                text_height = bbox_text[3] - bbox_text[1]
                
                # Draw label background
                draw.rectangle([x1, y1-text_height-5, x1+text_width+10, y1], fill=color)
                
                # Draw label text
                draw.text((x1+5, y1-text_height-2), label, fill=(255, 255, 255), font=font)
            
            # Convert back to numpy array
            return np.array(pil_image)
            
        except Exception as e:
            raise Exception(f"Error drawing bounding boxes: {str(e)}")
    
    def create_visualization_summary(self, detections: List[Dict]) -> Dict:
        """Create a summary of detected elements"""
        summary = {}
        
        for detection in detections:
            class_name = detection['class_name']
            if class_name not in summary:
                summary[class_name] = {
                    'count': 0,
                    'avg_confidence': 0.0,
                    'elements': []
                }
            
            summary[class_name]['count'] += 1
            summary[class_name]['elements'].append({
                'bbox': detection['bbox'],
                'confidence': detection.get('confidence', 0.0)
            })
        
        # Calculate average confidence for each class
        for class_name in summary:
            confidences = [elem['confidence'] for elem in summary[class_name]['elements']]
            summary[class_name]['avg_confidence'] = sum(confidences) / len(confidences)
        
        return summary
    
    def image_to_base64(self, image: np.ndarray) -> str:
        """Convert numpy image to base64 string"""
        try:
            # Convert to RGB if needed
            if len(image.shape) == 3 and image.shape[2] == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            
            # Convert to PIL Image
            pil_image = Image.fromarray(image_rgb)
            
            # Save to bytes
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()
            
            # Encode to base64
            base64_string = base64.b64encode(image_bytes).decode('utf-8')
            return f"data:image/png;base64,{base64_string}"
            
        except Exception as e:
            raise Exception(f"Error converting image to base64: {str(e)}")
    
    def save_visualization(self, image: np.ndarray, output_path: str) -> str:
        """Save visualization image to file"""
        try:
            cv2.imwrite(output_path, image)
            return output_path
        except Exception as e:
            raise Exception(f"Error saving visualization: {str(e)}")