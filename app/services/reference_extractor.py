# app/services/reference_extractor.py - 타입 안전성 개선
import re
from typing import List, Dict, Any, Tuple

class ReferenceExtractor:
    def __init__(self):
        """Initialize reference extractor with predefined patterns"""
        # Common figure reference patterns
        self.reference_patterns = [
            # Figure patterns
            r'\bFig\.?\s*\d+(?:\.\d+)*\b',  # Fig. 1, Fig 1.2
            r'\bFigure\.?\s*\d+(?:\.\d+)*\b',  # Figure 1, Figure. 1.2
            r'\bFIG\.?\s*\d+(?:\.\d+)*\b',  # FIG. 1, FIG 1.2
            
            # Table patterns
            r'\bTable\.?\s*\d+(?:\.\d+)*\b',  # Table 1, Table. 1.2
            r'\bTab\.?\s*\d+(?:\.\d+)*\b',  # Tab. 1, Tab 1.2
            
            # Equation patterns
            r'\bEq\.?\s*\(\d+(?:\.\d+)*\)',  # Eq. (1), Eq (1.2)
            r'\bEquation\.?\s*\(\d+(?:\.\d+)*\)',  # Equation (1)
            r'\(\d+(?:\.\d+)*\)(?=\s|$|[,.])',  # (1) or (1.2) in parentheses
            
            # Example patterns
            r'\bExample\.?\s*\d+(?:\.\d+)*\b',  # Example 1, Example. 1.2
            
            # Combined patterns like "Figs. 1 and 2"
            r'\bFigs?\.?\s*\d+(?:\.\d+)*(?:\s*(?:and|&|-|,)\s*\d+(?:\.\d+)*)*\b',
            r'\bTables?\.?\s*\d+(?:\.\d+)*(?:\s*(?:and|&|-|,)\s*\d+(?:\.\d+)*)*\b',
        ]
        
        # Compile all patterns into one
        self.compiled_pattern = re.compile('|'.join(self.reference_patterns), re.IGNORECASE)
    
    def extract_references(self, text_blocks: List[Dict[str, Any]], page_idx: int = None) -> List[Dict[str, Any]]:
        """Extract references from text blocks, returning text, bbox, and page_idx"""
        references = []
        
        if not text_blocks or not isinstance(text_blocks, list):
            return references
        
        for block in text_blocks:
            if not isinstance(block, dict):
                continue
                
            text = block.get('text', '')
            bbox = block.get('bbox', {})
            
            # 타입 안전성 보장
            text_str = str(text) if text is not None else ''
            
            if not text_str:
                continue
            
            # bbox 검증 및 기본값 설정
            if not isinstance(bbox, dict):
                bbox = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
            
            # Find all references in this text block
            try:
                matches = self.compiled_pattern.finditer(text_str)
                
                for match in matches:
                    ref_text = match.group(0)
                    start_pos = match.start()
                    end_pos = match.end()
                    
                    # Estimate bounding box for the reference
                    ref_bbox = self._estimate_ref_bbox(bbox, text_str, start_pos, end_pos)
                    
                    # Add reference with page info
                    reference = {
                        'text': ref_text,
                        'bbox': ref_bbox
                    }
                    
                    # Add page_idx if provided
                    if page_idx is not None:
                        try:
                            reference['page_idx'] = int(page_idx)
                        except (ValueError, TypeError):
                            reference['page_idx'] = 0
                    
                    references.append(reference)
            except Exception as e:
                print(f"Error processing text block: {e}")
                continue
        
        return references
    
    def _estimate_ref_bbox(self, text_bbox: Dict[str, int], full_text: str, start_pos: int, end_pos: int) -> Dict[str, int]:
        """Estimate bounding box for reference within text block"""
        # 기본값 설정
        default_bbox = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        
        if not text_bbox or not isinstance(text_bbox, dict) or not full_text:
            return default_bbox
        
        # 타입 안전성을 위한 값 추출
        try:
            text_x = int(text_bbox.get('x', 0))
            text_y = int(text_bbox.get('y', 0))
            text_width = int(text_bbox.get('width', 0))
            text_height = int(text_bbox.get('height', 0))
        except (ValueError, TypeError):
            return default_bbox
        
        # Simple estimation based on character position
        text_length = len(full_text)
        if text_length == 0:
            return {
                'x': text_x,
                'y': text_y,
                'width': text_width,
                'height': text_height
            }
        
        # Estimate horizontal position (assuming horizontal text)
        try:
            char_width = text_width / text_length
            ref_x = text_x + int(start_pos * char_width)
            ref_width = int((end_pos - start_pos) * char_width)
            
            # 음수값 방지
            ref_x = max(0, ref_x)
            ref_width = max(1, ref_width)
            
            return {
                'x': ref_x,
                'y': text_y,
                'width': ref_width,
                'height': text_height
            }
        except (ValueError, TypeError, ZeroDivisionError):
            return default_bbox