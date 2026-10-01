import http.server
import socketserver
import json
import os
import glob
import threading
import time
import math

# --- 設定 ---
PORT = 8000
PHOTO_DIR = "photos00"
# 操作権のタイムアウト（秒）
CONTROL_TIMEOUT = 30

class SlideshowHandler(http.server.SimpleHTTPRequestHandler):
    current_index = 0
    image_list = []
    # スライドショーの自動再生設定
    auto_play = True
    lock = threading.Lock()

    def do_GET(self):
        if not SlideshowHandler.image_list:
            exts = ('.jpg', '.jpeg', '.png', '.JPG', '.PNG')
            files = []
            # PHOTO_DIR配下を再帰的に探索
            for root, dirs, filenames in os.walk(PHOTO_DIR):
                for filename in filenames:
                    if filename.endswith(exts):
                        files.append(os.path.join(root, filename))

            # 重複を除去してソート
            SlideshowHandler.image_list = sorted(list(set(files)))

        if self.path == '/status':
            with SlideshowHandler.lock:
                self._send_json({
                    "index": SlideshowHandler.current_index,
                    "total": len(SlideshowHandler.image_list),
                    "auto_play": SlideshowHandler.auto_play,
                    "image_list": SlideshowHandler.image_list
                })

        elif self.path == '/current_image_url':
            if SlideshowHandler.image_list:
                img_path = SlideshowHandler.image_list[SlideshowHandler.current_index]
                url_path = '/' + img_path.replace('\\', '/')
                # フォルダパスを抽出 (photosフォルダ以降の部分)
                relative_path = os.path.relpath(os.path.dirname(img_path), PHOTO_DIR)
                # ルート(photos)直下の場合は空にする
                if relative_path == '.':
                    folder_path = ""
                else:
                    # WindowsパスをWeb形式(/)に変換
                    folder_path = relative_path.replace('\\', '/')

                self._send_json({"url": url_path, "folder": folder_path})
            else:
                self._send_json({"url": "", "folder": ""})

        elif self.path.startswith('/set_index'):
            try:
                index = int(self.path.split('=')[-1])
                with SlideshowHandler.lock:
                    if 0 <= index < len(SlideshowHandler.image_list):
                        SlideshowHandler.current_index = index
                        self._send_json({"success": True, "index": index})
                    else:
                        self._send_json({"success": False, "message": "Invalid index"})
            except ValueError:
                self._send_json({"success": False, "message": "Invalid index format"})

        elif self.path == '/toggle_autoplay':
            with SlideshowHandler.lock:
                SlideshowHandler.auto_play = not SlideshowHandler.auto_play
                self._send_json({"success": True, "auto_play": SlideshowHandler.auto_play})

        else:
            super().do_GET()

    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

def robust_maintenance_loop():
    next_auto_advance_time = 0
    while True:
        time.sleep(0.5)
        with SlideshowHandler.lock:
            now = time.time()
            # 自動再生が有効な場合のみ進める
            if SlideshowHandler.auto_play and SlideshowHandler.image_list:
                if next_auto_advance_time == 0:
                    next_auto_advance_time = math.ceil(now / 10) * 10
                if now >= next_auto_advance_time:
                    SlideshowHandler.current_index = (SlideshowHandler.current_index + 1) % len(SlideshowHandler.image_list)
                    print(f"Auto-advanced to index: {SlideshowHandler.current_index}")
                    next_auto_advance_time = now + 10
            else:
                next_auto_advance_time = 0

if __name__ == "__main__":
    threading.Thread(target=robust_maintenance_loop, daemon=True).start()
    with socketserver.TCPServer(("0.0.0.0", PORT), SlideshowHandler) as httpd:
        print(f"🚀 Hybrid Control Server started at http://0.0.0.0:{PORT}")
        print(f"📱 Access via your PC IP address (e.g., http://192.168.1.97:{PORT})")
        httpd.serve_forever()
