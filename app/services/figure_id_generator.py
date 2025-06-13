import re
from typing import Dict, Any, Optional

class FigureIDGenerator:
    def __init__(self):
        """Initialize figure ID generator"""
        # Patterns to extract figure IDs from text
        self.id_patterns = [
            r'fig\.?\s*(\d+(?:\.\d+)*)',
            r'figure\.?\s*(\d+(?:\.\d+)*)',
            r'table\.?\s*(\d+(?:\.\d+)*)',
            r'tab\.?\s*(\d+(?:\.\d+)*)',
            r'equation\.?\s*(\d+(?:\.\d+)*)',
            r'eq\.?\s*(\d+(?:\.\d+)*)',
            r'chart\.?\s*(\d+(?:\.\d+)*)',
            r'graph\.?\s*(\d+(?:\.\d+)*)',
            r'image\.?\s*(\d+(?:\.\d+)*)',
        ]
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.id_patterns]
    
    def generate_figure_info(self, layout_block: Dict[str, Any], page_idx: int) -> Dict[str, Any]:
        """Generate figure information including ID and position"""
        # 타입 안전성을 위해 모든 값을 적절히 변환
        figure_type = str(layout_block.get('type', 'figure'))
        text = str(layout_block.get('text', '')).strip()
        bbox = layout_block.get('bbox', {})
        
        # bbox 검증 및 기본값 설정
        if not isinstance(bbox, dict):
            bbox = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        
        # bbox 값들의 타입 안전성 보장
        safe_bbox = {}
        for key in ['x', 'y', 'width', 'height']:
            try:
                safe_bbox[key] = int(bbox.get(key, 0))
            except (ValueError, TypeError):
                safe_bbox[key] = 0
        
        # Try to extract figure ID from text
        figure_id = self._extract_figure_id_from_text(text)
        
        # If no ID found in text, generate one based on page and position
        if not figure_id:
            figure_id = self._generate_fallback_id(figure_type, page_idx, safe_bbox)
        
        # confidence 값의 타입 안전성 보장
        confidence = layout_block.get('confidence', 0.0)
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            confidence = 0.0
        
        return {
            'figure_id': figure_id,
            'type': figure_type,
            'bbox': safe_bbox,
            'page_idx': int(page_idx),
            'text': text,
            'confidence': confidence
        }
    
    def _extract_figure_id_from_text(self, text: str) -> Optional[str]:
        """Extract figure ID from text (e.g., from figure caption)"""
        if not text or not isinstance(text, str):
            return None
        
        # Try each pattern
        for pattern in self.compiled_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1)
        
        return None
    
    def _generate_fallback_id(self, figure_type: str, page_idx: int, bbox: Dict[str, int]) -> str:
        """Generate fallback ID based on type, page, and position"""
        # Use page index and vertical position to create unique ID
        try:
            y_position = int(bbox.get('y', 0))
            page_num = int(page_idx)
        except (ValueError, TypeError):
            y_position = 0
            page_num = 0
        
        # Create ID format: page_yposition (e.g., "0_150" for page 0, y=150)
        # This ensures figures on the same page have different IDs
        return f"{page_num}_{y_position}"