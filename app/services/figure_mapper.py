# app/services/figure_mapper.py - 그래프 기반으로 리팩토링
import re
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

class FigureMapper:
    def __init__(self):
        """Initialize figure mapper with graph-based approach"""
        self.graph = nx.DiGraph()
        self.node_counter = 0
        
    def map_references_to_figures(self, references: List[Dict[str, Any]], figures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map references to their corresponding figures using graph-based approach"""
        # 그래프 초기화
        self.graph.clear()
        self.node_counter = 0
        
        # 그래프 구축
        self._build_graph(references, figures)
        
        # 관계 추론
        mappings = self._infer_relationships()
        
        # 매핑 결과 생성
        mapped_references = []
        for i, reference in enumerate(references):
            ref_node_id = f"ref_{i}"
            mapped_ref = {
                'text': reference.get('text', ''),
                'bbox': reference.get('bbox', {})
            }
            
            if ref_node_id in mappings:
                mapped_ref['figure_id'] = mappings[ref_node_id]
                mapped_ref['not_matched'] = False
            else:
                mapped_ref['not_matched'] = True
            
            mapped_references.append(mapped_ref)
        
        return mapped_references
    
    def _build_graph(self, references: List[Dict[str, Any]], figures: List[Dict[str, Any]]):
        """Build document graph with references and figures"""
        # 피규어 노드 추가
        for figure in figures:
            fig_id = figure.get('figure_id', '')
            self.graph.add_node(
                fig_id,
                type='figure',
                data=figure,
                page_idx=figure.get('page_idx', 0),
                bbox=figure.get('bbox', {}),
                text=figure.get('text', '')
            )
        
        # 참조 노드 추가
        for i, reference in enumerate(references):
            ref_node_id = f"ref_{i}"
            self.graph.add_node(
                ref_node_id,
                type='reference',
                data=reference,
                text=reference.get('text', ''),
                bbox=reference.get('bbox', {}),
                page_idx=reference.get('page_idx', 0)  # PDFProcessor에서 제공되어야 함
            )
            
            # 참조에서 추출한 ID로 직접 연결 시도
            ref_figure_id = self._extract_id_from_reference(reference.get('text', ''))
            if ref_figure_id:
                # ID 기반 잠재적 연결
                for fig_node in self.graph.nodes():
                    if self.graph.nodes[fig_node].get('type') == 'figure':
                        fig_data = self.graph.nodes[fig_node]['data']
                        if self._is_id_match(ref_figure_id, fig_data):
                            self.graph.add_edge(
                                ref_node_id, 
                                fig_node,
                                weight=0.8,
                                relation='id_match'
                            )
        
        # 공간적 관계 추가
        self._add_spatial_relationships()
        
        # 의미론적 관계 추가
        self._add_semantic_relationships()
    
    def _add_spatial_relationships(self):
        """Add spatial relationships between nodes"""
        ref_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'reference']
        fig_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'figure']
        
        for ref_node in ref_nodes:
            ref_data = self.graph.nodes[ref_node]
            ref_page = ref_data.get('page_idx', 0)
            ref_bbox = ref_data.get('bbox', {})
            
            for fig_node in fig_nodes:
                fig_data = self.graph.nodes[fig_node]
                fig_page = fig_data.get('page_idx', 0)
                fig_bbox = fig_data.get('bbox', {})
                
                # 같은 페이지 관계
                if ref_page == fig_page:
                    distance = self._calculate_distance(ref_bbox, fig_bbox)
                    if distance < 500:  # 픽셀 임계값
                        weight = 1.0 - (distance / 500)
                        self.graph.add_edge(
                            ref_node,
                            fig_node,
                            weight=weight * 0.5,
                            relation='same_page',
                            distance=distance
                        )
                
                # 인접 페이지 관계
                elif abs(ref_page - fig_page) == 1:
                    # 참조가 피규어 다음 페이지에 있는 경우 가중치 부여
                    if ref_page > fig_page:
                        self.graph.add_edge(
                            ref_node,
                            fig_node,
                            weight=0.3,
                            relation='next_page'
                        )
    
    def _add_semantic_relationships(self):
        """Add semantic relationships based on text similarity"""
        ref_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'reference']
        fig_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'figure']
        
        for ref_node in ref_nodes:
            ref_text = self.graph.nodes[ref_node].get('text', '').lower()
            
            for fig_node in fig_nodes:
                fig_text = self.graph.nodes[fig_node].get('text', '').lower()
                
                # 텍스트 유사도 계산
                similarity = self._calculate_text_similarity(ref_text, fig_text)
                if similarity > 0.2:
                    self.graph.add_edge(
                        ref_node,
                        fig_node,
                        weight=similarity * 0.4,
                        relation='semantic'
                    )
    
    def _infer_relationships(self) -> Dict[str, str]:
        """Infer figure-reference relationships from graph"""
        mappings = {}
        
        ref_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'reference']
        
        for ref_node in ref_nodes:
            # 참조 노드에서 연결된 모든 피규어 노드 찾기
            connected_figures = []
            
            for successor in self.graph.successors(ref_node):
                if self.graph.nodes[successor]['type'] == 'figure':
                    # 모든 엣지의 가중치 합산
                    total_weight = 0
                    for edge_data in self.graph.get_edge_data(ref_node, successor).values():
                        if isinstance(edge_data, dict):
                            total_weight = edge_data.get('weight', 0)
                        else:
                            total_weight += edge_data
                    
                    connected_figures.append((successor, total_weight))
            
            # 가장 높은 가중치를 가진 피규어 선택
            if connected_figures:
                connected_figures.sort(key=lambda x: x[1], reverse=True)
                best_figure, best_weight = connected_figures[0]
                
                # 임계값 이상인 경우에만 매핑
                if best_weight > 0.3:
                    mappings[ref_node] = best_figure
        
        return mappings
    
    def _extract_id_from_reference(self, ref_text: str) -> Optional[str]:
        """Extract figure ID from reference text"""
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
    
    def _is_id_match(self, ref_id: str, figure_data: Dict[str, Any]) -> bool:
        """Check if reference ID matches figure"""
        fig_id = figure_data.get('figure_id', '')
        
        # Direct match
        if fig_id == ref_id:
            return True
        
        # Check if ID appears in figure text
        fig_text = figure_data.get('text', '').lower()
        if ref_id in fig_text:
            return True
        
        return False
    
    def _calculate_distance(self, bbox1: Dict[str, int], bbox2: Dict[str, int]) -> float:
        """Calculate distance between two bounding boxes"""
        if not bbox1 or not bbox2:
            return float('inf')
        
        # 중심점 간 거리
        x1 = bbox1.get('x', 0) + bbox1.get('width', 0) / 2
        y1 = bbox1.get('y', 0) + bbox1.get('height', 0) / 2
        x2 = bbox2.get('x', 0) + bbox2.get('width', 0) / 2
        y2 = bbox2.get('y', 0) + bbox2.get('height', 0) / 2
        
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        if not text1 or not text2:
            return 0.0
        
        # 단어 기반 Jaccard 유사도
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the constructed graph"""
        return {
            'num_nodes': self.graph.number_of_nodes(),
            'num_edges': self.graph.number_of_edges(),
            'num_references': len([n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'reference']),
            'num_figures': len([n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'figure']),
            'avg_degree': np.mean([d for n, d in self.graph.degree()]) if self.graph.number_of_nodes() > 0 else 0
        }