import os
import zipfile
import shutil
import glob
import sys
from datetime import datetime
import requests

def upload_to_fileio(filepath):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Internetga (file.io) vaqtinchalik zaxira yuklanmoqda...")
    try:
        url = 'https://file.io'
        with open(filepath, 'rb') as f:
            response = requests.post(url, files={'file': f})
        
        if response.status_code == 200:
            data = response.json()
            link = data.get('link')
            print(f"[MUVAFFAQIYATLI] Internetga yuklandi!")
            print(f"Yuklab olish ssilkasi (Faqat 1 marta yuklash mumkin, 14 kun turadi): {link}")
        else:
            print(f"[XATOLIK] Internetga yuklash muvaffaqiyatsiz bo'ldi. Status code: {response.status_code}")
    except Exception as e:
        print(f"[XATOLIK] Yuklashda xato: {e}")

def export_data():
    project_root = os.path.dirname(os.path.abspath(__file__))
    zip_filename = "bot_migration_package.zip"
    zip_path = os.path.join(project_root, zip_filename)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Zaxira nusxasi yaratilmoqda: {zip_filename}...")
    
    files_to_zip = []
    
    # Barcha .db fayllar
    db_files = glob.glob(os.path.join(project_root, "*.db"))
    files_to_zip.extend(db_files)
    
    # Maxsus fayllar
    special_files = [".env", "config.json"]
    for sf in special_files:
        sf_path = os.path.join(project_root, sf)
        if os.path.exists(sf_path):
            files_to_zip.append(sf_path)
            
    # Chroma_db jild
    chroma_dir = os.path.join(project_root, "chroma_db")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Fayllarni qo'shish
        for file in files_to_zip:
            if os.path.exists(file):
                print(f"Qo'shilmoqda: {os.path.basename(file)}")
                zipf.write(file, arcname=os.path.basename(file))
                
        # Jildlarni qo'shish
        if os.path.exists(chroma_dir):
            print("Qo'shilmoqda: chroma_db/")
            for root, dirs, files in os.walk(chroma_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join("chroma_db", os.path.relpath(file_path, chroma_dir))
                    zipf.write(file_path, arcname=arcname)
                    
    print(f"\n[MUVAFFAQIYATLI] ZIP arxiv yaratildi: {zip_path}")
    print(f"Hajmi: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
    
    # D: diskiga nusxalash (USB Fleshka)
    usb_drive = "D:\\"
    usb_zip_path = os.path.join(usb_drive, zip_filename)
    if os.path.exists(usb_drive):
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Fleshkaga (D:\) nusxalanmoqda...")
            shutil.copy2(zip_path, usb_zip_path)
            print(f"[MUVAFFAQIYATLI] Fleshkaga nusxalandi: {usb_zip_path}")
        except Exception as e:
            print(f"[XATOLIK] Fleshkaga nusxalashda xato: {e}")
    else:
        print("\n[OGOHLANTIRISH] D:\ diski (Fleshka) topilmadi!")

    print("\n" + "="*60)
    print("MUHIM: INTERNETGA DOIMIY NUSXA OLISH")
    print("="*60)
    print("Fleshkadagi ma'lumotlar o'chib ketsa, tiklash uchun:")
    print("O'zingizning Telegramingizdagi 'Saved Messages' ga yoki")
    print("Google Drive / Yandex Disk ga ushbu ZIP faylni yuklab qo'ying:")
    print(f"-> {zip_path}")
    print("="*60)
    
    upload_to_fileio(zip_path)

if __name__ == "__main__":
    export_data()
