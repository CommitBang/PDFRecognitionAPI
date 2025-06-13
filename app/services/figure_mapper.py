import re
from typing import List, Dict, Any, Optional

class FigureMapper:
    def __init__(self):
        """Initialize figure mapper"""
        pass
    
    def map_references_to_figures(self, references: List[Dict[str, Any]], figures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map references to their corresponding figures"""
        mapped_references = []
        
        for reference in references:
            ref_text = reference.get('text', '')
            ref_bbox = reference.get('bbox', {})
            
            # Extract figure ID from reference text
            ref_figure_id = self._extract_id_from_reference(ref_text)
            
            # Find matching figure
            matched_figure = None
            if ref_figure_id:
                matched_figure = self._find_matching_figure(ref_figure_id, figures)
            
            # Create mapped reference
            mapped_ref = {
                'text': ref_text,
                'bbox': ref_bbox
            }
            
            if matched_figure:
                mapped_ref['figure_id'] = matched_figure['figure_id']
                mapped_ref['not_matched'] = False
            else:
                mapped_ref['not_matched'] = True
            
            mapped_references.append(mapped_ref)
        
        return mapped_references
    
    def _extract_id_from_reference(self, ref_text: str) -> Optional[str]:
        """Extract figure ID from reference text"""
        # Patterns to extract IDs from references
        patterns = [
            r'fig\.?\s*(\d+(?:\.\d+)*)',
            r'figure\.?\s*(\d+(?:\.\d+)*)',
            r'table\.?\s*(\d+(?:\.\d+)*)',
            r'tab\.?\s*(\d+(?:\.\d+)*)',
            r'equation\.?\s*(\d+(?:\.\d+)*)',
            r'eq\.?\s*\((\d+(?:\.\d+)*)\)',
            r'\((\d+(?:\.\d+)*)\)',
            r'example\.?\s*(\d+(?:\.\d+)*)',
            r'chart\.?\s*(\d+(?:\.\d+)*)',
            r'graph\.?\s*(\d+(?:\.\d+)*)',
        ]
        
        ref_lower = ref_text.lower()
        for pattern in patterns:
            match = re.search(pattern, ref_lower)
            if match:
                return match.group(1)
        
        return None
    
    def _find_matching_figure(self, ref_id: str, figures: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find figure that matches the reference ID"""
        for figure in figures:
            fig_id = figure.get('figure_id', '')
            
            # Direct match
            if fig_id == ref_id:
                return figure
            
            # Check if figure text contains the ID
            fig_text = figure.get('text', '').lower()
            if ref_id in fig_text:
                return figure
        
        return None