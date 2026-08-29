"""Update willyStocks from the latest GitHub Release.

Before distribution, replace GITHUB_REPOSITORY with "owner/repository".
Publish an asset named willyStocks.exe for every stable GitHub Release.
Optionally publish willyStocks.exe.sha256 containing the SHA-256 hash of that
EXE; when it is present, this updater verifies the download before replacing
the installed file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# Change this before releasing the application, e.g. "willy/stocks".
GITHUB_REPOSITORY = "willy1106101/stocks"
APPLICATION_NAME = "willyStocks.exe"
VERSION_FILENAME = "version.json"
GITHUB_API = "https://api.github.com/repos/{repository}/releases/latest"
USER_AGENT = "willyStocks-updater/1.0"


def app_directory() -> Path:
    """Use the updater's directory when packaged, otherwise this source dir."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def version_key(version: str) -> tuple[int, ...]:
    """Compare ordinary numeric GitHub tags such as v1.2.3 safely."""
    clean = version.strip().lstrip("vV").split("-", 1)[0]
    parts = clean.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError(f"無法辨識版本格式：{version}")
    return tuple(int(part) for part in parts)


def read_current_version(directory: Path) -> str:
    version_file = directory / VERSION_FILENAME
    # During development the target is normally dist/willyStocks.exe while
    # version.json remains in the project root.  Packaged distributions should
    # keep version.json beside update.exe and willyStocks.exe.
    if not version_file.exists() and not getattr(sys, "frozen", False):
        version_file = app_directory() / VERSION_FILENAME
    if not version_file.exists():
        return "0.0.0"
    try:
        return str(json.loads(version_file.read_text(encoding="utf-8"))["version"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"無法讀取 {version_file.name}：{error}") from error


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"無法取得 GitHub Release（HTTP {error.code}）。") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"無法連線至 GitHub：{error}") from error


def download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=60) as response, destination.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"下載更新檔失敗：{error}") from error


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def release_asset(release: dict, name: str) -> dict | None:
    return next((asset for asset in release.get("assets", []) if asset.get("name") == name), None)


def update(target: Path, check_only: bool = False) -> int:
    if GITHUB_REPOSITORY.startswith("YOUR_GITHUB_"):
        print("請先在 update.py 設定 GITHUB_REPOSITORY，例如：your-account/your-repository")
        return 2

    directory = target.parent
    current_version = read_current_version(directory)
    release = fetch_json(GITHUB_API.format(repository=GITHUB_REPOSITORY))
    latest_version = str(release.get("tag_name", "")).lstrip("vV")
    if not latest_version:
        raise RuntimeError("GitHub Release 沒有 tag_name。")

    if version_key(latest_version) <= version_key(current_version):
        print(f"目前已是最新版：v{current_version}")
        return 0

    print(f"發現新版：v{latest_version}（目前 v{current_version}）")
    if check_only:
        return 1
    if not target.exists():
        raise RuntimeError(f"找不到要更新的程式：{target}")

    asset = release_asset(release, APPLICATION_NAME)
    if not asset or not asset.get("browser_download_url"):
        raise RuntimeError(f"Release 找不到 {APPLICATION_NAME}。")

    temporary_file = target.with_suffix(target.suffix + ".new")
    print("正在下載新版…")
    download(asset["browser_download_url"], temporary_file)

    checksum_asset = release_asset(release, f"{APPLICATION_NAME}.sha256")
    if checksum_asset and checksum_asset.get("browser_download_url"):
        checksum_file = temporary_file.with_suffix(".sha256")
        download(checksum_asset["browser_download_url"], checksum_file)
        expected = checksum_file.read_text(encoding="utf-8").strip().split()[0].lower()
        checksum_file.unlink(missing_ok=True)
        if sha256(temporary_file).lower() != expected:
            temporary_file.unlink(missing_ok=True)
            raise RuntimeError("SHA-256 驗證失敗，已取消更新。")

    try:
        os.replace(temporary_file, target)
        (directory / VERSION_FILENAME).write_text(
            json.dumps({"version": latest_version}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except PermissionError as error:
        raise RuntimeError("無法取代執行檔。請先完全關閉股票工具後再執行更新。") from error
    finally:
        temporary_file.unlink(missing_ok=True)

    print(f"更新完成：v{latest_version}")
    return 0


def wait_for_process_exit(pid: int) -> None:
    """Wait briefly for the application that launched this updater to close."""
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.25)
    raise RuntimeError("等待主程式結束逾時，請關閉程式後再更新。")


def main() -> int:
    parser = argparse.ArgumentParser(description="從 GitHub Releases 更新股票工具")
    parser.add_argument("--target", type=Path, help="要更新的 willyStocks.exe 路徑")
    parser.add_argument("--check", action="store_true", help="只檢查是否有新版，不下載")
    parser.add_argument("--wait-pid", type=int, help="更新前等待指定的主程式結束")
    args = parser.parse_args()

    default_target = app_directory() / APPLICATION_NAME
    if not default_target.exists() and not getattr(sys, "frozen", False):
        default_target = app_directory() / "dist" / APPLICATION_NAME

    try:
        if args.wait_pid:
            wait_for_process_exit(args.wait_pid)
        return update((args.target or default_target).resolve(), args.check)
    except (RuntimeError, ValueError) as error:
        print(f"更新失敗：{error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
