from paddleocr import PPStructureV3
from typing import List, Dict, Any

class LayoutDetector:
    def __init__(self, use_gpu: bool = True, lang: str = 'en'):
        """Initialize PP-StructureV3 for layout detection and text recognition"""
        self.pipeline = PPStructureV3(
            use_gpu=use_gpu,
            lang=lang,
            show_log=False
        )
    
    def detect_layout_and_text(self, image_path: str) -> Dict[str, Any]:
        """Detect layout and extract text using PP-StructureV3"""
        """Detect layout and extract text using PP-StructureV3"""
        try:
            # Run PP-StructureV3 pipeline
            output = self.pipeline.predict(image_path)
            # Run PP-StructureV3 pipeline
            output = self.pipeline.predict(image_path)
            
            if not output or not isinstance(output, list) or len(output) == 0:
                return {'text_blocks': [], 'layout_blocks': []}
            
            result = output[0]
            
            # Extract layout detection results
            layout_det_res = result.get('layout_det_res', {})
            layout_boxes = layout_det_res.get('boxes', [])
            
            # Extract text recognition results  
            ocr_res = result.get('overall_ocr_res', {})
            rec_texts = ocr_res.get('rec_texts', [])
            rec_scores = ocr_res.get('rec_scores', [])
            rec_boxes = ocr_res.get('rec_boxes', [])
            
            
            # Process layout regions - filter out text layouts
            layout_blocks = []
            
            for box in layout_boxes:
                label = box.get('label', '')
                if label != 'text':  # Keep only non-text layout regions
                    coordinate = box.get('coordinate', [0, 0, 0, 0])
                    bbox_formatted = self._format_bbox_from_coords(coordinate)
                    
                    layout_block = {
                        'type': label,
                        'type': label,
                        'bbox': bbox_formatted,
                        'confidence': box.get('score', 0.0),
                        'text': ''  # Will be filled with contained text
                    }
                    layout_blocks.append(layout_block)
            
            # Process text blocks and assign to layout regions or standalone text
            text_blocks = []
            
            for i, text in enumerate(rec_texts):
                if i < len(rec_scores) and i < len(rec_boxes):
                    bbox_formatted = self._format_bbox_from_coords(rec_boxes[i])
                    
                    # Check if this text block belongs to any figure-type layout region
                    assigned_to_layout = False
                    for layout_block in layout_blocks:
                        if self._is_text_in_figure_region(bbox_formatted, [layout_block['bbox']]):
                            # Add text to the layout block's text property
                            if layout_block['text']:
                                layout_block['text'] += ' ' + text
                            else:
                                layout_block['text'] = text
                            assigned_to_layout = True
                            break
                    
                    # If not assigned to any layout, add as standalone text block
                    if not assigned_to_layout:
                        text_block = {
                            'text': text,
                            'bbox': bbox_formatted,
                            'confidence': rec_scores[i]
                        }
                        text_blocks.append(text_block)
            
            return {
                'text_blocks': text_blocks,
                'layout_blocks': layout_blocks
            }
            
        except Exception as e:
            print(f"Error in layout detection: {str(e)}")
            return {'text_blocks': [], 'layout_blocks': [], 'error': str(e)}
    
    def _format_bbox_from_coords(self, coordinate: List[float]) -> Dict[str, int]:
        """Convert bbox from [x1, y1, x2, y2] to x, y, width, height format"""
        try:
            if len(coordinate) >= 4:
                x1, y1, x2, y2 = coordinate[:4]
                return {
                    'x': int(x1),
                    'y': int(y1),
                    'width': int(x2 - x1),
                    'height': int(y2 - y1)
                }
            else:
                return {'x': 0, 'y': 0, 'width': 0, 'height': 0}
            if len(coordinate) >= 4:
                x1, y1, x2, y2 = coordinate[:4]
                return {
                    'x': int(x1),
                    'y': int(y1),
                    'width': int(x2 - x1),
                    'height': int(y2 - y1)
                }
            else:
                return {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        except Exception as e:
            print(f"Error formatting bbox from coordinates: {str(e)}")
            print(f"Error formatting bbox from coordinates: {str(e)}")
            return {'x': 0, 'y': 0, 'width': 0, 'height': 0}
    
    def _is_text_in_figure_region(self, text_bbox: Dict[str, int], figure_regions: List[Dict[str, int]]) -> bool:
        """Check if text block overlaps with any figure-type layout region"""
        text_x1 = text_bbox['x']
        text_y1 = text_bbox['y']
        text_x2 = text_x1 + text_bbox['width']
        text_y2 = text_y1 + text_bbox['height']
        
        for figure_bbox in figure_regions:
            fig_x1 = figure_bbox['x']
            fig_y1 = figure_bbox['y']
            fig_x2 = fig_x1 + figure_bbox['width']
            fig_y2 = fig_y1 + figure_bbox['height']
            
            # Check if text box overlaps with figure region
            if (text_x1 < fig_x2 and text_x2 > fig_x1 and 
                text_y1 < fig_y2 and text_y2 > fig_y1):
                return True
        
        return False
    
    def _is_text_in_figure_region(self, text_bbox: Dict[str, int], figure_regions: List[Dict[str, int]]) -> bool:
        """Check if text block overlaps with any figure-type layout region"""
        text_x1 = text_bbox['x']
        text_y1 = text_bbox['y']
        text_x2 = text_x1 + text_bbox['width']
        text_y2 = text_y1 + text_bbox['height']
        
        for figure_bbox in figure_regions:
            fig_x1 = figure_bbox['x']
            fig_y1 = figure_bbox['y']
            fig_x2 = fig_x1 + figure_bbox['width']
            fig_y2 = fig_y1 + figure_bbox['height']
            
            # Check if text box overlaps with figure region
            if (text_x1 < fig_x2 and text_x2 > fig_x1 and 
                text_y1 < fig_y2 and text_y2 > fig_y1):
                return True
        
        return False