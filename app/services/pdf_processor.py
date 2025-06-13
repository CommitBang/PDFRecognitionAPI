# app/services/pdf_processor.py - 개선된 FigureGrouper를 사용하는 버전
import fitz
import os
import io
from PIL import Image
from typing import List, Dict, Any
from paddleocr import PPStructureV3
import tempfile
import shutil
from app.services.layout_detector import LayoutDetector
from app.services.figure_grouper import FigureGrouper  # 개선된 FigureGrouper import
from app.services.figure_id_generator import FigureIDGenerator
from app.services.reference_extractor import ReferenceExtractor
from app.services.figure_mapper import FigureMapper

_pp_structure_instance = None

def get_pp_structure_instance(use_gpu: bool = True):
    """Get or create global PP-Structure instance"""
    global _pp_structure_instance
    if _pp_structure_instance is None:
        # Check if models are already cached
        cache_dir = os.path.expanduser("~/.paddlex/official_models")
        if os.path.exists(cache_dir):
            print(f"Models cache found at: {cache_dir}")
            model_files = os.listdir(cache_dir)
            print(f"Cached models: {len(model_files)} files")
        else:
            print("No model cache found - models will be downloaded")
        
        print("Initializing PP-StructureV3 with lightweight models...")
        
        # Balanced configuration
        config_balanced = {
            'use_doc_orientation_classify': False,
            'use_doc_unwarping': False,
            'use_textline_orientation': False,
            'use_seal_recognition': False,
            'use_chart_recognition': False,
            'use_table_recognition': False,
            'use_formula_recognition': False,
            
            'device': 'gpu' if use_gpu else 'cpu',
        }
        
        _pp_structure_instance = PPStructureV3(**config_balanced)
        print("PP-StructureV3 models loaded successfully!")
    else:
        print("Using cached PP-StructureV3 instance")
    return _pp_structure_instance

