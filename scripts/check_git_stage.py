#!/usr/bin/env python3
import sys
import os
import subprocess

FORBIDDEN_EXTENSIONS = ('.db', '.db-wal', '.db-shm', '.sqlite', '.pth', '.zip', '.joblib', '.pkl')
FORBIDDEN_PATHS = ('dist/', 'node_modules/', 'chroma_db/', 'models/')
MAX_SIZE_BYTES = 5 * 1024 * 1024 # 5 MB

def check_staged_files():
    try:
        res = subprocess.run(['git', 'diff', '--cached', '--name-only'], capture_output=True, text=True, check=True)
        staged_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
    except Exception as e:
        print(f"[PRE-COMMIT HOOK WARN] Failed to get staged files: {e}")
        return 0

    errors = []
    for file_path in staged_files:
        # Check forbidden extensions
        if file_path.endswith(FORBIDDEN_EXTENSIONS):
            errors.append(f"Forbidden binary/database file extension: {file_path}")
            continue

        # Check forbidden paths
        if any(file_path.startswith(p) for p in FORBIDDEN_PATHS):
            errors.append(f"Forbidden directory path: {file_path}")
            continue

        # Check file size if file exists on disk
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            if size > MAX_SIZE_BYTES:
                errors.append(f"File exceeds maximum size limit (5MB): {file_path} ({size / (1024*1024):.2f} MB)")

    if errors:
        print("\n❌ [PRE-COMMIT REJECTED] The following files violate git staging guidelines:\n")
        for err in errors:
            print(f"  - {err}")
        print("\nPlease remove them from staging using `git reset HEAD <file>` before committing.\n")
        return 1

    print("✅ [PRE-COMMIT] All staged files passed safety validation.")
    return 0

if __name__ == '__main__':
    sys.exit(check_staged_files())
