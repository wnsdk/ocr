# PDF OCR 처리 스크립트

PDF 파일을 Tesseract OCR로 처리하여 **검색 가능한 PDF**와 **텍스트 파일**을 생성합니다.

## 폴더 구조

```
원본/           ← 원본 PDF
산출물/
├── pdf/       ← OCR Searchable PDF
└── txt/       ← OCR 텍스트 파일
ocr_pdf.py     ← OCR 스크립트
```

## 사전 설치

```bash
brew install tesseract tesseract-lang poppler
pip3 install pytesseract pdf2image pillow
```

## 사용법

```bash
python3 ocr_pdf.py "파일명.pdf"
python3 ocr_pdf.py "파일명.pdf" --dpi 200
python3 ocr_pdf.py "파일명.pdf" --lang eng
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--dpi` | 150 | 이미지 변환 해상도 |
| `--lang` | kor+eng | OCR 언어 |

## 처리 방식

1. PDF → 이미지 변환 (1장씩, 파일로 저장)
2. 이미지 → TXT 추출 + Searchable PDF 생성
3. PDF 합치기 → 임시 파일 정리

- 중간에 중단되어도 이어서 처리 가능 (resume 지원)
- 작업 디렉토리: `.ocr_work/<파일명>/`
