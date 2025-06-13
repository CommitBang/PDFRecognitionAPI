# app/services/figure_mapper.py - 타입을 구분하는 개선된 버전
import re
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from enum import Enum

class ReferenceType(Enum):
    """참조 타입 정의"""
    FIGURE = "figure"
    TABLE = "table"
    EQUATION = "equation"
    EXAMPLE = "example"
    ALGORITHM = "algorithm"
    UNKNOWN = "unknown"

class FigureMapper:
    def __init__(self):
        """Initialize figure mapper with graph-based approach"""
        self.graph = nx.DiGraph()
        self.node_counter = 0
        
        # 타입별 패턴 정의
        self.type_patterns = {
            ReferenceType.FIGURE: [
                r'fig(?:ure)?\.?\s*(\d+(?:\.\d+)*)',
                r'그림\.?\s*(\d+(?:\.\d+)*)',
            ],
            ReferenceType.TABLE: [
                r'tab(?:le)?\.?\s*(\d+(?:\.\d+)*)',
                r'표\.?\s*(\d+(?:\.\d+)*)',
            ],
            ReferenceType.EQUATION: [
                r'eq(?:uation)?\.?\s*\((\d+(?:\.\d+)*)\)',
                r'eq(?:uation)?\.?\s*(\d+(?:\.\d+)*)',
                r'(?<!\w)\((\d+(?:\.\d+)*)\)(?!\w)',  # 단독 괄호 숫자
                r'식\.?\s*\((\d+(?:\.\d+)*)\)',
            ],
            ReferenceType.EXAMPLE: [
                r'ex(?:ample)?\.?\s*(\d+(?:\.\d+)*)',
                r'예제\.?\s*(\d+(?:\.\d+)*)',
            ],
            ReferenceType.ALGORITHM: [
                r'alg(?:orithm)?\.?\s*(\d+(?:\.\d+)*)',
                r'알고리즘\.?\s*(\d+(?:\.\d+)*)',
            ]
        }
        
        # 컴파일된 패턴 저장
        self.compiled_patterns = {}
        for ref_type, patterns in self.type_patterns.items():
            self.compiled_patterns[ref_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
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
                'text': str(reference.get('text', '')),
                'bbox': reference.get('bbox', {})
            }
            
            if ref_node_id in mappings:
                mapped_ref['figure_id'] = str(mappings[ref_node_id])
                mapped_ref['not_matched'] = False
                
                # 참조 타입 정보 추가
                node_data = self.graph.nodes[ref_node_id]
                mapped_ref['reference_type'] = node_data.get('ref_type', ReferenceType.UNKNOWN).value
            else:
                mapped_ref['not_matched'] = True
            
            mapped_references.append(mapped_ref)
        
        return mapped_references
    
    def _build_graph(self, references: List[Dict[str, Any]], figures: List[Dict[str, Any]]):
        """Build document graph with references and figures"""
        # 피규어 노드 추가
        for figure in figures:
            fig_id = str(figure.get('figure_id', ''))
            if not fig_id:
                continue
            
            # 피규어 타입 추출
            fig_type = self._get_figure_type(figure)
            
            self.graph.add_node(
                fig_id,
                type='figure',
                fig_type=fig_type,
                data=figure,
                page_idx=int(figure.get('page_idx', 0)),
                bbox=figure.get('bbox', {}),
                text=str(figure.get('text', ''))
            )
        
        # 참조 노드 추가
        for i, reference in enumerate(references):
            ref_node_id = f"ref_{i}"
            ref_text = str(reference.get('text', ''))
            
            # 참조 타입과 ID 추출
            ref_type, ref_id = self._extract_typed_id_from_reference(ref_text)
            
            self.graph.add_node(
                ref_node_id,
                type='reference',
                ref_type=ref_type,
                ref_id=ref_id,
                data=reference,
                text=ref_text,
                bbox=reference.get('bbox', {}),
                page_idx=int(reference.get('page_idx', 0))
            )
            
            # ID 기반 매칭 (타입이 일치하는 경우만)
            if ref_id and ref_type != ReferenceType.UNKNOWN:
                for fig_node in self.graph.nodes():
                    if self.graph.nodes[fig_node].get('type') == 'figure':
                        fig_data = self.graph.nodes[fig_node]
                        fig_type = fig_data.get('fig_type')
                        
                        # 타입이 일치하는 경우만 매칭 시도
                        if self._is_type_compatible(ref_type, fig_type):
                            if self._is_id_match(ref_id, fig_data['data']):
                                self.graph.add_edge(
                                    ref_node_id, 
                                    fig_node,
                                    weight=0.9,  # 타입이 일치하면 더 높은 가중치
                                    relation='typed_id_match'
                                )
        
        # 공간적 관계 추가
        self._add_spatial_relationships()
        
        # 의미론적 관계 추가 (타입을 고려)
        self._add_semantic_relationships()
    
    def _get_figure_type(self, figure: Dict[str, Any]) -> ReferenceType:
        """피규어의 타입을 결정"""
        fig_type = str(figure.get('type', '')).lower()
        fig_text = str(figure.get('text', '')).lower()
        
        # 레이아웃 타입에서 추출
        if 'table' in fig_type:
            return ReferenceType.TABLE
        elif 'formula' in fig_type or 'equation' in fig_type:
            return ReferenceType.EQUATION
        elif 'algorithm' in fig_type:
            return ReferenceType.ALGORITHM
        elif 'figure' in fig_type or 'image' in fig_type:
            return ReferenceType.FIGURE
        
        # 텍스트에서 추출
        if any(keyword in fig_text for keyword in ['table', '표']):
            return ReferenceType.TABLE
        elif any(keyword in fig_text for keyword in ['equation', 'eq.', '식']):
            return ReferenceType.EQUATION
        elif any(keyword in fig_text for keyword in ['example', 'ex.', '예제']):
            return ReferenceType.EXAMPLE
        elif any(keyword in fig_text for keyword in ['algorithm', 'alg.', '알고리즘']):
            return ReferenceType.ALGORITHM
        elif any(keyword in fig_text for keyword in ['figure', 'fig.', '그림']):
            return ReferenceType.FIGURE
        
        return ReferenceType.FIGURE  # 기본값
    
    def _extract_typed_id_from_reference(self, ref_text: str) -> Tuple[ReferenceType, Optional[str]]:
        """참조 텍스트에서 타입과 ID를 함께 추출"""
        if not ref_text:
            return ReferenceType.UNKNOWN, None
        
        ref_lower = ref_text.lower()
        
        # 각 타입별로 패턴 매칭 시도
        for ref_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(ref_lower)
                if match:
                    return ref_type, match.group(1)
        
        return ReferenceType.UNKNOWN, None
    
    def _is_type_compatible(self, ref_type: ReferenceType, fig_type: ReferenceType) -> bool:
        """참조 타입과 피규어 타입이 호환되는지 확인"""
        # 정확히 일치
        if ref_type == fig_type:
            return True
        
        # 일부 호환 가능한 경우
        # 예: EQUATION 참조는 FORMULA 피규어와 매칭 가능
        compatible_types = {
            ReferenceType.EQUATION: [ReferenceType.EQUATION],
            ReferenceType.FIGURE: [ReferenceType.FIGURE],
            ReferenceType.TABLE: [ReferenceType.TABLE],
            ReferenceType.EXAMPLE: [ReferenceType.EXAMPLE, ReferenceType.FIGURE],  # 예제는 피규어일 수도 있음
            ReferenceType.ALGORITHM: [ReferenceType.ALGORITHM, ReferenceType.FIGURE],
        }
        
        return fig_type in compatible_types.get(ref_type, [])
    
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
    
    def _add_spatial_relationships(self):
        """Add spatial relationships between nodes"""
        ref_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'reference']
        fig_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'figure']
        
        for ref_node in ref_nodes:
            ref_data = self.graph.nodes[ref_node]
            ref_page = int(ref_data.get('page_idx', 0))
            ref_bbox = ref_data.get('bbox', {})
            ref_type = ref_data.get('ref_type', ReferenceType.UNKNOWN)
            
            for fig_node in fig_nodes:
                fig_data = self.graph.nodes[fig_node]
                fig_page = int(fig_data.get('page_idx', 0))
                fig_bbox = fig_data.get('bbox', {})
                fig_type = fig_data.get('fig_type', ReferenceType.UNKNOWN)
                
                # 타입이 호환되지 않으면 스킵
                if not self._is_type_compatible(ref_type, fig_type):
                    continue
                
                # 같은 페이지 관계
                if ref_page == fig_page:
                    distance = self._calculate_distance(ref_bbox, fig_bbox)
                    if distance < 500:
                        weight = max(0.0, 1.0 - (distance / 500)) * 0.4
                        self.graph.add_edge(
                            ref_node,
                            fig_node,
                            weight=weight,
                            relation='same_page_typed',
                            distance=distance
                        )
                
                # 인접 페이지 관계
                elif abs(ref_page - fig_page) == 1:
                    if ref_page > fig_page:
                        self.graph.add_edge(
                            ref_node,
                            fig_node,
                            weight=0.2,
                            relation='next_page_typed'
                        )
    
    def _add_semantic_relationships(self):
        """Add semantic relationships based on text similarity"""
        ref_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'reference']
        fig_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'figure']
        
        for ref_node in ref_nodes:
            ref_data = self.graph.nodes[ref_node]
            ref_text = str(ref_data.get('text', '')).lower()
            ref_type = ref_data.get('ref_type', ReferenceType.UNKNOWN)
            
            for fig_node in fig_nodes:
                fig_data = self.graph.nodes[fig_node]
                fig_text = str(fig_data.get('text', '')).lower()
                fig_type = fig_data.get('fig_type', ReferenceType.UNKNOWN)
                
                # 타입이 호환되지 않으면 스킵
                if not self._is_type_compatible(ref_type, fig_type):
                    continue
                
                # 텍스트 유사도 계산
                similarity = self._calculate_text_similarity(ref_text, fig_text)
                if similarity > 0.2:
                    self.graph.add_edge(
                        ref_node,
                        fig_node,
                        weight=similarity * 0.3,
                        relation='semantic_typed'
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
    
    def _calculate_distance(self, bbox1: Dict[str, int], bbox2: Dict[str, int]) -> float:
        """Calculate distance between two bounding boxes"""
        if not bbox1 or not bbox2:
            return float('inf')
        
        try:
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
            words1 = set(str(text1).split())
            words2 = set(str(text2).split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1 & words2
            union = words1 | words2
            
            return len(intersection) / len(union) if union else 0.0
        except Exception:
            return 0.0
    
    def _create_unmapped_references(self, references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create unmapped references when no figures are available"""
        unmapped = []
        for ref in references:
            ref_text = str(ref.get('text', ''))
            ref_type, ref_id = self._extract_typed_id_from_reference(ref_text)
            
            unmapped.append({
                'text': ref_text,
                'bbox': ref.get('bbox', {}),
                'not_matched': True,
                'reference_type': ref_type.value
            })
        
        return unmapped
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the constructed graph"""
        try:
            # 타입별 참조 수 계산
            ref_type_counts = {}
            fig_type_counts = {}
            
            for node, data in self.graph.nodes(data=True):
                if data['type'] == 'reference':
                    ref_type = data.get('ref_type', ReferenceType.UNKNOWN)
                    ref_type_counts[ref_type.value] = ref_type_counts.get(ref_type.value, 0) + 1
                elif data['type'] == 'figure':
                    fig_type = data.get('fig_type', ReferenceType.UNKNOWN)
                    fig_type_counts[fig_type.value] = fig_type_counts.get(fig_type.value, 0) + 1
            
            return {
                'num_nodes': self.graph.number_of_nodes(),
                'num_edges': self.graph.number_of_edges(),
                'num_references': len([n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'reference']),
                'num_figures': len([n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'figure']),
                'reference_types': ref_type_counts,
                'figure_types': fig_type_counts,
                'avg_degree': float(np.mean([d for n, d in self.graph.degree()])) if self.graph.number_of_nodes() > 0 else 0.0
            }
        except Exception as e:
            print(f"Error calculating graph statistics: {e}")
            return {}


# 테스트용 예제
if __name__ == "__main__":
    mapper = FigureMapper()
    
    # 테스트 참조들
    test_refs = [
        {'text': 'Fig. 2.31', 'bbox': {'x': 100, 'y': 100, 'width': 50, 'height': 20}},
        {'text': '(2.31)', 'bbox': {'x': 200, 'y': 100, 'width': 30, 'height': 20}},
        {'text': 'Ex. 2.31', 'bbox': {'x': 300, 'y': 100, 'width': 40, 'height': 20}},
        {'text': 'Table 2.31', 'bbox': {'x': 400, 'y': 100, 'width': 60, 'height': 20}},
    ]
    
    # 테스트 피규어들
    test_figs = [
        {'figure_id': '2.31', 'type': 'figure', 'text': 'Figure 2.31: Test figure', 'page_idx': 0},
        {'figure_id': '2.31', 'type': 'formula', 'text': 'Equation (2.31)', 'page_idx': 0},
        {'figure_id': '2.31', 'type': 'example', 'text': 'Example 2.31', 'page_idx': 0},
        {'figure_id': '2.31', 'type': 'table', 'text': 'Table 2.31: Test table', 'page_idx': 0},
    ]
    
    # 매핑 수행
    results = mapper.map_references_to_figures(test_refs, test_figs)
    
    # 결과 출력
    for i, result in enumerate(results):
        print(f"Reference: {test_refs[i]['text']}")
        print(f"  Type: {result.get('reference_type', 'unknown')}")
        print(f"  Matched: {not result.get('not_matched', True)}")
        if not result.get('not_matched', True):
            print(f"  Figure ID: {result.get('figure_id', '')}")
        print()