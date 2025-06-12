# 주요기능은 다음과 같습니다.
OCR 과 레이아웃 분석을 이용해 피규어와 레퍼런스를 맵핑

# 주요 사용자 시나리오는 다음과 같습니다.
1. 사용자가 PDF 파일을 /api/v1/analyze 엔드포인트로 업로드(POST, multipart/form-data)
2. 각 페이지별 이미지 변환 및 OCR 수행 및 레이아웃 분석
3. 레이아웃 타입이 피규어와 관련된 것에 해당하는 경우 해당 바운딩 박스 혹은 주변에서 피규어 타이틀을 찾음 (예를들어 ‘Figure 2.6: Document’) 해당 피규어 타이틀을 이용하여 피규어 아이디 생성 (피규어 아이디, 피규어 타입, 바운딩박스, 피규어타이틀, 피규어가 속한 페이지 인덱스)
4. (2)에서 추출한 텍스트에서 참조 부분을 추출,‘Fig.2.6’, ‘Example 2.4’, ‘(1.4)’와 같이) 텍스트를 추출. (텍스트, 바운딩 박스)
5. (4)에서 추출한 참조를 (3)번에서 생성한 피규어와 맵핑
6. 결과 반환

# 코드 요구사항

**구현 시스템 환경**
- 윈도우 11
- Nvidia RTX 3090 cuda 12.9
- Ram 64 GB
- Rygen8 5700x 8 core
- Python 3.10 사용 (Anaconda)

1. 결과는 다음 json 형식으로 반환해야합니다.
```
Reference { // 텍스트중 피규어를 가리키는 문구
    bbox // 해당 문구에 대한 좌표, 크기
    text
    figure_id: // 해당 문구가 가리키는 피규어 아이디
}

Figure {
    bbox // 피규어가 있는 좌표, 크기
    page_idx: // 피규어가 있는 페이지 인덱스
    figure_id // 피규어 아이디
    type
}

TextBlock { // 텍스트 타입에 해당하는 레이아웃
    text    
    bbox
}

Page {
    index // page index
    page_size // page rect size (width, height) 
    blocks: [TextBlock] 
    references: [Annotation]
}

Pdf { // result
    metadata // pdf meta data
    pages: [Page]
    figures: [Figure]
}
```
2. Flask를 이용하여 백엔드 서버를 구축하여, Swagger를 이용하여 문서화해야합니다.
3. 기능별 모듈화를 통해 코드를 간결하게 유지해야합니다.
4. 레이아웃 분석, OCR, 텍스트 분류에는 다음 모델을 사용해야합니다.
hugginface에 있는 모델로 transforms 라이브러리를 통해 동작해야합니다. (라이브러리 문서를 읽고 반드시 라이브러리 가이드에 맞춰 사용할 것, 버전확인)
OCR: PaddleOCR (https://github.com/PaddlePaddle/PaddleOCR)
레이아웃분석: PaddleOCR 사용 (https://github.com/PaddlePaddle/PaddleOCR)
텍스트 분류(피규어 참조 분류): https://huggingface.co/microsoft/layoutlmv2-base-uncased
5. 파일 업로드 용량 제한(예: 50MB)
6. 예외/에러 처리 및 Swagger에 명시
7. 반환 JSON 구조, 각 필드 설명 Swagger에 명시
8. 보안: 업로드 파일 확장자/용량 제한, 임시파일 삭제 등
9. 코드 내 TODO, 미완성 부분 없이 완전 구현
10. host, port, model등 상수부분은 config로 별도 분리하여 나중에 사용자가 설정할 수 있도록 할 것.
11. 사용하는 파이썬 라이브러리마다 필요 버전조사후 conflict발생하지 않도록 버전 설정
12. api관련은 모두 app 폴더내에 위치시킬 것
13. 라이브러리 사용시 반드시 해당 라이브러리 공식 문서를 확인할 것