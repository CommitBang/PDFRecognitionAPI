from paddleocr import PaddleOCR, PPStructure
from typing import List, Dict, Any

class LayoutDetector:
    def __init__(self, use_gpu: bool = True, lang: str = 'en'):
        """Initialize PPStructure for layout detection and text recognition"""
        self.engine = PPStructure(
            show_log=False,
            use_gpu=use_gpu,
            lang=lang,
            recovery=False,  # Disable recovery to get raw layout results
            structure_version='PP-StructureV2'
        )
    
    def detect_layout_and_text(self, image_path: str) -> Dict[str, Any]:
        """Detect layout and extract text using PPStructure"""
        try:
            # Run PPStructure analysis
            result = self.engine(image_path)
            
            if not result:
                return {'text_blocks': [], 'layout_blocks': []}
            
            # Process results
            layout_blocks = []
            text_blocks = []
            
            for item in result:
                item_type = item.get('type', '')
                bbox = item.get('bbox', [0, 0, 0, 0])
                
                # Format bbox from [x1, y1, x2, y2] to {x, y, width, height}
                bbox_formatted = self._format_bbox_from_coords(bbox)
                
                if item_type != 'text':
                    # Non-text layout element (figure, table, etc.)
                    layout_block = {
                        'type': item_type,
                        'bbox': bbox_formatted,
                        'confidence': item.get('score', 1.0),
                        'text': ''  # Will be filled if contains text
                    }
                    
                    # Check if this layout element has associated text
                    if 'res' in item and item['res']:
                        text_content = self._extract_text_from_res(item['res'])
                        layout_block['text'] = text_content
                    
                    layout_blocks.append(layout_block)
                else:
                    # Text element
                    if 'res' in item and item['res']:
                        text_content = self._extract_text_from_res(item['res'])
                        if text_content:
                            # Check if this text is inside any layout block
                            assigned = False
                            for layout in layout_blocks:
                                if self._is_bbox_inside(bbox_formatted, layout['bbox']):
                                    if layout['text']:
                                        layout['text'] += ' ' + text_content
                                    else:
                                        layout['text'] = text_content
                                    assigned = True
                                    break
                            
                            if not assigned:
                                text_block = {
                                    'text': text_content,
                                    'bbox': bbox_formatted,
                                    'confidence': item.get('score', 1.0)
                                }
                                text_blocks.append(text_block)
            
            return {
                'text_blocks': text_blocks,
                'layout_blocks': layout_blocks
            }
            
        except Exception as e:
            print(f"Error in layout detection: {str(e)}")
            return {'text_blocks': [], 'layout_blocks': [], 'error': str(e)}
    
    def _format_bbox_from_coords(self, bbox: List[float]) -> Dict[str, int]:
        """Convert bbox from [x1, y1, x2, y2] to x, y, width, height format"""
        try:
            if len(bbox) >= 4:
                x1, y1, x2, y2 = bbox[:4]
                return {
                    'x': int(x1),
                    'y': int(y1),
                    'width': int(x2 - x1),
                    'height': int(y2 - y1)
                }
            else:
                return {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        except Exception as e:
            print(f"Error formatting bbox: {str(e)}")
            return {'x': 0, 'y': 0, 'width': 0, 'height': 0}
    
    def _extract_text_from_res(self, res) -> str:
        """Extract text content from res field"""
        try:
            if isinstance(res, list):
                text_parts = []
                for item in res:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    elif isinstance(item, list) and len(item) > 1:
                        # OCR format [[bbox], [text, score]]
                        if isinstance(item[1], list) and len(item[1]) > 0:
                            text_parts.append(item[1][0])
                return ' '.join(text_parts)
            elif isinstance(res, dict) and 'text' in res:
                return res['text']
            elif isinstance(res, str):
                return res
            return ''
        except Exception as e:
            print(f"Error extracting text: {str(e)}")
            return ''
    
    def _is_bbox_inside(self, inner_bbox: Dict[str, int], outer_bbox: Dict[str, int]) -> bool:
        """Check if inner bbox is inside outer bbox"""
        inner_x1 = inner_bbox['x']
        inner_y1 = inner_bbox['y']
        inner_x2 = inner_x1 + inner_bbox['width']
        inner_y2 = inner_y1 + inner_bbox['height']
        
        outer_x1 = outer_bbox['x']
        outer_y1 = outer_bbox['y']
        outer_x2 = outer_x1 + outer_bbox['width']
        outer_y2 = outer_y1 + outer_bbox['height']
        
        # Check if inner is completely inside outer
        return (inner_x1 >= outer_x1 and inner_y1 >= outer_y1 and 
                inner_x2 <= outer_x2 and inner_y2 <= outer_y2)