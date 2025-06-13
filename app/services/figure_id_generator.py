# app/services/figure_id_generator.py - 타입 정보를 포함하는 버전
import re
from typing import Dict, Any, Optional, Tuple

class FigureIDGenerator:
    def __init__(self):
        """Initialize figure ID generator with type awareness"""
        # 타입별 ID 추출 패턴
        self.typed_id_patterns = {
            'figure': [
                (r'fig(?:ure)?\.?\s*(\d+(?:\.\d+)*)', 'figure'),
                (r'그림\.?\s*(\d+(?:\.\d+)*)', 'figure'),
            ],
            'table': [
                (r'tab(?:le)?\.?\s*(\d+(?:\.\d+)*)', 'table'),
                (r'표\.?\s*(\d+(?:\.\d+)*)', 'table'),
            ],
            'equation': [
                (r'eq(?:uation)?\.?\s*\((\d+(?:\.\d+)*)\)', 'equation'),
                (r'eq(?:uation)?\.?\s*(\d+(?:\.\d+)*)', 'equation'),
                (r'식\.?\s*\((\d+(?:\.\d+)*)\)', 'equation'),
                (r'수식\.?\s*(\d+(?:\.\d+)*)', 'equation'),
            ],
            'formula': [
                (r'formula\.?\s*(\d+(?:\.\d+)*)', 'equation'),  # formula는 equation으로 매핑
                (r'\((\d+(?:\.\d+)*)\)', 'equation'),
            ],
            'example': [
                (r'ex(?:ample)?\.?\s*(\d+(?:\.\d+)*)', 'example'),
                (r'예제\.?\s*(\d+(?:\.\d+)*)', 'example'),
            ],
            'algorithm': [
                (r'alg(?:orithm)?\.?\s*(\d+(?:\.\d+)*)', 'algorithm'),
                (r'알고리즘\.?\s*(\d+(?:\.\d+)*)', 'algorithm'),
            ],
            'chart': [
                (r'chart\.?\s*(\d+(?:\.\d+)*)', 'figure'),
                (r'graph\.?\s*(\d+(?:\.\d+)*)', 'figure'),
                (r'diagram\.?\s*(\d+(?:\.\d+)*)', 'figure'),
            ],
            'image': [
                (r'image\.?\s*(\d+(?:\.\d+)*)', 'figure'),
                (r'picture\.?\s*(\d+(?:\.\d+)*)', 'figure'),
            ]
        }
        
        # 컴파일된 패턴 저장
        self.compiled_patterns = []
        for patterns in self.typed_id_patterns.values():
            for pattern, mapped_type in patterns:
                self.compiled_patterns.append((re.compile(pattern, re.IGNORECASE), mapped_type))
        
        # 레이아웃 타입과 참조 타입의 매핑
        self.layout_type_mapping = {
            'figure': 'figure',
            'figure_title': 'figure',
            'figure_caption': 'figure',
            'image': 'figure',
            'table': 'table',
            'table_caption': 'table',
            'formula': 'equation',
            'number': 'equation',  # 수식 번호
            'algorithm': 'algorithm',
            'chart': 'figure',
            'graph': 'figure',
            'diagram': 'figure',
        }
    
    def generate_figure_info(self, layout_block: Dict[str, Any], page_idx: int) -> Dict[str, Any]:
        """Generate figure information including ID, type, and position"""
        # 타입 안전성을 위해 모든 값을 적절히 변환
        layout_type = str(layout_block.get('type', 'figure'))
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
        
        # 레이아웃 타입에서 참조 타입 결정
        ref_type = self._determine_reference_type(layout_type, text)
        
        # 텍스트에서 ID와 타입 추출 시도
        figure_id, extracted_type = self._extract_typed_figure_id(text)
        
        # 추출된 타입이 있으면 우선 사용
        if extracted_type:
            ref_type = extracted_type
        
        # ID가 없으면 생성
        if not figure_id:
            figure_id = self._generate_fallback_id(ref_type, page_idx, safe_bbox)
        
        # confidence 값의 타입 안전성 보장
        confidence = layout_block.get('confidence', 0.0)
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            confidence = 0.0
        
        return {
            'figure_id': figure_id,
            'type': layout_type,  # 원본 레이아웃 타입 유지
            'reference_type': ref_type,  # 참조 매칭용 타입
            'bbox': safe_bbox,
            'page_idx': int(page_idx),
            'text': text,
            'confidence': confidence
        }
    
    def _determine_reference_type(self, layout_type: str, text: str) -> str:
        """레이아웃 타입과 텍스트를 기반으로 참조 타입 결정"""
        # 레이아웃 타입 매핑 확인
        layout_lower = layout_type.lower()
        if layout_lower in self.layout_type_mapping:
            return self.layout_type_mapping[layout_lower]
        
        # 텍스트에서 타입 힌트 찾기
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in ['fig', 'figure', '그림']):
            return 'figure'
        elif any(keyword in text_lower for keyword in ['table', 'tab', '표']):
            return 'table'
        elif any(keyword in text_lower for keyword in ['eq', 'equation', 'formula', '식', '수식']):
            return 'equation'
        elif any(keyword in text_lower for keyword in ['example', 'ex.', '예제']):
            return 'example'
        elif any(keyword in text_lower for keyword in ['algorithm', 'alg', '알고리즘']):
            return 'algorithm'
        
        # 기본값
        return 'figure'
    
    def _extract_typed_figure_id(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """텍스트에서 ID와 타입을 함께 추출"""
        if not text or not isinstance(text, str):
            return None, None
        
        # 각 패턴 시도
        for pattern, ref_type in self.compiled_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1), ref_type
        
        return None, None
    
    def _generate_fallback_id(self, ref_type: str, page_idx: int, bbox: Dict[str, int]) -> str:
        """타입을 포함한 fallback ID 생성"""
        # Use page index and vertical position to create unique ID
        try:
            y_position = int(bbox.get('y', 0))
            page_num = int(page_idx)
        except (ValueError, TypeError):
            y_position = 0
            page_num = 0
        
        # Create ID format with type prefix: type_page_yposition
        # 예: "fig_0_150", "eq_1_200", "tab_2_300"
        type_prefix = {
            'figure': 'fig',
            'table': 'tab',
            'equation': 'eq',
            'example': 'ex',
            'algorithm': 'alg',
        }.get(ref_type, 'unk')
        
        return f"{type_prefix}_{page_num}_{y_position}"


