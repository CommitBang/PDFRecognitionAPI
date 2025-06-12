from paddleocr import PaddleOCR
from typing import List, Dict, Any

class LayoutDetector:
    def __init__(self, use_gpu: bool = True, lang: str = 'en'):
        self.ocr = PaddleOCR(
            use_angle_cls=True, 
            lang=lang,
            use_gpu=use_gpu,
            show_log=False,
            use_doc_orientation_classify=True
        )
    
    def detect_layout_and_text(self, image_path: str) -> Dict[str, Any]:
        """Detect layout and extract text from image using PaddleOCR"""
        try:
            # Run OCR with layout detection
            result = self.ocr.ocr(image_path, cls=True)
            
            if not result or not result[0]:
                return {'text_blocks': [], 'layout_blocks': []}
            
            text_blocks = []
            layout_blocks = []
            
            # Process OCR results - result[0] contains the detection results
            for line in result[0]:
                if line:
                    # line[0] contains bbox coordinates as [[x1,y1], [x2,y2], ...]
                    # line[1] contains (text, confidence)
                    bbox_points = line[0]
                    text_info = line[1]
                    
                    text = text_info[0] if text_info else ""
                    confidence = text_info[1] if text_info and len(text_info) > 1 else 0.0
                    
                    # Convert bbox from points to x,y,width,height format
                    bbox_formatted = self._format_bbox(bbox_points)
                    
                    # Create text block
                    text_block = {
                        'text': text,
                        'bbox': bbox_formatted,
                        'confidence': confidence
                    }
                    text_blocks.append(text_block)
                    
                    # Create layout block with type classification
                    layout_type = self._classify_layout_type(text, bbox_formatted)
                    layout_block = {
                        'type': layout_type,
                        'bbox': bbox_formatted,
                        'text': text,
                        'confidence': confidence
                    }
                    layout_blocks.append(layout_block)
            
            return {
                'text_blocks': text_blocks,
                'layout_blocks': layout_blocks
            }
            
        except Exception as e:
            print(f"Error in layout detection: {str(e)}")
            return {'text_blocks': [], 'layout_blocks': [], 'error': str(e)}
    
    def _format_bbox(self, bbox_points: List[List[float]]) -> Dict[str, int]:
        """Convert bbox from list of points to x, y, width, height format"""
        try:
            # bbox_points is [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            x_coords = [point[0] for point in bbox_points]
            y_coords = [point[1] for point in bbox_points]
            
            x = int(min(x_coords))
            y = int(min(y_coords))
            width = int(max(x_coords) - min(x_coords))
            height = int(max(y_coords) - min(y_coords))
            
            return {'x': x, 'y': y, 'width': width, 'height': height}
        except Exception as e:
            print(f"Error formatting bbox: {str(e)}")
            return {'x': 0, 'y': 0, 'width': 0, 'height': 0}
    
    def _classify_layout_type(self, text: str, bbox: Dict[str, int]) -> str:
        """Basic layout type classification based on text content"""
        if not text:
            return 'text'
        
        text_lower = text.lower().strip()
        
        # Check for common layout types based on text patterns
        if any(keyword in text_lower for keyword in ['figure', 'fig.', 'image', 'chart', 'graph', 'table', 'tab.']):
            return 'figure'
        elif len(text) < 100 and bbox['height'] > 20:
            # Likely a title or heading
            return 'paragraph_title'
        else:
            return 'text'