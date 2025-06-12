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
            text_blocks = []
            layout_blocks = []
            if not output_list or not isinstance(output_list, list):
                return {'text_blocks': [], 'layout_blocks': []}
        
            # Access the result dict - structure has 'res' key containing all data
            result = output_list[0].json  # First result contains the data
            if not isinstance(result, dict) or 'res' not in result:
                return {'text_blocks': [], 'layout_blocks': []}
            
            res_data = result['res']
            print(f"Result keys: {res_data.keys()}")
            
            # Extract structured parsing results (higher level blocks)
            parsing_res_list = res_data.get('parsing_res_list', [])
            print(f"Found {len(parsing_res_list)} parsed blocks")
            
            # Extract OCR results
            overall_ocr_res = res_data.get('overall_ocr_res', {})
            rec_texts = overall_ocr_res.get('rec_texts', [])
            rec_scores = overall_ocr_res.get('rec_scores', [])
            rec_boxes = overall_ocr_res.get('rec_boxes', [])
            
            print(f"Found {len(rec_texts)} OCR texts")
            
            # Process structured parsing results (use these for layout blocks)
            for parsed_block in parsing_res_list:
                block_label = parsed_block.get('block_label', '')
                block_content = parsed_block.get('block_content', '')
                block_bbox = parsed_block.get('block_bbox', [])
                
                # Format bbox from [x1, y1, x2, y2] to our format
                if len(block_bbox) >= 4:
                    bbox_formatted = {
                        'x': int(block_bbox[0]),
                        'y': int(block_bbox[1]),
                        'width': int(block_bbox[2] - block_bbox[0]),
                        'height': int(block_bbox[3] - block_bbox[1])
                    }
                    
                    # Determine if this is a text block or layout block
                    if block_label in ['text', 'paragraph_title', 'header']:
                        # Add as text block
                        text_block = {
                            'text': block_content,
                            'bbox': bbox_formatted,
                            'confidence': 1.0
                        }
                        text_blocks.append(text_block)
                    else:
                        # Add as layout block (figure, table, algorithm, etc.)
                        layout_block = {
                            'type': block_label,
                            'bbox': bbox_formatted,
                            'confidence': 1.0,
                            'text': block_content
                        }
                        layout_blocks.append(layout_block)
            
            # Also process individual OCR results for any missed text
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
                        
                        # Check if this text is already covered by parsing results
                        already_covered = False
                        for existing_block in text_blocks:
                            if self._is_text_in_region(bbox_formatted, existing_block['bbox']):
                                already_covered = True
                                break
                        
                        if not already_covered:
                            text_block = {
                                'text': text,
                                'bbox': bbox_formatted,
                                'confidence': float(rec_scores[i]) if i < len(rec_scores) else 1.0
                            }
                            text_blocks.append(text_block)
            
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