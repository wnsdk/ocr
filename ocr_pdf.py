"""
PDF OCR 처리 스크립트
- 입력: PDF 파일
- 출력: OCR 텍스트 파일 (.txt) + 검색 가능한 OCR PDF (.pdf)
- 언어: 한글 + 영어

방식:
  1. PDF → 이미지 변환 (1장씩) → 작업 디렉토리에 저장
  2. 저장된 이미지로 TXT 추출 + PDF 페이지 생성 (이미지 1회만 변환)
  3. PDF 합치기
  4. 임시 파일 정리

특징:
  - 중간에 죽어도 이어서 처리 가능 (resume 지원)
  - 작업 디렉토리를 .ocr_work/<파일명>/ 에 유지
  - 완료 후 자동 정리

사용법:
  python3 ocr_pdf.py "파일명.pdf"
  python3 ocr_pdf.py "파일명.pdf" --dpi 200 --lang kor+eng
  python3 ocr_pdf.py "파일명.pdf" --dpi 300 --lang eng
"""

import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import os, subprocess, sys, gc, argparse

# Tesseract 경로 (Homebrew 설치 기준)
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
POPPLER_PATH = '/opt/homebrew/bin'


def get_total_pages(pdf_path):
    result = subprocess.run(
        [f'{POPPLER_PATH}/pdfinfo', pdf_path],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if line.startswith('Pages:'):
            return int(line.split(':')[1].strip())
    return 0


def ocr_pdf(pdf_path, dpi=150, lang='kor+eng'):
    if not os.path.exists(pdf_path):
        print(f"파일을 찾을 수 없습니다: {pdf_path}")
        sys.exit(1)

    base_name = os.path.splitext(pdf_path)[0]
    output_txt = f"{base_name}_ocr.txt"
    output_pdf = f"{base_name}_ocr.pdf"

    total_pages = get_total_pages(pdf_path)
    if total_pages == 0:
        print("페이지 수를 확인할 수 없습니다.")
        sys.exit(1)

    # 작업 디렉토리: .ocr_work/<파일명>/
    work_dir = os.path.join('.ocr_work', base_name)
    img_dir = os.path.join(work_dir, 'images')
    pdf_dir = os.path.join(work_dir, 'pdfs')
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)

    print(f"파일: {pdf_path}")
    print(f"총 {total_pages} 페이지 | DPI: {dpi} | 언어: {lang}")
    print(f"출력: {output_txt}, {output_pdf}")
    print(f"작업 디렉토리: {work_dir}\n")

    # ========================================
    # 1단계: PDF → 이미지 변환 (이미 있으면 건너뜀)
    # ========================================
    existing_imgs = set(os.listdir(img_dir))
    skip_img = sum(1 for p in range(1, total_pages + 1) if f"page_{p:04d}.png" in existing_imgs)

    if skip_img == total_pages:
        print(f"[1/3] 이미지 변환 — {total_pages}장 이미 완료, 건너뜀", flush=True)
    else:
        if skip_img > 0:
            print(f"[1/3] 이미지 변환 — {skip_img}장 완료됨, 이어서 변환...", flush=True)
        else:
            print("[1/3] PDF → 이미지 변환 중...", flush=True)

        for page_num in range(1, total_pages + 1):
            img_path = os.path.join(img_dir, f"page_{page_num:04d}.png")
            if os.path.exists(img_path):
                continue
            try:
                images = convert_from_path(
                    pdf_path, dpi=dpi, poppler_path=POPPLER_PATH,
                    first_page=page_num, last_page=page_num
                )
                images[0].save(img_path, 'PNG')
                del images
                gc.collect()
                print(f"  {page_num}/{total_pages}", flush=True)
            except Exception as e:
                print(f"  페이지 {page_num} 이미지 변환 에러: {e}", flush=True)

    # ========================================
    # 2단계: OCR (이미 있는 PDF 페이지는 건너뜀)
    # ========================================
    existing_pdfs = set(os.listdir(pdf_dir))
    skip_ocr = sum(1 for p in range(1, total_pages + 1) if f"ocr_{p:04d}.pdf" in existing_pdfs)

    if skip_ocr == total_pages:
        print(f"\n[2/3] OCR 처리 — {total_pages}장 이미 완료, 건너뜀", flush=True)
    else:
        if skip_ocr > 0:
            print(f"\n[2/3] OCR 처리 — {skip_ocr}장 완료됨, 이어서 처리...", flush=True)
        else:
            print("\n[2/3] OCR 처리 중 (TXT + PDF)...", flush=True)

        with open(output_txt, 'w', encoding='utf-8') as txt_f:
            for page_num in range(1, total_pages + 1):
                img_path = os.path.join(img_dir, f"page_{page_num:04d}.png")
                pdf_page_path = os.path.join(pdf_dir, f"ocr_{page_num:04d}.pdf")

                if not os.path.exists(img_path):
                    print(f"  페이지 {page_num} 이미지 없음, 건너뜀", flush=True)
                    continue

                try:
                    image = Image.open(img_path)

                    # TXT 추출 (항상 재생성 — 이어쓰기보다 전체 재생성이 정확)
                    text = pytesseract.image_to_string(image, lang=lang)
                    txt_f.write(f"=== 페이지 {page_num} ===\n{text}\n\n")
                    txt_f.flush()

                    # PDF 페이지 (이미 있으면 건너뜀)
                    if not os.path.exists(pdf_page_path):
                        pdf_data = pytesseract.image_to_pdf_or_hocr(image, lang=lang, extension='pdf')
                        with open(pdf_page_path, 'wb') as pf:
                            pf.write(pdf_data)
                        del pdf_data

                    del image
                    gc.collect()
                    print(f"  {page_num}/{total_pages}", flush=True)
                except Exception as e:
                    print(f"  페이지 {page_num} OCR 에러: {e}", flush=True)

    # ========================================
    # 3단계: PDF 합치기 + 정리
    # ========================================
    print("\n[3/3] PDF 합치는 중...", flush=True)
    all_pdfs = sorted([
        os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.endswith('.pdf')
    ])
    cmd = [f'{POPPLER_PATH}/pdfunite'] + all_pdfs + [output_pdf]
    subprocess.run(cmd, check=True)

    # 작업 디렉토리 정리
    import shutil
    shutil.rmtree(work_dir)

    txt_size = os.path.getsize(output_txt)
    pdf_size = os.path.getsize(output_pdf)
    print(f"\n완료!")
    print(f"TXT: {output_txt} ({txt_size:,} bytes)")
    print(f"PDF: {output_pdf} ({pdf_size / 1024 / 1024:.1f} MB)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PDF OCR 처리 (한글+영어)')
    parser.add_argument('pdf', help='입력 PDF 파일 경로')
    parser.add_argument('--dpi', type=int, default=150, help='이미지 변환 해상도 (기본: 150)')
    parser.add_argument('--lang', default='kor+eng', help='OCR 언어 (기본: kor+eng)')
    args = parser.parse_args()

    ocr_pdf(args.pdf, dpi=args.dpi, lang=args.lang)
