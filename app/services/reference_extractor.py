# app/services/reference_extractor.py - 타입 정보를 포함하는 버전
import re
from typing import List, Dict, Any, Tuple

class ReferenceExtractor:
    def __init__(self):
        """Initialize reference extractor with type-aware patterns"""
        # 타입별 참조 패턴 정의
        self.typed_patterns = {
            'figure': [
                (r'\bFig\.?\s*\d+(?:\.\d+)*\b', 'Fig'),
                (r'\bFigure\.?\s*\d+(?:\.\d+)*\b', 'Figure'),
                (r'\bFIG\.?\s*\d+(?:\.\d+)*\b', 'FIG'),
                (r'\b그림\.?\s*\d+(?:\.\d+)*\b', '그림'),
            ],
            'table': [
                (r'\bTable\.?\s*\d+(?:\.\d+)*\b', 'Table'),
                (r'\bTab\.?\s*\d+(?:\.\d+)*\b', 'Tab'),
                (r'\b표\.?\s*\d+(?:\.\d+)*\b', '표'),
            ],
            'equation': [
                (r'\bEq\.?\s*\(\d+(?:\.\d+)*\)', 'Eq'),
                (r'\bEquation\.?\s*\(\d+(?:\.\d+)*\)', 'Equation'),
                (r'\bEq\.?\s*\d+(?:\.\d+)*\b', 'Eq'),
                (r'\bEquation\.?\s*\d+(?:\.\d+)*\b', 'Equation'),
                (r'(?<!\w)\(\d+(?:\.\d+)*\)(?=\s|$|[,.])', 'parentheses'),  # 단독 괄호
                (r'\b식\.?\s*\(\d+(?:\.\d+)*\)', '식'),
                (r'\b수식\.?\s*\d+(?:\.\d+)*\b', '수식'),
            ],
            'example': [
                (r'\bExample\.?\s*\d+(?:\.\d+)*\b', 'Example'),
                (r'\bEx\.?\s*\d+(?:\.\d+)*\b', 'Ex'),
                (r'\b예제\.?\s*\d+(?:\.\d+)*\b', '예제'),
                (r'\b예\.?\s*\d+(?:\.\d+)*\b', '예'),
            ],
            'algorithm': [
                (r'\bAlgorithm\.?\s*\d+(?:\.\d+)*\b', 'Algorithm'),
                (r'\bAlg\.?\s*\d+(?:\.\d+)*\b', 'Alg'),
                (r'\b알고리즘\.?\s*\d+(?:\.\d+)*\b', '알고리즘'),
            ],
            'combined': [
                (r'\bFigs?\.?\s*\d+(?:\.\d+)*(?:\s*(?:and|&|-|,)\s*\d+(?:\.\d+)*)*\b', 'Figs'),
                (r'\bTables?\.?\s*\d+(?:\.\d+)*(?:\s*(?:and|&|-|,)\s*\d+(?:\.\d+)*)*\b', 'Tables'),
            ]
        }
        
        # 모든 패턴을 하나로 합치되, 타입 정보를 보존
        self.all_patterns = []
        for ref_type, patterns in self.typed_patterns.items():
            for pattern, prefix in patterns:
                compiled = re.compile(pattern, re.IGNORECASE)
                self.all_patterns.append((compiled, ref_type, prefix))
    
    def extract_references(self, text_blocks: List[Dict[str, Any]], page_idx: int = None) -> List[Dict[str, Any]]:
        """Extract references with type information from text blocks"""
        references = []
        
        if not text_blocks or not isinstance(text_blocks, list):
            return references
        
        for block in text_blocks:
            if not isinstance(block, dict):
                continue
                
            text = block.get('text', '')
            bbox = block.get('bbox', {})
            
            # 타입 안전성 보장
            text_str = str(text) if text is not None else ''
            
            if not text_str:
                continue
            
            # bbox 검증 및 기본값 설정
            if not isinstance(bbox, dict):
                bbox = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
            
            # Find all references with types in this text block
            try:
                # 모든 매치를 찾고 위치별로 정렬
                all_matches = []
                
                for pattern, ref_type, prefix in self.all_patterns:
                    for match in pattern.finditer(text_str):
                        all_matches.append({
                            'match': match,
                            'ref_type': ref_type,
                            'prefix': prefix
                        })
                
                # 위치별로 정렬 (겹치는 매치 제거)
                all_matches.sort(key=lambda x: x['match'].start())
                
                # 겹치지 않는 매치만 선택
                selected_matches = []
                last_end = -1
                
                for match_info in all_matches:
                    match = match_info['match']
                    if match.start() >= last_end:
                        selected_matches.append(match_info)
                        last_end = match.end()
                
                # 선택된 매치로 참조 생성
                for match_info in selected_matches:
                    match = match_info['match']
                    ref_text = match.group(0)
                    start_pos = match.start()
                    end_pos = match.end()
                    
                    # Estimate bounding box for the reference
                    ref_bbox = self._estimate_ref_bbox(bbox, text_str, start_pos, end_pos)
                    
                    # Add reference with type and page info
                    reference = {
                        'text': ref_text,
                        'bbox': ref_bbox,
                        'reference_type': match_info['ref_type']
                    }
                    
                    # Add page_idx if provided
                    if page_idx is not None:
                        try:
                            reference['page_idx'] = int(page_idx)
                        except (ValueError, TypeError):
                            reference['page_idx'] = 0
                    
                    references.append(reference)
                    
            except Exception as e:
                print(f"Error processing text block: {e}")
                continue
        
        return references
    
    def _estimate_ref_bbox(self, text_bbox: Dict[str, int], full_text: str, start_pos: int, end_pos: int) -> Dict[str, int]:
        """Estimate bounding box for reference within text block"""
        # 기본값 설정
        default_bbox = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        
        if not text_bbox or not isinstance(text_bbox, dict) or not full_text:
            return default_bbox
        
        # 타입 안전성을 위한 값 추출
        try:
            text_x = int(text_bbox.get('x', 0))
            text_y = int(text_bbox.get('y', 0))
            text_width = int(text_bbox.get('width', 0))
            text_height = int(text_bbox.get('height', 0))
        except (ValueError, TypeError):
            return default_bbox
        
        # Simple estimation based on character position
        text_length = len(full_text)
        if text_length == 0:
            return {
                'x': text_x,
                'y': text_y,
                'width': text_width,
                'height': text_height
            }
        
        # Estimate horizontal position (assuming horizontal text)
        try:
            char_width = text_width / text_length
            ref_x = text_x + int(start_pos * char_width)
            ref_width = int((end_pos - start_pos) * char_width)
            
            # 음수값 방지
            ref_x = max(0, ref_x)
            ref_width = max(1, ref_width)
            
            return {
                'x': ref_x,
                'y': text_y,
                'width': ref_width,
                'height': text_height
            }
        except (ValueError, TypeError, ZeroDivisionError):
            return default_bbox
    
    def get_reference_statistics(self, references: List[Dict[str, Any]]) -> Dict[str, int]:
        """참조 타입별 통계 반환"""
        stats = {}
        for ref in references:
            ref_type = ref.get('reference_type', 'unknown')
            stats[ref_type] = stats.get(ref_type, 0) + 1
        return stats


# 테스트 예제
if __name__ == "__main__":
    extractor = ReferenceExtractor()
    
    # 테스트 텍스트 블록
    test_blocks = [
        {
            'text': 'As shown in Fig. 2.31, the results are significant. Equation (2.31) describes the relationship.',
            'bbox': {'x': 100, 'y': 100, 'width': 500, 'height': 50}
        },
        {
            'text': 'Example 2.31 demonstrates this concept. See also Table 2.31 for numerical values.',
            'bbox': {'x': 100, 'y': 200, 'width': 500, 'height': 50}
        },
        {
            'text': 'The formula (2.31) is derived from Algorithm 2.31.',
            'bbox': {'x': 100, 'y': 300, 'width': 500, 'height': 50}
        }
    ]
    
    # 참조 추출
    references = extractor.extract_references(test_blocks, page_idx=0)
    
    # 결과 출력
    print("Extracted references:")
    for ref in references:
        print(f"  Text: {ref['text']}")
        print(f"  Type: {ref['reference_type']}")
        print(f"  BBox: {ref['bbox']}")
        print()
    
    # 통계 출력
    stats = extractor.get_reference_statistics(references)
    print(f"Statistics: {stats}")