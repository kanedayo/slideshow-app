import os
from pathlib import Path
from PIL import Image
import tempfile
import shutil

# 設定
TARGET_SIZE_KB = 500
TARGET_SIZE_BYTES = TARGET_SIZE_KB * 1024
EXTENSIONS = {'.jpg', '.jpeg', '.png'}
MAX_DIMENSION = 2000  # qualityを下げてもサイズが大きい場合の最大解像度

def compress_image(file_path):
    """
    画像を目標サイズ(TARGET_SIZE_KB)に合わせて圧縮する。
    """
    file_path = Path(file_path)
    original_size = file_path.stat().st_size

    if original_size <= TARGET_SIZE_BYTES:
        return None # 圧縮不要

    try:
        with Image.open(file_path) as img:
            # PNGなどの場合はRGBに変換してJPEGとして保存することを検討
            # (ファイルサイズ削減のため)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 1. Quality調整 (二分探索)
            best_quality = 95
            low = 1
            high = 95

            # 一時ファイルを作成してサイズを確認
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                while low <= high:
                    mid = (low + high) // 2
                    img.save(tmp_path, "JPEG", quality=mid, optimize=True)
                    current_size = os.path.getsize(tmp_path)

                    if current_size <= TARGET_SIZE_BYTES:
                        best_quality = mid
                        low = mid + 1
                    else:
                        high = mid - 1

                # 最終的な品質で保存
                img.save(tmp_path, "JPEG", quality=best_quality, optimize=True)
                final_size = os.path.getsize(tmp_path)

                # 2. それでも大きい場合はリサイズ
                if final_size > TARGET_SIZE_BYTES:
                    width, height = img.size
                    if max(width, height) > MAX_DIMENSION:
                        scale = MAX_DIMENSION / max(width, height)
                        new_size = (int(width * scale), int(height * scale))
                        img_resized = img.resize(new_size, Image.Resampling.LANCZOS)

                        # リサイズ後に再度品質調整（簡易的に低めの品質で試行）
                        img_resized.save(tmp_path, "JPEG", quality=70, optimize=True)
                        final_size = os.path.getsize(tmp_path)
                        # さらに調整が必要な場合は再度二分探索しても良いが、ここでは簡易化

                # 元ファイルに上書き保存 (安全のため一時ファイルからコピー)
                shutil.copy2(tmp_path, file_path)

                return original_size, final_size, best_quality

            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def main():
    print(f"Searching for images to compress to ~{TARGET_SIZE_KB}KB...")

    count = 0
    processed = 0

    # カレントディレクトリから再帰的に探索
    for path in Path('.').rglob('*'):
        if path.suffix.lower() in EXTENSIONS:
            count += 1
            result = compress_image(path)
            if result:
                orig, final, qual = result
                processed += 1
                print(f"Compressed: {path} | {orig/1024:.1f}KB -> {final/1024:.1f}KB (q={qual})")

    print(f"\nDone. Total images found: {count}, Compressed: {processed}")

if __name__ == "__main__":
    main()