class PDFProcessor:
    def __init__(self, dpi: int = 150, use_gpu: bool = True, lang: str = 'en'):
        self.dpi = dpi
        # Use global PP-Structure instance to avoid reloading models
        self.pp_structure = get_pp_structure_instance(use_gpu)
        
        # Initialize services
        self.layout_detector = LayoutDetector(self.pp_structure)
        self.figure_grouper = FigureGrouper()  # 개선된 FigureGrouper 사용
        self.figure_id_generator = FigureIDGenerator()
        self.reference_extractor = ReferenceExtractor()
        self.figure_mapper = FigureMapper()
    
    def extract_pdf_data(self, pdf_path: str) -> tuple[Dict[str, Any], List[Image.Image]]:
        """Extract metadata and convert PDF to images in single operation"""
        try:
            doc = fitz.open(pdf_path)
            
            # Extract metadata
            metadata = doc.metadata
            page_count = doc.page_count
            
            # 타입 안전성을 위한 메타데이터 처리
            metadata_dict = {
                'title': str(metadata.get('title', '') or ''),
                'author': str(metadata.get('author', '') or ''),
                'subject': str(metadata.get('subject', '') or ''),
                'creator': str(metadata.get('creator', '') or ''),
                'producer': str(metadata.get('producer', '') or ''),
                'creation_date': str(metadata.get('creationDate', '') or ''),
                'modification_date': str(metadata.get('modDate', '') or ''),
                'pages': int(page_count)
            }
            
            # Convert to images
            images = []
            # Calculate zoom factor from DPI
            zoom = self.dpi / 72.0  # 72 DPI is default
            mat = fitz.Matrix(zoom, zoom)
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                images.append(img)
                pix = None  # Free memory
            
            doc.close()
            return metadata_dict, images
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return {}, []
    
    def save_temp_image(self, image: Image.Image, prefix: str = "page_") -> str:
        """Save PIL Image to temporary file and return path"""
        try:
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='.png', 
                prefix=prefix
            )
            image.save(temp_file.name, 'PNG')
            return temp_file.name
        except Exception as e:
            print(f"Error saving temporary image: {str(e)}")
            return ""
    
    def cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting temporary file {file_path}: {str(e)}")
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Main method to process PDF and return structured data"""
        try:
            # Extract metadata and convert to images in single operation
            metadata, images = self.extract_pdf_data(pdf_path)
            
            if not images:
                raise Exception("Failed to convert PDF to images")
            
            # Prepare result structure
            result = {
                'metadata': metadata,
                'pages': [],
                'figures': [],
                'temp_image_paths': [],
                'all_references': []  # 모든 참조를 모아서 그래프 매핑에 사용
            }
            
            # Process each page
            for page_idx, image in enumerate(images):
                try:
                    page_size = list(image.size)
                    temp_image_path = self.save_temp_image(image, f"page_{page_idx}_")
                    
                    if temp_image_path:
                        result['temp_image_paths'].append(temp_image_path)
                    
                    # Step 2: Detect layout and text from current page
                    detection_result = self.layout_detector.detect_layout_and_text(temp_image_path)
                    text_blocks = detection_result.get('text_blocks', [])
                    layout_blocks = detection_result.get('layout_blocks', [])
                    
                    # Step 3: Group related layout elements using improved FigureGrouper
                    print(f"Grouping {len(layout_blocks)} layout elements on page {page_idx}...")
                    grouped_figures = self.figure_grouper.group_figure_elements(layout_blocks, page_idx)
                    print(f"Created {len(grouped_figures)} grouped figures from {len(layout_blocks)} elements")
                    
                    # Step 3.5: Generate figure IDs and type information for grouped figures
                    for grouped_figure in grouped_figures:
                        try:
                            # 그룹핑된 figure에 대해 ID와 타입 정보 생성
                            # grouped_figure는 이미 figure_id와 type을 가지고 있지만, 
                            # figure_id_generator를 통해 reference_type 등 추가 정보 생성
                            figure_info = {
                                'figure_id': grouped_figure.get('figure_id'),
                                'type': grouped_figure.get('type'),
                                'bbox': grouped_figure.get('bbox'),
                                'page_idx': grouped_figure.get('page_idx'),
                                'text': grouped_figure.get('text', ''),
                                'confidence': grouped_figure.get('confidence', 0.0),
                                'elements': grouped_figure.get('elements', []),
                                'grouping_method': grouped_figure.get('grouping_method', 'unknown'),
                                'id_source': grouped_figure.get('id_source', 'unknown')
                            }
                            
                            # figure_id_generator를 사용하여 reference_type 추가
                            enhanced_info = self.figure_id_generator.generate_figure_info(
                                grouped_figure, 
                                page_idx
                            )
                            
                            # 기존 정보에 reference_type 추가
                            figure_info['reference_type'] = enhanced_info.get('reference_type', 'figure')
                            
                            result['figures'].append(figure_info)
                        except Exception as e:
                            print(f"Error generating figure info: {e}")
                            continue
                    
                    # Step 4: Extract references from text blocks with page info
                    references = self.reference_extractor.extract_references(text_blocks, page_idx)
                    
                    # 모든 참조를 수집 (나중에 그래프 매핑에 사용)
                    result['all_references'].extend(references)
                    
                    # Create page data
                    page_data = {
                        'index': page_idx,
                        'page_size': page_size,
                        'image_path': temp_image_path,
                        'blocks': text_blocks,
                        'references': references  # 페이지별 참조 (임시 저장)
                    }
                    
                    result['pages'].append(page_data)
                    
                except Exception as e:
                    print(f"Error processing page {page_idx}: {e}")
                    import traceback
                    traceback.print_exc()
                    # 에러가 발생한 페이지도 기본 구조로 추가
                    result['pages'].append({
                        'index': page_idx,
                        'page_size': [595, 842],  # 기본 크기
                        'blocks': [],
                        'references': []
                    })
                    continue
            
            # Step 5-7: 모든 페이지 처리 후 그래프 기반 매핑 수행
            print(f"Mapping {len(result['all_references'])} references to {len(result['figures'])} figures using graph-based approach...")
            
            try:
                # 이제 figure_mapper가 타입을 고려하여 매핑함
                all_mapped_references = self.figure_mapper.map_references_to_figures(
                    result['all_references'], 
                    result['figures']
                )
                
                # 그래프 통계 출력 (디버깅용)
                if hasattr(self.figure_mapper, 'get_graph_statistics'):
                    stats = self.figure_mapper.get_graph_statistics()
                    print(f"Graph statistics: {stats}")
                
                # 매핑된 참조를 각 페이지에 다시 할당
                ref_idx = 0
                for page_data in result['pages']:
                    num_refs = len(page_data.get('references', []))
                    if num_refs > 0 and ref_idx < len(all_mapped_references):
                        page_data['references'] = all_mapped_references[ref_idx:ref_idx + num_refs]
                        ref_idx += num_refs
                    else:
                        page_data['references'] = []
                
                # all_references는 최종 결과에서 제거
                del result['all_references']
                
                # 매핑 통계 추가
                total_refs = len(all_mapped_references)
                matched_count = sum(1 for ref in all_mapped_references if not ref.get('not_matched', True))
                unmatched_count = total_refs - matched_count
                match_rate = matched_count / total_refs if total_refs > 0 else 0.0
                
                result['mapping_statistics'] = {
                    'total_references': total_refs,
                    'matched_references': matched_count,
                    'unmatched_references': unmatched_count,
                    'match_rate': float(match_rate)
                }
                
                # 타입별 통계 추가
                result['type_statistics'] = self._calculate_type_statistics(
                    all_mapped_references, 
                    result['figures']
                )
                
                # 그룹핑 통계 추가
                result['grouping_statistics'] = self._calculate_grouping_statistics(result['figures'])
                
                print(f"Mapping complete: {matched_count}/{total_refs} references matched ({match_rate:.1%})")
                
                # 타입별 매칭률 출력
                if 'type_statistics' in result:
                    print("\nType-specific matching rates:")
                    for ref_type, stats in result['type_statistics'].get('matching_by_type', {}).items():
                        if stats['total'] > 0:
                            print(f"  {ref_type}: {stats['matched']}/{stats['total']} ({stats['rate']:.1%})")
                
                # 그룹핑 통계 출력
                if 'grouping_statistics' in result:
                    stats = result['grouping_statistics']
                    print(f"\nGrouping statistics:")
                    print(f"  Total figures: {stats['total_figures']}")
                    print(f"  Grouped figures: {stats['grouped_figures']}")
                    print(f"  Total elements: {stats['total_elements']}")
                    print(f"  Average elements per figure: {stats['avg_elements_per_figure']:.1f}")
                
            except Exception as e:
                print(f"Error in figure mapping: {e}")
                import traceback
                traceback.print_exc()
                # 매핑 실패 시 기본 참조 유지
                del result['all_references']
                result['mapping_statistics'] = {
                    'total_references': 0,
                    'matched_references': 0,
                    'unmatched_references': 0,
                    'match_rate': 0.0
                }
                result['type_statistics'] = {}
                result['grouping_statistics'] = {}
            
            return result
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    def _calculate_type_statistics(self, references: List[Dict[str, Any]], 
                                  figures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """타입별 통계 계산"""
        stats = {
            'figures_by_type': {},
            'references_by_type': {},
            'matching_by_type': {}
        }
        
        # 피규어 타입별 카운트
        for fig in figures:
            # reference_type이 있으면 사용, 없으면 type 사용
            ref_type = fig.get('reference_type', fig.get('type', 'unknown'))
            stats['figures_by_type'][ref_type] = stats['figures_by_type'].get(ref_type, 0) + 1
        
        # 참조 타입별 카운트 및 매칭률
        for ref in references:
            ref_type = ref.get('reference_type', 'unknown')
            stats['references_by_type'][ref_type] = stats['references_by_type'].get(ref_type, 0) + 1
            
            # 매칭 성공 여부
            if ref_type not in stats['matching_by_type']:
                stats['matching_by_type'][ref_type] = {'matched': 0, 'total': 0}
            
            stats['matching_by_type'][ref_type]['total'] += 1
            if not ref.get('not_matched', True):
                stats['matching_by_type'][ref_type]['matched'] += 1
        
        # 타입별 매칭률 계산
        for ref_type, counts in stats['matching_by_type'].items():
            if counts['total'] > 0:
                counts['rate'] = counts['matched'] / counts['total']
            else:
                counts['rate'] = 0.0
        
        return stats
    
    def _calculate_grouping_statistics(self, figures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """그룹핑 통계 계산"""
        stats = {
            'total_figures': len(figures),
            'grouped_figures': 0,
            'single_element_figures': 0,
            'total_elements': 0,
            'max_elements_in_figure': 0,
            'avg_elements_per_figure': 0.0,
            'grouping_methods': {}
        }
        
        element_counts = []
        
        for fig in figures:
            elements = fig.get('elements', [])
            element_count = len(elements)
            element_counts.append(element_count)
            
            stats['total_elements'] += element_count
            
            if element_count > 1:
                stats['grouped_figures'] += 1
            else:
                stats['single_element_figures'] += 1
            
            # 그룹핑 방법별 통계
            method = fig.get('grouping_method', 'unknown')
            stats['grouping_methods'][method] = stats['grouping_methods'].get(method, 0) + 1
        
        if element_counts:
            stats['max_elements_in_figure'] = max(element_counts)
            stats['avg_elements_per_figure'] = sum(element_counts) / len(element_counts)
        
        return stats


# 편의 함수들 추가
def print_type_statistics(result: Dict[str, Any]):
    """타입별 통계를 보기 좋게 출력"""
    if 'type_statistics' not in result:
        print("No type statistics available")
        return
    
    stats = result['type_statistics']
    
    print("\n=== Type Statistics ===")
    print("\nFigures by type:")
    for fig_type, count in sorted(stats.get('figures_by_type', {}).items()):
        print(f"  {fig_type:12s}: {count:3d}")
    
    print("\nReferences by type:")
    for ref_type, count in sorted(stats.get('references_by_type', {}).items()):
        print(f"  {ref_type:12s}: {count:3d}")
    
    print("\nMatching performance by type:")
    print(f"  {'Type':12s} {'Matched':>7s} {'Total':>7s} {'Rate':>7s}")
    print("  " + "-" * 36)
    for ref_type, data in sorted(stats.get('matching_by_type', {}).items()):
        print(f"  {ref_type:12s} {data['matched']:7d} {data['total']:7d} {data['rate']:6.1%}")


def print_grouping_statistics(result: Dict[str, Any]):
    """그룹핑 통계를 보기 좋게 출력"""
    if 'grouping_statistics' not in result:
        print("No grouping statistics available")
        return
    
    stats = result['grouping_statistics']
    
    print("\n=== Grouping Statistics ===")
    print(f"Total figures: {stats['total_figures']}")
    print(f"Grouped figures (>1 element): {stats['grouped_figures']}")
    print(f"Single element figures: {stats['single_element_figures']}")
    print(f"Total elements: {stats['total_elements']}")
    print(f"Average elements per figure: {stats['avg_elements_per_figure']:.2f}")
    print(f"Max elements in a figure: {stats['max_elements_in_figure']}")
    
    print("\nGrouping methods used:")
    for method, count in sorted(stats.get('grouping_methods', {}).items()):
        print(f"  {method}: {count}")


def get_unmatched_references_by_type(result: Dict[str, Any]) -> Dict[str, List[str]]:
    """타입별로 매칭되지 않은 참조들 반환"""
    unmatched = {}
    
    for page in result.get('pages', []):
        for ref in page.get('references', []):
            if ref.get('not_matched', False):
                ref_type = ref.get('reference_type', 'unknown')
                if ref_type not in unmatched:
                    unmatched[ref_type] = []
                unmatched[ref_type].append(ref['text'])
    
    return unmatched