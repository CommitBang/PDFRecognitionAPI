# app/services/reference_extractor.py - 페이지 정보 추가
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
        
        for block in text_blocks:
            text = block.get('text', '')
            bbox = block.get('bbox', {})
            
            if not text:
                continue
            
            # Find all references in this text block
            matches = self.compiled_pattern.finditer(text)
            
            for match in matches:
                ref_text = match.group(0)
                start_pos = match.start()
                end_pos = match.end()
                
                # Estimate bounding box for the reference
                ref_bbox = self._estimate_ref_bbox(bbox, text, start_pos, end_pos)
                
                # Add reference with page info
                reference = {
                    'text': ref_text,
                    'bbox': ref_bbox
                }
                
                # Add page_idx if provided
                if page_idx is not None:
                    reference['page_idx'] = page_idx
                
                references.append(reference)
        
        return references
    
    def _estimate_ref_bbox(self, text_bbox: Dict[str, int], full_text: str, start_pos: int, end_pos: int) -> Dict[str, int]:
        """Estimate bounding box for reference within text block"""
        if not text_bbox or not full_text:
            return {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        
        # Simple estimation based on character position
        text_length = len(full_text)
        if text_length == 0:
            return text_bbox
        
        # Estimate horizontal position (assuming horizontal text)
        char_width = text_bbox.get('width', 0) / text_length
        ref_x = text_bbox.get('x', 0) + int(start_pos * char_width)
        ref_width = int((end_pos - start_pos) * char_width)
        
        # Use same vertical position and height as text block
        return {
            'x': ref_x,
            'y': text_bbox.get('y', 0),
            'width': ref_width,
            'height': text_bbox.get('height', 0)
        }