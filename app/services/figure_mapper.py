import re
from typing import List, Dict, Any, Optional

class FigureMapper:
    """Enhanced mapper with fuzzy matching and spatial awareness"""
    def __init__(self):
        self.id_variations = {
            'figure': ['fig', 'figure', 'image'],
            'table': ['tab', 'table'],
            'equation': ['eq', 'equation', 'eqn'],
            'algorithm': ['alg', 'algorithm']
        }
    
    def map_references_to_figures(self, references: List[Dict[str, Any]], figures: List[Dict[str, Any]], 
                                  page_mapping: Dict[int, List[int]] = None) -> List[Dict[str, Any]]:
        """Enhanced reference mapping with multiple strategies"""
        mapped_refs = []
        
        for ref in references:
            ref_text = ref.get('text', '')
            ref_bbox = ref.get('bbox', {})
            
            # Try multiple matching strategies
            matched_figure = None
            
            # 1. Exact ID match
            ref_id = self._extract_reference_id(ref_text)
            if ref_id:
                matched_figure = self._find_figure_by_id(ref_id, figures)
            
            # 2. Fuzzy text matching if no exact match
            if not matched_figure:
                matched_figure = self._fuzzy_match_figure(ref_text, figures)
            
            # 3. Spatial proximity matching (for same-page references)
            if not matched_figure and page_mapping:
                matched_figure = self._spatial_match_figure(ref_bbox, figures, page_mapping)
            
            # Create mapped reference
            mapped_ref = {
                'text': ref_text,
                'bbox': ref_bbox
            }
            
            if matched_figure:
                mapped_ref['figure_id'] = matched_figure['figure_id']
                mapped_ref['not_matched'] = False
                mapped_ref['match_confidence'] = matched_figure.get('match_confidence', 1.0)
            else:
                mapped_ref['not_matched'] = True
            
            mapped_refs.append(mapped_ref)
        
        return mapped_refs
    
    def _extract_reference_id(self, ref_text: str) -> Optional[str]:
        """Extract ID from reference text with improved patterns"""
        patterns = [
            r'(?:fig|figure)s?\.?\s*(\d+(?:\.\d+)*(?:\s*[a-z])?)',  # Fig 1.2a
            r'(?:tab|table)s?\.?\s*(\d+(?:\.\d+)*)',
            r'(?:eq|equation)s?\.?\s*\(?(\d+(?:\.\d+)*)\)?',
            r'(?:alg|algorithm)s?\.?\s*(\d+(?:\.\d+)*)',
            r'\((\d+(?:\.\d+)*)\)',  # Just (1.2)
        ]
        
        ref_lower = ref_text.lower()
        for pattern in patterns:
            match = re.search(pattern, ref_lower)
            if match:
                return match.group(1).strip()
        return None
    
    def _find_figure_by_id(self, ref_id: str, figures: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find figure with matching ID"""
        # Normalize ID (remove trailing letters for base match)
        base_id = re.sub(r'[a-z]+$', '', ref_id.strip())
        
        for figure in figures:
            fig_id = figure.get('figure_id', '')
            
            # Exact match
            if fig_id == ref_id:
                return {**figure, 'match_confidence': 1.0}
            
            # Base ID match (1.2 matches 1.2a)
            if fig_id == base_id:
                return {**figure, 'match_confidence': 0.9}
            
            # Check if ID appears in figure text
            fig_text = figure.get('text', '').lower()
            if ref_id in fig_text or base_id in fig_text:
                return {**figure, 'match_confidence': 0.8}
        
        return None
    
    def _fuzzy_match_figure(self, ref_text: str, figures: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Fuzzy matching based on text similarity"""
        ref_lower = ref_text.lower()
        best_match = None
        best_score = 0.5  # Minimum threshold
        
        for figure in figures:
            fig_text = figure.get('text', '').lower()
            if not fig_text:
                continue
            
            # Calculate similarity score
            score = self._calculate_similarity(ref_lower, fig_text)
            
            if score > best_score:
                best_score = score
                best_match = {**figure, 'match_confidence': score}
        
        return best_match
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity score"""
        # Simple word overlap similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _spatial_match_figure(self, ref_bbox: Dict[str, int], figures: List[Dict[str, Any]], 
                             page_mapping: Dict[int, List[int]]) -> Optional[Dict[str, Any]]:
        """Match based on spatial proximity"""
        # This would require page information for the reference
        # Implementation depends on your page tracking logic
        return None