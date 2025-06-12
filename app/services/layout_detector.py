from typing import List, Dict, Any

class LayoutDetector:
    def __init__(self, pp_structure):
        """Initialize with existing PP-Structure instance"""
        self.pp_structure = pp_structure
    
    def detect_layout_and_text(self, image_path: str) -> Dict[str, Any]:
        """Detect layout and extract text using PP-Structure"""
        try:
            # Run PP-Structure analysis
            output = self.pp_structure(image_path)
            
            print(f"PP-Structure output type: {type(output)}")
            print(f"PP-Structure output keys: {output.keys() if isinstance(output, dict) else 'Not a dict'}")
            
            if not output or 'res' not in output:
                return {'text_blocks': [], 'layout_blocks': []}
            
            # Extract the results from the 'res' key
            res = output['res']
            boxes = res.get('boxes', [])
            
            print(f"Found {len(boxes)} layout boxes")
            
            text_blocks = []
            layout_blocks = []
            
            # Process each detected box
            for box in boxes:
                label = box.get('label', '')
                coordinate = box.get('coordinate', [])
                score = box.get('score', 0.0)
                
                # Format bbox
                if len(coordinate) >= 4:
                    bbox_formatted = self._format_bbox_from_coords(coordinate)
                else:
                    continue
                
                print(f"Processing box: label={label}, bbox={bbox_formatted}")
                
                if label == 'text':
                    # This is a text region, but we need to run OCR to get actual text
                    # For now, we'll create a placeholder text block
                    text_block = {
                        'text': f"Text region {len(text_blocks) + 1}",  # Placeholder text
                        'bbox': bbox_formatted,
                        'confidence': score
                    }
                    text_blocks.append(text_block)
                else:
                    # Non-text layout element
                    layout_block = {
                        'type': label,
                        'bbox': bbox_formatted,
                        'confidence': score,
                        'text': ''  # No text content for layout elements
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