# 테스트 예제
if __name__ == "__main__":
    generator = FigureIDGenerator()
    
    # 테스트 레이아웃 블록들
    test_blocks = [
        {
            'type': 'figure',
            'text': 'Figure 2.31: Sample figure',
            'bbox': {'x': 100, 'y': 200, 'width': 300, 'height': 400},
            'confidence': 0.95
        },
        {
            'type': 'formula',
            'text': 'y = mx + b (2.31)',
            'bbox': {'x': 100, 'y': 300, 'width': 200, 'height': 50},
            'confidence': 0.90
        },
        {
            'type': 'table',
            'text': 'Table 2.31: Results',
            'bbox': {'x': 100, 'y': 400, 'width': 400, 'height': 300},
            'confidence': 0.92
        },
        {
            'type': 'figure_caption',
            'text': 'Example 2.31: Code snippet',
            'bbox': {'x': 100, 'y': 500, 'width': 300, 'height': 30},
            'confidence': 0.88
        },
        {
            'type': 'image',
            'text': '',  # 텍스트 없는 이미지
            'bbox': {'x': 100, 'y': 600, 'width': 300, 'height': 200},
            'confidence': 0.85
        }
    ]
    
    # 피규어 정보 생성
    for i, block in enumerate(test_blocks):
        info = generator.generate_figure_info(block, page_idx=0)
        print(f"\nBlock {i+1}:")
        print(f"  Layout Type: {block['type']}")
        print(f"  Generated Info:")
        print(f"    Figure ID: {info['figure_id']}")
        print(f"    Reference Type: {info['reference_type']}")
        print(f"    Original Type: {info['type']}")