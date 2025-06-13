# app/services/figure_grouper.py
from typing import List, Dict, Any, Tuple, Optional, Set
import re
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import defaultdict

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
    
    @property
    def area(self):
        return self.width * self.height
    
    def iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union"""
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x2, other.x2)
        y2 = min(self.y2, other.y2)
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        union = self.area + other.area - intersection
        return intersection / union if union > 0 else 0
    
    def distance_to(self, other: 'BoundingBox') -> float:
        """Calculate minimum distance between boxes"""
        # If boxes overlap, distance is 0
        if not (self.x2 < other.x or other.x2 < self.x or 
                self.y2 < other.y or other.y2 < self.y):
            return 0.0
        
        # Calculate distances between edges
        dx = max(0, max(self.x - other.x2, other.x - self.x2))
        dy = max(0, max(self.y - other.y2, other.y - self.y2))
        
        return (dx * dx + dy * dy) ** 0.5
    
    def vertical_overlap(self, other: 'BoundingBox') -> bool:
        """Check if boxes overlap vertically"""
        return not (self.y2 < other.y or other.y2 < self.y)
    
    def horizontal_overlap(self, other: 'BoundingBox') -> bool:
        """Check if boxes overlap horizontally"""
        return not (self.x2 < other.x or other.x2 < self.x)
    
    def is_above(self, other: 'BoundingBox', threshold: int = 50) -> bool:
        """Check if this box is above another"""
        return self.y2 < other.y and abs(self.center_x - other.center_x) < threshold
    
    def is_below(self, other: 'BoundingBox', threshold: int = 50) -> bool:
        """Check if this box is below another"""
        return self.y > other.y2 and abs(self.center_x - other.center_x) < threshold


class FigureGrouper:
    """Groups related figure elements (title, image, caption) into single figures"""
    
    def __init__(self, vertical_threshold: int = 50, horizontal_threshold: int = 100):
        self.vertical_threshold = vertical_threshold  # Max vertical distance for grouping
        self.horizontal_threshold = horizontal_threshold  # Max horizontal distance
        self.alignment_threshold = 50  # Max alignment deviation
        
        # Patterns for extracting figure IDs
        self.id_patterns = [
            (r'(?:Fig|Figure)\.?\s*(\d+(?:\.\d+)*)', 'figure'),
            (r'(?:Table|Tab)\.?\s*(\d+(?:\.\d+)*)', 'table'),
            (r'(?:Equation|Eq)\.?\s*\((\d+(?:\.\d+)*)\)', 'formula'),
            (r'(?:Algorithm|Alg)\.?\s*(\d+(?:\.\d+)*)', 'algorithm'),
            (r'(?:Example|Ex)\.?\s*(\d+(?:\.\d+)*)', 'example'),
            (r'\((\d+(?:\.\d+)*)\)', 'formula'),  # Just numbers in parentheses
        ]
        self.compiled_patterns = [(re.compile(p, re.IGNORECASE), t) for p, t in self.id_patterns]
        
        # Layout patterns (typical arrangements)
        self.layout_patterns = {
            'figure_standard': ['figure_title', 'figure/image', 'figure_caption'],
            'table_standard': ['table_caption', 'table'],
            'formula_standard': ['formula', 'number'],  # Number usually to the right
            'algorithm_standard': ['figure_title', 'algorithm', 'figure_caption'],
        }
    
    def group_figure_elements(self, layout_blocks: List[Dict[str, Any]], page_idx: int) -> List[Dict[str, Any]]:
        """Group related layout elements into complete figures"""
        # Convert to internal format with enhanced metadata
        elements = []
        for block in layout_blocks:
            bbox = BoundingBox(
                block['bbox']['x'],
                block['bbox']['y'], 
                block['bbox']['width'],
                block['bbox']['height']
            )
            
            # Extract ID and type information
            text = block.get('text', '')
            element_id = None
            id_type = None
            
            for pattern, fig_type in self.compiled_patterns:
                match = pattern.search(text)
                if match:
                    element_id = match.group(1)
                    id_type = fig_type
                    break
            
            elements.append({
                'type': block.get('type', ''),
                'bbox': bbox,
                'text': text,
                'confidence': block.get('confidence', 0.0),
                'original': block,
                'element_id': element_id,
                'id_type': id_type
            })
        
        # Apply multiple grouping strategies
        # Strategy 1: ID-based grouping
        id_groups = self._group_by_ids(elements)
        
        # Strategy 2: Spatial pattern matching
        pattern_groups = self._group_by_patterns(elements)
        
        # Strategy 3: Enhanced proximity-based grouping (modified _create_groups)
        proximity_groups = self._create_groups(elements)
        
        # Merge groups from different strategies
        final_groups = self._merge_groups(id_groups, pattern_groups, proximity_groups)
        
        # Convert groups to figure objects
        figures = []
        for group in final_groups:
            figure = self._create_figure_from_group(group, page_idx)
            if figure:
                figures.append(figure)
        
        return figures
    
    def _group_by_ids(self, elements: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group elements by matching IDs"""
        id_groups = defaultdict(list)
        
        # First pass: group elements with same ID
        for elem in elements:
            if elem['element_id']:
                key = f"{elem['id_type']}_{elem['element_id']}"
                id_groups[key].append(elem)
        
        # Second pass: find elements without IDs that might belong to ID groups
        for elem in elements:
            if not elem['element_id']:
                best_group = None
                best_score = 0
                
                for key, group in id_groups.items():
                    score = self._calculate_group_affinity(elem, group)
                    if score > best_score:
                        best_score = score
                        best_group = key
                
                if best_group and best_score > 0.5:
                    id_groups[best_group].append(elem)
        
        return list(id_groups.values())
    
    def _group_by_patterns(self, elements: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group elements by common layout patterns"""
        groups = []
        used = set()
        
        # Sort elements by y-coordinate (top to bottom)
        sorted_elements = sorted(elements, key=lambda e: e['bbox'].y)
        
        for pattern_name, pattern_types in self.layout_patterns.items():
            for i, elem in enumerate(sorted_elements):
                if i in used:
                    continue
                
                # Try to match pattern starting from this element
                group = self._match_pattern(sorted_elements, i, pattern_types, used)
                if len(group) >= 2:  # Valid group
                    groups.append(group)
                    for e in group:
                        idx = sorted_elements.index(e)
                        used.add(idx)
        
        return groups
    
    def _match_pattern(self, elements: List[Dict[str, Any]], start_idx: int, 
                       pattern: List[str], used: Set[int]) -> List[Dict[str, Any]]:
        """Try to match a specific pattern starting from given index"""
        group = []
        current_elem = elements[start_idx]
        
        # Check if starting element matches pattern
        if not self._type_matches_pattern(current_elem['type'], pattern[0]):
            return []
        
        group.append(current_elem)
        pattern_idx = 1
        
        # Look for subsequent pattern elements
        for i in range(start_idx + 1, len(elements)):
            if i in used or pattern_idx >= len(pattern):
                break
            
            elem = elements[i]
            
            # Check spatial relationship
            if not self._is_spatially_related(group[-1], elem):
                continue
            
            # Check type match
            if self._type_matches_pattern(elem['type'], pattern[pattern_idx]):
                group.append(elem)
                pattern_idx += 1
        
        # Validate group completeness
        if pattern_idx < len(pattern) * 0.6:  # At least 60% of pattern matched
            return []
        
        return group
    
    def _create_groups(self, elements: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Enhanced proximity-based grouping with better heuristics"""
        groups = []
        used = set()
        
        # First, identify core figure elements (images, tables, formulas)
        core_elements = [(i, e) for i, e in enumerate(elements) if self._is_core_element(e['type'])]
        
        for i, core in core_elements:
            if i in used:
                continue
            
            group = [core]
            used.add(i)
            
            # Calculate affinity scores for all other elements
            affinities = []
            for j, elem in enumerate(elements):
                if j in used or elem == core:
                    continue
                
                score = self._calculate_element_affinity(core, elem)
                if score > 0:
                    affinities.append((j, elem, score))
            
            # Sort by affinity score and add to group
            affinities.sort(key=lambda x: x[2], reverse=True)
            
            for j, elem, score in affinities:
                if score > 0.3 and self._should_group_elements(core, elem):
                    group.append(elem)
                    used.add(j)
            
            groups.append(group)
        
        # Handle standalone titles/captions that might belong to nearby figures
        remaining = [(i, e) for i, e in enumerate(elements) if i not in used]
        for i, elem in remaining:
            if self._is_figure_metadata(elem['type']):
                # Find nearest group with enhanced scoring
                best_group_idx = self._find_best_group_for_element(elem, groups)
                if best_group_idx is not None:
                    groups[best_group_idx].append(elem)
        
        return groups
    
    def _calculate_element_affinity(self, elem1: Dict[str, Any], elem2: Dict[str, Any]) -> float:
        """Calculate affinity score between two elements"""
        scores = []
        
        # Distance score
        distance = elem1['bbox'].distance_to(elem2['bbox'])
        max_distance = 300
        distance_score = max(0, 1.0 - distance / max_distance)
        scores.append(distance_score * 0.4)
        
        # Type compatibility score
        if self._is_compatible_element(elem2['type'], self._determine_group_type([elem1])):
            scores.append(0.3)
        else:
            scores.append(0.0)
        
        # Alignment score
        if elem1['bbox'].is_above(elem2['bbox']) or elem1['bbox'].is_below(elem2['bbox']):
            x_diff = abs(elem1['bbox'].center_x - elem2['bbox'].center_x)
            alignment_score = max(0, 1.0 - x_diff / self.alignment_threshold)
            scores.append(alignment_score * 0.2)
        elif elem1['bbox'].horizontal_overlap(elem2['bbox']):
            scores.append(0.2)
        else:
            scores.append(0.0)
        
        # ID matching bonus
        if elem1['element_id'] and elem2['element_id'] and elem1['element_id'] == elem2['element_id']:
            scores.append(0.5)
        
        return sum(scores)
    
    def _calculate_group_affinity(self, elem: Dict[str, Any], group: List[Dict[str, Any]]) -> float:
        """Calculate how well an element fits with a group"""
        if not group:
            return 0.0
        
        # Calculate average affinity with group members
        affinities = [self._calculate_element_affinity(elem, g) for g in group]
        return np.mean(affinities)
    
    def _merge_groups(self, *group_lists) -> List[List[Dict[str, Any]]]:
        """Merge groups from different strategies"""
        all_groups = []
        element_to_groups = defaultdict(set)
        
        # Collect all groups and track element membership
        for group_list in group_lists:
            for i, group in enumerate(group_list):
                group_id = len(all_groups)
                all_groups.append(group)
                
                for elem in group:
                    elem_id = id(elem)
                    element_to_groups[elem_id].add(group_id)
        
        # Merge overlapping groups
        merged = []
        used_groups = set()
        
        for i, group in enumerate(all_groups):
            if i in used_groups:
                continue
            
            merged_group = list(group)
            used_groups.add(i)
            
            # Find overlapping groups
            for elem in group:
                elem_id = id(elem)
                for other_group_id in element_to_groups[elem_id]:
                    if other_group_id != i and other_group_id not in used_groups:
                        # Merge if significant overlap
                        other_group = all_groups[other_group_id]
                        overlap = len(set(id(e) for e in group) & 
                                    set(id(e) for e in other_group))
                        
                        if overlap >= min(len(group), len(other_group)) * 0.5:
                            for e in other_group:
                                if e not in merged_group:
                                    merged_group.append(e)
                            used_groups.add(other_group_id)
            
            # Remove duplicates while preserving order
            unique_group = []
            seen = set()
            for elem in merged_group:
                elem_id = id(elem)
                if elem_id not in seen:
                    seen.add(elem_id)
                    unique_group.append(elem)
            
            merged.append(unique_group)
        
        return merged
    
    def _type_matches_pattern(self, elem_type: str, pattern_type: str) -> bool:
        """Check if element type matches pattern specification"""
        if '/' in pattern_type:
            # Multiple acceptable types
            acceptable_types = pattern_type.split('/')
            return elem_type in acceptable_types
        return elem_type == pattern_type
    
    def _is_spatially_related(self, elem1: Dict[str, Any], elem2: Dict[str, Any]) -> bool:
        """Check if two elements are spatially related"""
        bbox1 = elem1['bbox']
        bbox2 = elem2['bbox']
        
        # Vertical relationship
        if bbox1.is_above(bbox2, self.alignment_threshold * 2):
            return bbox2.y - bbox1.y2 < self.vertical_threshold
        
        # Horizontal relationship (for formulas with numbers)
        if abs(bbox1.center_y - bbox2.center_y) < bbox1.height:
            return abs(bbox1.x - bbox2.x2) < self.horizontal_threshold or \
                   abs(bbox2.x - bbox1.x2) < self.horizontal_threshold
        
        return False
    
    def _is_core_element(self, elem_type: str) -> bool:
        """Check if element is a core figure element"""
        core_types = {'figure', 'image', 'table', 'formula', 'algorithm'}
        return elem_type in core_types
    
    def _is_figure_metadata(self, elem_type: str) -> bool:
        """Check if element is figure metadata (title, caption, number)"""
        metadata_types = {'figure_title', 'figure_caption', 'table_caption', 'number'}
        return elem_type in metadata_types
    
    def _should_group_elements(self, core: Dict[str, Any], elem: Dict[str, Any]) -> bool:
        """Enhanced decision logic for grouping two elements"""
        core_bbox = core['bbox']
        elem_bbox = elem['bbox']
        elem_type = elem['type']
        
        # Check if it's a related metadata element
        if not self._is_figure_metadata(elem_type):
            return False
        
        # Enhanced spatial relationship checks
        if elem_type in ['figure_title', 'table_caption']:
            # Titles/captions are usually above or below
            if elem_bbox.horizontal_overlap(core_bbox) or \
               abs(elem_bbox.center_x - core_bbox.center_x) < self.alignment_threshold * 2:
                # Check vertical distance
                if elem_bbox.y2 < core_bbox.y:  # Above
                    return (core_bbox.y - elem_bbox.y2) < self.vertical_threshold * 2
                else:  # Below
                    return (elem_bbox.y - core_bbox.y2) < self.vertical_threshold * 2
        
        elif elem_type == 'number':
            # Formula numbers are usually to the right
            if elem_bbox.vertical_overlap(core_bbox) or \
               abs(elem_bbox.center_y - core_bbox.center_y) < core_bbox.height / 2:
                return (elem_bbox.x - core_bbox.x2) < self.horizontal_threshold
        
        # General proximity check with relaxed threshold
        return elem_bbox.distance_to(core_bbox) < self.vertical_threshold * 3
    
    def _find_best_group_for_element(self, elem: Dict[str, Any], groups: List[List[Dict[str, Any]]]) -> Optional[int]:
        """Find the best group for an unassigned element with enhanced scoring"""
        best_idx = None
        best_score = 0
        
        elem_bbox = elem['bbox']
        
        for idx, group in enumerate(groups):
            # Calculate comprehensive score
            score = 0
            
            # 1. Distance to group centroid
            group_bbox = self._get_group_bbox(group)
            distance = elem_bbox.distance_to(group_bbox)
            distance_score = max(0, 1.0 - distance / (self.vertical_threshold * 3))
            score += distance_score * 0.4
            
            # 2. Type compatibility
            group_type = self._determine_group_type(group)
            if self._is_compatible_element(elem['type'], group_type):
                score += 0.3
            
            # 3. Alignment with group members
            alignment_scores = []
            for member in group:
                member_bbox = member['bbox']
                if elem_bbox.is_above(member_bbox) or elem_bbox.is_below(member_bbox):
                    x_diff = abs(elem_bbox.center_x - member_bbox.center_x)
                    alignment_scores.append(max(0, 1.0 - x_diff / self.alignment_threshold))
            
            if alignment_scores:
                score += max(alignment_scores) * 0.2
            
            # 4. ID matching
            if elem['element_id']:
                for member in group:
                    if member['element_id'] == elem['element_id']:
                        score += 0.5
                        break
            
            if score > best_score:
                best_score = score
                best_idx = idx
        
        # Only assign if score is above threshold
        if best_score > 0.3:
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
        
        # Find core element and metadata elements
        core_elem = None
        title_elem = None
        caption_elem = None
        number_elem = None
        
        # Prioritize by area for core element
        for elem in group:
            if self._is_core_element(elem['type']):
                if not core_elem or elem['bbox'].area > core_elem['bbox'].area:
                    core_elem = elem
            elif elem['type'] in ['figure_title', 'table_caption']:
                if not title_elem or len(elem['text']) > len(title_elem['text']):
                    title_elem = elem
            elif elem['type'] == 'figure_caption':
                caption_elem = elem
            elif elem['type'] == 'number':
                number_elem = elem
        
        if not core_elem:
            # If no core element, use the largest element
            core_elem = max(group, key=lambda e: e['bbox'].area)
        
        # Extract figure ID (prefer extracted ID over generated)
        figure_id, id_source = self._extract_figure_id(group)
        
        # Get group bounding box
        group_bbox = self._get_group_bbox(group)
        
        # Combine text from all elements
        text_parts = []
        if title_elem:
            text_parts.append(title_elem['text'])
        if caption_elem and caption_elem != title_elem:
            text_parts.append(caption_elem['text'])
        if number_elem and number_elem not in [title_elem, caption_elem]:
            text_parts.append(number_elem['text'])
        
        # Add any remaining text from core element if not already included
        if core_elem['text'] and core_elem not in [title_elem, caption_elem, number_elem]:
            text_parts.append(core_elem['text'])
        
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
            'id_source': id_source,
            'grouping_method': 'multi_strategy'  # Indicate enhanced grouping
        }
    
    def _extract_figure_id(self, group: List[Dict[str, Any]]) -> Tuple[str, str]:
        """Extract figure ID from group elements with preference for extracted IDs"""
        # First, try to use already extracted IDs
        for elem in group:
            if elem['element_id']:
                return elem['element_id'], 'extracted'
        
        # Then, try to extract from combined text
        all_text = ' '.join(e['text'] for e in group if e['text'])
        
        for pattern, fig_type in self.compiled_patterns:
            match = pattern.search(all_text)
            if match:
                return match.group(1), 'extracted'
        
        # Fallback: generate from position
        core_elem = next((e for e in group if self._is_core_element(e['type'])), group[0])
        return f"{core_elem['bbox'].y}_{core_elem['bbox'].x}", 'generated'
    
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
    
    def _boxes_overlap(self, bbox1: Dict[str, int], bbox2: Dict[str, int]) -> bool:
        """Check if two bounding boxes overlap"""
        x1_1 = bbox1['x']
        y1_1 = bbox1['y']
        x2_1 = x1_1 + bbox1['width']
        y2_1 = y1_1 + bbox1['height']
        
        x1_2 = bbox2['x']
        y1_2 = bbox2['y']
        x2_2 = x1_2 + bbox2['width']
        y2_2 = y1_2 + bbox2['height']
        
        # Check if boxes overlap
        return (x1_1 < x2_2 and x2_1 > x1_2 and 
                y1_1 < y2_2 and y2_1 > y1_2)