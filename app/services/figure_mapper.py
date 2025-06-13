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
        
        # 입력 데이터 검증
        if not references or not figures:
            return self._create_unmapped_references(references)
        
        # 그래프 구축
        self._build_graph(references, figures)
        
        # 관계 추론
        mappings = self._infer_relationships()
        
        # 매핑 결과 생성
        mapped_references = []
        for i, reference in enumerate(references):
            ref_node_id = f"ref_{i}"
            mapped_ref = {
                'text': str(reference.get('text', '')),  # 타입 안전성 보장
                'bbox': reference.get('bbox', {})
            }
            
            if ref_node_id in mappings:
                mapped_ref['figure_id'] = str(mappings[ref_node_id])  # 타입 안전성 보장
                mapped_ref['not_matched'] = False
            else:
                mapped_ref['not_matched'] = True
            
            mapped_references.append(mapped_ref)
        
        return mapped_references
    
    def _create_unmapped_references(self, references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create unmapped references when no figures are available"""
        return [
            {
                'text': str(ref.get('text', '')),
                'bbox': ref.get('bbox', {}),
                'not_matched': True
            }
            for ref in references
        ]
    
    def _build_graph(self, references: List[Dict[str, Any]], figures: List[Dict[str, Any]]):
        """Build document graph with references and figures"""
        # 피규어 노드 추가
        for figure in figures:
            fig_id = str(figure.get('figure_id', ''))  # 타입 안전성 보장
            if not fig_id:  # 빈 ID 처리
                continue
                
            self.graph.add_node(
                fig_id,
                type='figure',
                data=figure,
                page_idx=int(figure.get('page_idx', 0)),
                bbox=figure.get('bbox', {}),
                text=str(figure.get('text', ''))
            )
        
        # 참조 노드 추가
        for i, reference in enumerate(references):
            ref_node_id = f"ref_{i}"
            ref_text = str(reference.get('text', ''))  # 타입 안전성 보장
            
            self.graph.add_node(
                ref_node_id,
                type='reference',
                data=reference,
                text=ref_text,
                bbox=reference.get('bbox', {}),
                page_idx=int(reference.get('page_idx', 0))
            )
            
            # 참조에서 추출한 ID로 직접 연결 시도
            ref_figure_id = self._extract_id_from_reference(ref_text)
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
            ref_page = int(ref_data.get('page_idx', 0))
            ref_bbox = ref_data.get('bbox', {})
            
            for fig_node in fig_nodes:
                fig_data = self.graph.nodes[fig_node]
                fig_page = int(fig_data.get('page_idx', 0))
                fig_bbox = fig_data.get('bbox', {})
                
                # 같은 페이지 관계
                if ref_page == fig_page:
                    distance = self._calculate_distance(ref_bbox, fig_bbox)
                    if distance < 500:  # 픽셀 임계값
                        weight = max(0.0, 1.0 - (distance / 500))  # 음수 방지
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
            ref_text = str(self.graph.nodes[ref_node].get('text', '')).lower()
            
            for fig_node in fig_nodes:
                fig_text = str(self.graph.nodes[fig_node].get('text', '')).lower()
                
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
            connected_figures = []
            
            for successor in self.graph.successors(ref_node):
                if self.graph.nodes[successor]['type'] == 'figure':
                    edge_data = self.graph.get_edge_data(ref_node, successor)
                    
                    if edge_data:
                        # get_edge_data는 단일 dict를 반환함
                        weight = edge_data.get('weight', 0)
                        try:
                            total_weight = float(weight)
                        except (ValueError, TypeError):
                            total_weight = 0.0
                    else:
                        total_weight = 0.0
                    
                    connected_figures.append((successor, total_weight))
            
            if connected_figures:
                connected_figures.sort(key=lambda x: x[1], reverse=True)
                best_figure, best_weight = connected_figures[0]
                
                if best_weight > 0.3:
                    mappings[ref_node] = best_figure
        
        return mappings
        
    def _extract_id_from_reference(self, ref_text: str) -> Optional[str]:
        """Extract figure ID from reference text"""
        if not ref_text:
            return None
            
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
        
        ref_lower = str(ref_text).lower()
        for pattern in patterns:
            match = re.search(pattern, ref_lower)
            if match:
                return match.group(1)
        
        return None
    
    def _is_id_match(self, ref_id: str, figure_data: Dict[str, Any]) -> bool:
        """Check if reference ID matches figure"""
        if not ref_id or not figure_data:
            return False
            
        fig_id = str(figure_data.get('figure_id', ''))
        
        # Direct match
        if fig_id == ref_id:
            return True
        
        # Check if ID appears in figure text
        fig_text = str(figure_data.get('text', '')).lower()
        if ref_id in fig_text:
            return True
        
        return False
    
    def _calculate_distance(self, bbox1: Dict[str, int], bbox2: Dict[str, int]) -> float:
        """Calculate distance between two bounding boxes"""
        if not bbox1 or not bbox2:
            return float('inf')
        
        try:
            # 중심점 간 거리
            x1 = float(bbox1.get('x', 0)) + float(bbox1.get('width', 0)) / 2
            y1 = float(bbox1.get('y', 0)) + float(bbox1.get('height', 0)) / 2
            x2 = float(bbox2.get('x', 0)) + float(bbox2.get('width', 0)) / 2
            y2 = float(bbox2.get('y', 0)) + float(bbox2.get('height', 0)) / 2
            
            return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        except (ValueError, TypeError):
            return float('inf')
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        if not text1 or not text2:
            return 0.0
        
        try:
            # 단어 기반 Jaccard 유사도
            words1 = set(str(text1).split())
            words2 = set(str(text2).split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1 & words2
            union = words1 | words2
            
            return len(intersection) / len(union) if union else 0.0
        except Exception:
            return 0.0
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the constructed graph"""
        try:
            num_nodes = self.graph.number_of_nodes()
            num_edges = self.graph.number_of_edges()
            
            ref_count = len([n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'reference'])
            fig_count = len([n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'figure'])
            
            degrees = [d for n, d in self.graph.degree()]
            avg_degree = np.mean(degrees) if degrees else 0.0
            
            return {
                'num_nodes': num_nodes,
                'num_edges': num_edges,
                'num_references': ref_count,
                'num_figures': fig_count,
                'avg_degree': float(avg_degree)
            }
        except Exception as e:
            print(f"Error calculating graph statistics: {e}")
            return {
                'num_nodes': 0,
                'num_edges': 0,
                'num_references': 0,
                'num_figures': 0,
                'avg_degree': 0.0
            }