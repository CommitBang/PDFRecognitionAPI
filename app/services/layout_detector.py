from typing import List, Dict, Any
import numpy as np

class LayoutDetector:
    def __init__(self, pp_structure):
        """Initialize with existing PP-Structure instance"""
        self.pp_structure = pp_structure
    
    def detect_layout_and_text(self, image_path: str) -> Dict[str, Any]:
        """Detect layout and extract text using PP-Structure"""
        try:
            # Run PP-Structure analysis - predict() returns a list of results
            output_list = self.pp_structure.predict(image_path)
            
            print(f"PP-Structure output type: {type(output_list)}")
            print(f"PP-Structure output length: {len(output_list) if isinstance(output_list, list) else 'Not a list'}")
            
            if not output_list or not isinstance(output_list, list):
                return {'text_blocks': [], 'layout_blocks': []}
            
            text_blocks = []
            layout_blocks = []
            
            # Process each result in the list - each result is a dict
            for result in output_list:
                print(f"Processing result: {type(result)}")
                print(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
                
                # Direct access to result dict (based on official docs)
                if not isinstance(result, dict):
                    continue
                
                # Extract layout detection results
                layout_det_res = result.get('layout_det_res', {})
                layout_boxes = layout_det_res.get('boxes', [])
                
                # Extract OCR results
                overall_ocr_res = result.get('overall_ocr_res', {})
                rec_texts = overall_ocr_res.get('rec_texts', [])
                rec_scores = overall_ocr_res.get('rec_scores', [])
                rec_boxes = overall_ocr_res.get('rec_boxes', [])
                
                print(f"Found {len(layout_boxes)} layout boxes")
                print(f"Found {len(rec_texts)} OCR texts")
                
                # Process OCR results to create text blocks
                for i, text in enumerate(rec_texts):
                    if i < len(rec_scores) and i < len(rec_boxes):
                        # Convert numpy array to list if needed
                        box = rec_boxes[i]
                        if isinstance(box, np.ndarray):
                            box = box.tolist()
                        
                        # rec_boxes format: [x1, y1, x2, y2]
                        if len(box) >= 4:
                            bbox_formatted = {
                                'x': int(box[0]),
                                'y': int(box[1]),
                                'width': int(box[2] - box[0]),
                                'height': int(box[3] - box[1])
                            }
                            
                            text_block = {
                                'text': text,
                                'bbox': bbox_formatted,
                                'confidence': float(rec_scores[i]) if i < len(rec_scores) else 1.0
                            }
                            text_blocks.append(text_block)
                
                # Process layout boxes to create layout blocks (non-text elements)
                for box in layout_boxes:
                    label = box.get('label', '')
                    coordinate = box.get('coordinate', [])
                    score = box.get('score', 0.0)
                    
                    # Skip text labels as we already processed OCR results
                    if label == 'text':
                        continue
                    
                    # Format bbox
                    if len(coordinate) >= 4:
                        bbox_formatted = self._format_bbox_from_coords(coordinate)
                        
                        layout_block = {
                            'type': label,
                            'bbox': bbox_formatted,
                            'confidence': score,
                            'text': self._extract_text_for_layout(bbox_formatted, text_blocks)
                        }
                        layout_blocks.append(layout_block)
            
            print(f"Created {len(text_blocks)} text blocks and {len(layout_blocks)} layout blocks")
            
            return {
                'text_blocks': text_blocks,
                'layout_blocks': layout_blocks
            }
            
        except Exception as e:
            print(f"Error in layout detection: {str(e)}")
            import traceback
            traceback.print_exc()
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
        except Exception as e:
            print(f"Error formatting bbox from coordinates: {str(e)}")
            return {'x': 0, 'y': 0, 'width': 0, 'height': 0}
    
    def _extract_text_for_layout(self, layout_bbox: Dict[str, int], text_blocks: List[Dict[str, Any]]) -> str:
        """Extract text that falls within a layout region"""
        texts = []
        for text_block in text_blocks:
            if self._is_text_in_region(text_block['bbox'], layout_bbox):
                texts.append(text_block['text'])
        return ' '.join(texts)
    
    def _is_text_in_region(self, text_bbox: Dict[str, int], region_bbox: Dict[str, int]) -> bool:
        """Check if text block overlaps with a region"""
        text_x1 = text_bbox['x']
        text_y1 = text_bbox['y']
        text_x2 = text_x1 + text_bbox['width']
        text_y2 = text_y1 + text_bbox['height']
        
        region_x1 = region_bbox['x']
        region_y1 = region_bbox['y']
        region_x2 = region_x1 + region_bbox['width']
        region_y2 = region_y1 + region_bbox['height']
        
        # Check if text box overlaps with region
        return (text_x1 < region_x2 and text_x2 > region_x1 and 
                text_y1 < region_y2 and text_y2 > region_y1)