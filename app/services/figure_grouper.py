# app/services/figure_grouper.py
from typing import List, Dict, Any, Tuple, Optional
import re
from dataclasses import dataclass
from enum import Enum

class LayoutType(Enum):
    """Layout element types"""
    FIGURE = "figure"
    FIGURE_TITLE = "figure_title" 
    FIGURE_CAPTION = "figure_caption"
    TABLE = "table"
    TABLE_CAPTION = "table_caption"
    FORMULA = "formula"
    FORMULA_NUMBER = "number"
    ALGORITHM = "algorithm"
    IMAGE = "image"
    TEXT = "text"

@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int
    
    @property
    def x2(self):
        return self.x + self.width
    
    @property
    def y2(self):
        return self.y + self.height
    
    @property
    def center_x(self):
        return self.x + self.width // 2
    
    @property
    def center_y(self):
        return self.y + self.height // 2
    
    def iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union"""
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x2, other.x2)
        y2 = min(self.y2, other.y2)
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        union = self.width * self.height + other.width * other.height - intersection
        return intersection / union if union > 0 else 0
    
    def distance_to(self, other: 'BoundingBox') -> float:
        """Calculate distance between centers"""
        dx = self.center_x - other.center_x
        dy = self.center_y - other.center_y
        return (dx * dx + dy * dy) ** 0.5
    
    def vertical_overlap(self, other: 'BoundingBox') -> bool:
        """Check if boxes overlap vertically"""
        return not (self.y2 < other.y or other.y2 < self.y)
    
    def horizontal_overlap(self, other: 'BoundingBox') -> bool:
        """Check if boxes overlap horizontally"""
        return not (self.x2 < other.x or other.x2 < self.x)


class FigureGrouper:
    """Groups related figure elements (title, image, caption) into single figures"""
    
    def __init__(self, vertical_threshold: int = 100, horizontal_threshold: int = 200):
        self.vertical_threshold = vertical_threshold  # Max vertical distance for grouping
        self.horizontal_threshold = horizontal_threshold  # Max horizontal distance
        
        # Patterns for extracting figure IDs
        self.id_patterns = [
            (r'(?:Fig|Figure)\.?\s*(\d+(?:\.\d+)*)', 'figure'),
            (r'(?:Table|Tab)\.?\s*(\d+(?:\.\d+)*)', 'table'),
            (r'(?:Equation|Eq)\.?\s*\((\d+(?:\.\d+)*)\)', 'formula'),
            (r'(?:Algorithm|Alg)\.?\s*(\d+(?:\.\d+)*)', 'algorithm'),
            (r'\((\d+(?:\.\d+)*)\)', 'formula'),  # Just numbers in parentheses
        ]
        self.compiled_patterns = [(re.compile(p, re.IGNORECASE), t) for p, t in self.id_patterns]
    
    def group_figure_elements(self, layout_blocks: List[Dict[str, Any]], page_idx: int) -> List[Dict[str, Any]]:
        """Group related layout elements into complete figures"""
        # Convert to internal format
        elements = []
        for block in layout_blocks:
            bbox = BoundingBox(
                block['bbox']['x'],
                block['bbox']['y'], 
                block['bbox']['width'],
                block['bbox']['height']
            )
            elements.append({
                'type': block.get('type', ''),
                'bbox': bbox,
                'text': block.get('text', ''),
                'confidence': block.get('confidence', 0.0),
                'original': block
            })
        
        # Group elements
        groups = self._create_groups(elements)
        
        # Convert groups to figure objects
        figures = []
        for group in groups:
            figure = self._create_figure_from_group(group, page_idx)
            if figure:
                figures.append(figure)
        
        return figures
    
    def _create_groups(self, elements: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Create groups of related elements"""
        groups = []
        used = set()
        
        # First, identify core figure elements (images, tables, formulas)
        core_elements = [e for e in elements if self._is_core_element(e['type'])]
        
        for i, core in enumerate(core_elements):
            if i in used:
                continue
            
            group = [core]
            used.add(i)
            
            # Find related elements (titles, captions, numbers)
            for j, elem in enumerate(elements):
                if j in used or elem == core:
                    continue
                
                if self._should_group_elements(core, elem):
                    group.append(elem)
                    used.add(j)
            
            groups.append(group)
        
        # Handle standalone titles/captions that might belong to nearby figures
        remaining = [e for i, e in enumerate(elements) if i not in used]
        for elem in remaining:
            if self._is_figure_metadata(elem['type']):
                # Find nearest group
                best_group = self._find_best_group_for_element(elem, groups)
                if best_group is not None:
                    groups[best_group].append(elem)
        
        return groups
    
    def _is_core_element(self, elem_type: str) -> bool:
        """Check if element is a core figure element"""
        core_types = {'figure', 'image', 'table', 'formula', 'algorithm'}
        return elem_type in core_types
    
    def _is_figure_metadata(self, elem_type: str) -> bool:
        """Check if element is figure metadata (title, caption, number)"""
        metadata_types = {'figure_title', 'figure_caption', 'table_caption', 'number'}
        return elem_type in metadata_types
    
    def _should_group_elements(self, core: Dict[str, Any], elem: Dict[str, Any]) -> bool:
        """Determine if two elements should be grouped"""
        core_bbox = core['bbox']
        elem_bbox = elem['bbox']
        elem_type = elem['type']
        
        # Check if it's a related metadata element
        if not self._is_figure_metadata(elem_type):
            return False
        
        # Check spatial relationship
        if elem_type in ['figure_title', 'table_caption']:
            # Titles/captions are usually above or below
            if elem_bbox.horizontal_overlap(core_bbox):
                # Check vertical distance
                if elem_bbox.y2 < core_bbox.y:  # Above
                    return (core_bbox.y - elem_bbox.y2) < self.vertical_threshold
                else:  # Below
                    return (elem_bbox.y - core_bbox.y2) < self.vertical_threshold
        
        elif elem_type == 'number':
            # Formula numbers are usually to the right
            if elem_bbox.vertical_overlap(core_bbox):
                return (elem_bbox.x - core_bbox.x2) < self.horizontal_threshold
        
        # General proximity check
        return elem_bbox.distance_to(core_bbox) < self.vertical_threshold * 2
    
    def _find_best_group_for_element(self, elem: Dict[str, Any], groups: List[List[Dict[str, Any]]]) -> Optional[int]:
        """Find the best group for an unassigned element"""
        best_idx = None
        best_distance = float('inf')
        
        elem_bbox = elem['bbox']
        
        for idx, group in enumerate(groups):
            # Calculate distance to group centroid
            group_bbox = self._get_group_bbox(group)
            distance = elem_bbox.distance_to(group_bbox)
            
            # Check if element makes sense for this group type
            group_type = self._determine_group_type(group)
            if self._is_compatible_element(elem['type'], group_type) and distance < best_distance:
                best_distance = distance
                best_idx = idx
        
        # Only assign if within reasonable distance
        if best_distance < self.vertical_threshold * 3:
            return best_idx
        return None
    
    def _get_group_bbox(self, group: List[Dict[str, Any]]) -> BoundingBox:
        """Get bounding box that encompasses entire group"""
        if not group:
            return BoundingBox(0, 0, 0, 0)
        
        min_x = min(e['bbox'].x for e in group)
        min_y = min(e['bbox'].y for e in group)
        max_x = max(e['bbox'].x2 for e in group)
        max_y = max(e['bbox'].y2 for e in group)
        
        return BoundingBox(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def _determine_group_type(self, group: List[Dict[str, Any]]) -> str:
        """Determine the primary type of a group"""
        for elem in group:
            if self._is_core_element(elem['type']):
                return elem['type']
        return 'unknown'
    
    def _is_compatible_element(self, elem_type: str, group_type: str) -> bool:
        """Check if element type is compatible with group type"""
        compatibility = {
            'figure': ['figure_title', 'figure_caption'],
            'table': ['table_caption', 'figure_title'],  # Sometimes titles are generic
            'formula': ['number', 'figure_caption'],
            'algorithm': ['figure_title', 'figure_caption'],
            'image': ['figure_title', 'figure_caption']
        }
        return elem_type in compatibility.get(group_type, [])
    
    def _create_figure_from_group(self, group: List[Dict[str, Any]], page_idx: int) -> Optional[Dict[str, Any]]:
        """Create a figure object from a group of elements"""
        if not group:
            return None
        
        # Find core element
        core_elem = None
        title_elem = None
        caption_elem = None
        number_elem = None
        
        for elem in group:
            if self._is_core_element(elem['type']):
                core_elem = elem
            elif elem['type'] in ['figure_title', 'table_caption']:
                if not title_elem or len(elem['text']) > len(title_elem['text']):
                    title_elem = elem
            elif elem['type'] == 'figure_caption':
                caption_elem = elem
            elif elem['type'] == 'number':
                number_elem = elem
        
        if not core_elem:
            return None
        
        # Extract figure ID
        figure_id, id_source = self._extract_figure_id(group)
        
        # Get group bounding box
        group_bbox = self._get_group_bbox(group)
        
        # Combine text from all elements
        text_parts = []
        if title_elem:
            text_parts.append(title_elem['text'])
        if caption_elem:
            text_parts.append(caption_elem['text'])
        if number_elem and number_elem not in [title_elem, caption_elem]:
            text_parts.append(number_elem['text'])
        
        combined_text = ' '.join(text_parts).strip()
        
        return {
            'figure_id': figure_id,
            'type': self._determine_group_type(group),
            'bbox': {
                'x': group_bbox.x,
                'y': group_bbox.y,
                'width': group_bbox.width,
                'height': group_bbox.height
            },
            'page_idx': page_idx,
            'text': combined_text,
            'confidence': max(e['confidence'] for e in group),
            'elements': [e['original'] for e in group],  # Keep original elements
            'id_source': id_source
        }
    
    def _extract_figure_id(self, group: List[Dict[str, Any]]) -> Tuple[str, str]:
        """Extract figure ID from group elements"""
        # Try to extract from any text in the group
        all_text = ' '.join(e['text'] for e in group if e['text'])
        
        for pattern, fig_type in self.compiled_patterns:
            match = pattern.search(all_text)
            if match:
                return match.group(1), 'extracted'
        
        # Fallback: generate from position
        core_elem = next((e for e in group if self._is_core_element(e['type'])), group[0])
        return f"{core_elem['bbox'].y}_{core_elem['bbox'].x}", 'generated'
    