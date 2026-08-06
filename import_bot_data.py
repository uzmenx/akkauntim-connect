import os
import zipfile
import shutil
from datetime import datetime

def import_data():
    project_root = os.path.dirname(os.path.abspath(__file__))
    zip_filename = "bot_migration_package.zip"
    
    # Fleshkadan izlash (D:\) yoki joriy papkadan
    zip_paths_to_check = [
        os.path.join(project_root, zip_filename),
        os.path.join("D:\\", zip_filename)
    ]
    
    found_path = None
    for path in zip_paths_to_check:
        if os.path.exists(path):
            found_path = path
            break
            
    if not found_path:
        print(f"[XATOLIK] {zip_filename} fayli topilmadi!")
        print("Iltimos, faylni shu papkaga yoki D:\\ (USB) ga joylashtiring.")
        return
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Zaxira topildi: {found_path}")
    print("Tiklash jarayoni boshlanmoqda...")
    
    try:
        with zipfile.ZipFile(found_path, 'r') as zipf:
            # Fayllarni arxivdan chiqarish
            zipf.extractall(project_root)
            
        print(f"\n[MUVAFFAQIYATLI] Barcha ma'lumotlar qayta tiklandi!")
        print("Sizning .db bazalaringiz, chroma_db va .env fayllaringiz joyiga qaytdi.")
    except Exception as e:
        print(f"\n[XATOLIK] Tiklashda xato yuz berdi: {e}")

if __name__ == "__main__":
    import_data()
