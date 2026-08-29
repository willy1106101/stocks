import os
import sys
import json
import subprocess
import threading
from pathlib import Path
import webview
import pystray
from PIL import Image, ImageDraw
from typing import Any
from desktop_bridge import DesktopApi
from update import GITHUB_API, GITHUB_REPOSITORY, fetch_json, version_key

window: Any = None
tray_icon: Any = None


def resource_path(filename: str) -> Path:
    """Resolve bundled files when running from PyInstaller or source."""
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_dir / filename


def current_version() -> str:
    """Read the version bundled with this application build."""
    try:
        return str(json.loads(resource_path("version.json").read_text(encoding="utf-8"))["version"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return "0.0.0"


def updater_command() -> list[str] | None:
    """Return the separately packaged updater command when it is available."""
    app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    updater = app_dir / ("update.exe" if getattr(sys, "frozen", False) else "update.py")
    if not updater.exists():
        return None
    if getattr(sys, "frozen", False):
        return [str(updater), "--target", str(app_dir / "willyStocks.exe")]
    return [sys.executable, str(updater), "--target", str(app_dir / "dist" / "willyStocks.exe")]


def check_for_update() -> None:
    """Check GitHub silently; an update is always confirmed by the user."""
    if GITHUB_REPOSITORY.startswith("YOUR_GITHUB_"):
        return

    command = updater_command()
    if command is None:
        return

    try:
        release = fetch_json(GITHUB_API.format(repository=GITHUB_REPOSITORY))
        latest_version = str(release.get("tag_name", "")).lstrip("vV")
        if not latest_version or version_key(latest_version) <= version_key(current_version()):
            return

        if window and window.create_confirmation_dialog(
            "發現新版",
            f"目前版本：v{current_version()}\n最新版本：v{latest_version}\n\n是否立即下載並更新？",
        ):
            subprocess.Popen(command + ["--wait-pid", str(os.getpid())], cwd=str(Path(command[0]).parent))
            os._exit(0)
    except Exception:
        # Update checks must never prevent the stock application from opening.
        return

def create_tray_image():
    image = Image.new('RGB', (64, 64), color=(37, 99, 235))
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
    return image

def on_show(icon, item):
    if window:
        window.show()
        window.restore()

def on_exit(icon, item):
    icon.stop()
    if window:
        window.destroy()
    os._exit(0)

def setup_tray():
    global tray_icon
    image = create_tray_image()
    menu = pystray.Menu(
        pystray.MenuItem('顯示視窗', on_show, default=True),
        pystray.MenuItem('結束程式', on_exit)
    )
    tray_icon = pystray.Icon("stock_terminal", image, "股票工具", menu)
    tray_icon.run()


def after_window_started():
    threading.Thread(target=check_for_update, daemon=True).start()
    setup_tray()

if __name__ == '__main__':
    window = webview.create_window(
        title="股票工具",
        # Open the bundled HTML file directly.  No localhost server is used.
        url=resource_path("dashboard.html").as_uri(),
        js_api=DesktopApi(),
        width=1450,
        height=900,
        resizable=True,
        min_size=(1024, 700)
    )

    # 攔截視窗的關閉 (X) 事件，改為隱藏視窗而不結束程式
    def on_closing():
        window.hide()
        return False  # 回傳 False 代表取消預設的關閉銷毀行為

    window.events.closing += on_closing

    webview.start(func=after_window_started)

    if tray_icon:
        tray_icon.stop()
