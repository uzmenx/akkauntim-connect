"""
file_reader.py — Kitob/maqola fayllaridan matn chiqarish.

Asl kod muammosi: file_path.read_text() faqat .txt fayllarda ishlaydi.
PDF binary fayl, uni shunday o'qish crash beradi yoki bo'sh string qaytaradi.

Bu modul PDF, DOCX, TXT — barchasini to'g'ri o'qiydi.
"""

from pathlib import Path
from typing import Optional


def extract_text(file_path: Path) -> Optional[str]:
    """
    Fayl turini aniqlaydi va mos ekstraktor bilan matnni chiqaradi.
    Xato bo'lsa None qaytaradi (dastur crash bo'lmasligi uchun) va sababini chop etadi.
    """
    suffix = file_path.suffix.lower()

    try:
        if suffix == ".pdf":
            return _extract_pdf(file_path)
        elif suffix == ".docx":
            return _extract_docx(file_path)
        elif suffix in (".txt", ".md"):
            return file_path.read_text(encoding="utf-8", errors="ignore")
        else:
            print(f"❌ Qo'llab-quvvatlanmaydigan format: {suffix} ({file_path.name})")
            return None
    except Exception as e:
        print(f"❌ Faylni o'qishda xato ({file_path.name}): {e}")
        return None


def _extract_pdf(file_path: Path) -> str:
    """PDF'dan matn chiqarish. Skanerlangan (rasm) PDF'lar uchun OCR kerak bo'lishi mumkin — bu funksiya faqat matn-qatlamli PDF'lar uchun ishlaydi."""
    import pypdf

    reader = pypdf.PdfReader(str(file_path))

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise ValueError("PDF parol bilan himoyalangan, ochib bo'lmadi")

    pages_text = []
    empty_page_count = 0

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages_text.append(text)
        else:
            empty_page_count += 1

    full_text = "\n\n".join(pages_text)

    # Agar sahifalarning ko'pi bo'sh bo'lsa — bu skanerlangan PDF, matn qatlami yo'q
    if empty_page_count > len(reader.pages) * 0.5 and len(reader.pages) > 3:
        print(
            f"⚠️ Ogohlantirish: {file_path.name} sahifalarining ko'pi matnsiz "
            f"({empty_page_count}/{len(reader.pages)}). Bu skanerlangan PDF bo'lishi mumkin, "
            f"OCR kerak bo'ladi (bu funksiya OCR qilmaydi)."
        )

    if not full_text.strip():
        raise ValueError("PDF'dan hech qanday matn chiqmadi (skanerlangan bo'lishi mumkin)")

    return full_text


def _extract_docx(file_path: Path) -> str:
    """DOCX'dan matn chiqarish."""
    import docx

    doc = docx.Document(str(file_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Ishlatish: python file_reader.py <fayl_yoli>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"❌ Fayl topilmadi: {path}")
        sys.exit(1)

    text = extract_text(path)
    if text:
        print(f"✅ {len(text)} belgi chiqarildi")
        print(f"Birinchi 300 belgi:\n{text[:300]}")
    else:
        print("❌ Matn chiqarilmadi")
