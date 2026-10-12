from __future__ import annotations

import argparse
import hashlib
import ipaddress
import io
import json
import mimetypes
import os
import secrets
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import qrcode
import yt_dlp


APP_NAME = "VideoGrab Mobile"
APP_VERSION = "2.3.2"
HOST = "0.0.0.0"
DEFAULT_PORT = 8765
MAX_BODY = 64 * 1024
PUBLIC_FILE_TTL = 2 * 60 * 60
PUBLIC_MAX_BYTES = 2 * 1024 * 1024 * 1024
PUBLIC_MAX_DURATION = 2 * 60 * 60


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VideoGrab" / "mobile"
    base.mkdir(parents=True, exist_ok=True)
    return base


def normalize_proxy(value: str) -> str:
    proxy = value.strip()
    if not proxy:
        return ""
    parsed = urllib.parse.urlsplit(proxy)
    if (
        parsed.scheme not in {"http", "https", "socks5", "socks5h"}
        or not parsed.hostname
        or not parsed.port
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or len(proxy) > 512
    ):
        raise ValueError("请输入有效的代理地址，例如 http://127.0.0.1:7897")
    return proxy


def active_proxy(value: str) -> str:
    """Ignore a stopped loopback proxy so other sites can still use direct access."""
    proxy = normalize_proxy(value)
    if not proxy:
        return ""
    parsed = urllib.parse.urlsplit(proxy)
    if parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        try:
            with socket.create_connection((parsed.hostname, parsed.port), timeout=0.3):
                pass
        except OSError:
            return ""
    return proxy


def configured_proxy() -> str:
    override = os.environ.get("VIDEOGRAB_DATA_DIR")
    settings_dir = Path(override) if override else Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VideoGrab"
    try:
        settings = json.loads((settings_dir / "settings.json").read_text(encoding="utf-8"))
        return normalize_proxy(str(settings.get("proxy") or ""))
    except (OSError, ValueError, AttributeError):
        return ""


def download_dir() -> Path:
    override = os.environ.get("VIDEOGRAB_MOBILE_OUTPUT_DIR")
    target = Path(override) if override else Path.home() / "Downloads" / "VideoGrab-Mobile"
    target.mkdir(parents=True, exist_ok=True)
    return target


def public_download_dir() -> Path:
    target = data_dir() / "public-cache"
    target.mkdir(parents=True, exist_ok=True)
    return target


def validate_public_url(value: str) -> str:
    """Reject local/private destinations before handing a public request to yt-dlp."""
    url = value.strip()
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("请输入有效的 http:// 或 https:// 链接。")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("公开模式不能访问本机或局域网地址。")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ValueError("无法解析该链接的服务器地址。") from exc
    for raw in addresses:
        if not ipaddress.ip_address(raw).is_global:
            raise ValueError("公开模式不能访问本机、局域网或保留网络地址。")
    return url


def load_or_create_token() -> str:
    path = data_dir() / "pairing-token.txt"
    try:
        token = path.read_text(encoding="utf-8").strip()
        if len(token) >= 24:
            return token
    except OSError:
        pass
    token = secrets.token_urlsafe(24)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(token, encoding="utf-8")
    temporary.replace(path)
    return token


def local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("1.1.1.1", 80))
        return str(sock.getsockname()[0])
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()


def format_selector(height: int | None) -> str:
    limit = f"[height<={height}]" if height else ""
    return f"bv*{limit}+ba/b{limit}"


def media_options(browser: str | None = None) -> dict[str, Any]:
    candidates = [
        resource_path("vendor", "ffmpeg.exe"),
        resource_path("..", "vendor", "ffmpeg.exe"),
        resource_path("..", "VideoGrab", "vendor", "ffmpeg.exe"),
    ]
    node_candidates = [
        resource_path("vendor", "node.exe"),
        resource_path("..", "vendor", "node.exe"),
        resource_path("..", "VideoGrab", "vendor", "node.exe"),
    ]
    options: dict[str, Any] = {
        "noplaylist": True,
        "windowsfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "continuedl": True,
    }
    ffmpeg = next((p.resolve() for p in candidates if p.exists()), None)
    node = next((p.resolve() for p in node_candidates if p.exists()), None)
    if ffmpeg:
        options["ffmpeg_location"] = str(ffmpeg)
    if node:
        options["js_runtimes"] = {"node": {"path": str(node)}}
    if browser in {"edge", "chrome", "firefox"}:
        options["cookiesfrombrowser"] = (browser,)
    proxy = active_proxy(configured_proxy())
    if proxy:
        options["proxy"] = proxy
    return options


def public_media_options() -> dict[str, Any]:
    options = media_options(None)
    options["max_filesize"] = PUBLIC_MAX_BYTES

    def public_filter(info: dict[str, Any], *, incomplete: bool = False) -> str | None:
        duration = info.get("duration")
        if duration and float(duration) > PUBLIC_MAX_DURATION:
            return "公开模式仅支持 2 小时以内的内容。"
        return None

    options["match_filter"] = public_filter
    return options


def friendly_error(exc: Exception) -> str:
    detail = str(exc).replace("ERROR:", "").strip()
    if len(detail) > 700:
        detail = detail[-700:]
    return detail or exc.__class__.__name__


class State:
    def __init__(self, port: int):
        self.port = port
        self.token = load_or_create_token()
        self.output = download_dir()
        self.public_output = public_download_dir()
        self.jobs: dict[str, dict[str, Any]] = {}
        self.lock = threading.RLock()
        self.active_job: str | None = None
        self.rate_limits: dict[tuple[str, str], list[float]] = {}

    @property
    def share_url(self) -> str:
        encoded = urllib.parse.quote(self.token)
        return f"http://{local_ip()}:{self.port}/?token={encoded}"

    def public_job(self, job: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in job.items()
            if key not in {"cancel", "paths", "owner"}
        }

    def allow_request(self, client: str, action: str) -> bool:
        count, window = {"analyze": (10, 60), "download": (3, 60 * 60)}[action]
        now = time.time()
        key = (client, action)
        with self.lock:
            recent = [stamp for stamp in self.rate_limits.get(key, []) if now - stamp < window]
            if len(recent) >= count:
                self.rate_limits[key] = recent
                return False
            recent.append(now)
            self.rate_limits[key] = recent
        return True

    def cleanup_public_cache(self) -> None:
        cutoff = time.time() - PUBLIC_FILE_TTL
        with self.lock:
            stale_jobs = [
                job_id for job_id, job in self.jobs.items()
                if job.get("public") and job.get("finished_at", time.time()) < cutoff
                and job.get("status") in {"complete", "error", "cancelled"}
            ]
            paths = [Path(path) for job_id in stale_jobs for path in self.jobs[job_id].get("paths", {}).values()]
            for job_id in stale_jobs:
                self.jobs.pop(job_id, None)
        for path in paths:
            try:
                if self.public_output.resolve() in path.resolve().parents:
                    path.unlink(missing_ok=True)
            except OSError:
                pass

    def create_job(self, payload: dict[str, Any], public: bool = False, owner: str = "local") -> dict[str, Any]:
        is_en = str(payload.get("language") or "zh") == "en"
        with self.lock:
            if self.active_job:
                active = self.jobs.get(self.active_job)
                if active and active["status"] in {"queued", "downloading", "processing"}:
                    raise RuntimeError("已有下载任务正在进行，请等待完成或先取消。")
            job_id = secrets.token_hex(8)
            job: dict[str, Any] = {
                "id": job_id,
                "url": str(payload.get("url", "")),
                "status": "queued",
                "progress": 0.0,
                "message": "Preparing…" if is_en else "正在准备…",
                "language": "en" if is_en else "zh",
                "title": "",
                "created": datetime.now().isoformat(timespec="seconds"),
                "files": [],
                "paths": {},
                "public": public,
                "owner": owner,
                "cancel": threading.Event(),
            }
            self.jobs[job_id] = job
            self.active_job = job_id
        threading.Thread(target=self._download, args=(job_id, payload, public), daemon=True).start()
        return self.public_job(job)

    def cancel_job(self, job_id: str, public: bool = False, owner: str = "local") -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or (public and (not job.get("public") or job.get("owner") != owner)):
                return False
            job["cancel"].set()
            job["message"] = "Cancelling…" if job.get("language") == "en" else "正在取消…"
            return True

    def _download(self, job_id: str, payload: dict[str, Any], public: bool = False) -> None:
        with self.lock:
            job = self.jobs[job_id]
        url = str(payload.get("url", "")).strip()
        want_video = bool(payload.get("video", True))
        want_cover = bool(payload.get("cover", False))
        want_mp3 = bool(payload.get("mp3", False))
        browser = None if public else (str(payload.get("browser") or "") or None)
        output = self.public_output if public else self.output
        is_en = str(payload.get("language") or "zh") == "en"
        phrase = lambda zh, en: en if is_en else zh
        try:
            quality = int(payload.get("quality") or 0) or None
        except (TypeError, ValueError):
            quality = None
        started = time.time()
        before = {p.resolve() for p in output.iterdir() if p.is_file()}
        count = int(want_video) + int(want_mp3) + int(want_cover and not (want_video or want_mp3))
        if not url.startswith(("http://", "https://")):
            self._fail(job_id, phrase("请输入有效的 http:// 或 https:// 链接。", "Enter a valid http:// or https:// URL."))
            return
        if public:
            try:
                url = validate_public_url(url)
            except ValueError as exc:
                self._fail(job_id, str(exc))
                return
        if count == 0:
            self._fail(job_id, phrase("请至少选择视频、封面或 MP3 中的一项。", "Select video, cover, or MP3."))
            return

        current = 0
        phase = phrase("视频", "Video")

        def update(**values: Any) -> None:
            with self.lock:
                job.update(values)

        def hook(data: dict[str, Any]) -> None:
            if job["cancel"].is_set():
                raise RuntimeError("cancelled")
            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                downloaded = data.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total else 0.0
                overall = ((current + percent / 100) / max(count, 1)) * 100
                speed = str(data.get("_speed_str") or "").strip()
                eta = str(data.get("_eta_str") or "").strip()
                eta_label = "ETA" if is_en else "剩余"
                update(status="downloading", progress=round(overall, 1), message=f"{phase} {percent:.1f}%  {speed}  {eta_label} {eta}")
            elif data.get("status") == "finished":
                update(status="processing", message=(f"{phase} downloaded. Processing…" if is_en else f"{phase}下载完成，正在处理…"))

        common = public_media_options() if public else media_options(browser)
        common.update({"progress_hooks": [hook]})
        jobs: list[tuple[str, dict[str, Any]]] = []
        if want_video:
            opts = dict(common)
            opts.update({
                "outtmpl": str(output / "%(title).170B [%(id)s] [Video].%(ext)s"),
                "format": format_selector(quality),
                "merge_output_format": "mp4",
                "writethumbnail": want_cover,
                "postprocessors": ([{"key": "FFmpegThumbnailsConvertor", "format": "jpg"}] if want_cover else []),
            })
            jobs.append((phrase("视频", "Video"), opts))
        if want_mp3:
            opts = dict(common)
            save_cover = want_cover and not want_video
            post = ([{"key": "FFmpegThumbnailsConvertor", "format": "jpg"}] if save_cover else [])
            post.append({"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"})
            opts.update({
                "outtmpl": str(output / "%(title).170B [%(id)s] [Audio].%(ext)s"),
                "format": "bestaudio/best",
                "writethumbnail": save_cover,
                "postprocessors": post,
            })
            jobs.append(("MP3", opts))
        if want_cover and not (want_video or want_mp3):
            opts = dict(common)
            opts.update({
                "outtmpl": str(output / "%(title).170B [%(id)s] [Cover].%(ext)s"),
                "skip_download": True,
                "writethumbnail": True,
                "postprocessors": [{"key": "FFmpegThumbnailsConvertor", "format": "jpg"}],
            })
            jobs.append((phrase("封面", "Cover"), opts))

        try:
            info: dict[str, Any] | None = None
            for current, (phase, opts) in enumerate(jobs):
                if job["cancel"].is_set():
                    raise RuntimeError("cancelled")
                update(status="processing", message=(f"Processing {phase}…" if is_en else f"正在处理{phase}…"))
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                update(progress=round(((current + 1) / count) * 100, 1))
            if info is None:
                raise RuntimeError(phrase("没有返回可用媒体。", "No media was returned."))

            candidates = []
            for path in output.iterdir():
                if not path.is_file() or path.suffix.lower() in {".part", ".ytdl", ".tmp"}:
                    continue
                resolved = path.resolve()
                if resolved not in before or path.stat().st_mtime >= started - 2:
                    candidates.append(path)
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            paths: dict[str, str] = {}
            files: list[dict[str, Any]] = []
            for path in candidates[:8]:
                key = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
                paths[key] = str(path)
                files.append({"id": key, "name": path.name, "size": path.stat().st_size})
            update(
                status="complete",
                progress=100.0,
                message=phrase("下载完成", "Download complete"),
                title=str(info.get("title") or phrase("媒体文件", "Media file")),
                files=files,
                paths=paths,
                finished_at=time.time(),
            )
        except Exception as exc:
            if job["cancel"].is_set() or str(exc) == "cancelled":
                update(status="cancelled", message=phrase("下载已取消", "Download cancelled"), finished_at=time.time())
            else:
                update(status="error", message=friendly_error(exc), finished_at=time.time())
        finally:
            with self.lock:
                if self.active_job == job_id:
                    self.active_job = None

    def _fail(self, job_id: str, message: str) -> None:
        with self.lock:
            self.jobs[job_id].update(status="error", message=message, finished_at=time.time())
            if self.active_job == job_id:
                self.active_job = None


class Handler(BaseHTTPRequestHandler):
    server_version = "VideoGrabMobile/1.0"

    @property
    def state(self) -> State:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _token(self) -> str:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        return self.headers.get("X-VideoGrab-Token", "") or query.get("token", [""])[0]

    def _authorized(self) -> bool:
        return secrets.compare_digest(self._token(), self.state.token)

    def _is_public(self) -> bool:
        host = self.headers.get("Host", "").split(":", 1)[0].lower()
        return bool(self.headers.get("CF-Connecting-IP")) or host.endswith(".trycloudflare.com")

    def _client_key(self) -> str:
        if self._is_public():
            return self.headers.get("CF-Connecting-IP", self.client_address[0])
        return self.client_address[0]

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > MAX_BODY:
            raise ValueError("请求内容无效。")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("请求内容无效。")
        return payload

    def _serve_static(self, name: str) -> None:
        root = resource_path("web").resolve()
        target = (root / name).resolve()
        if root not in target.parents and target != root:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-cache" if target.suffix in {".html", ".js"} else "public, max-age=86400")
        self.end_headers()
        self.wfile.write(body)

    def _serve_download(self, job_id: str, file_id: str) -> None:
        with self.state.lock:
            job = self.state.jobs.get(job_id)
            if self._is_public() and job and (not job.get("public") or job.get("owner") != self._client_key()):
                job = None
            raw_path = (job or {}).get("paths", {}).get(file_id)
        if not raw_path:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        path = Path(raw_path).resolve()
        allowed_outputs = {self.state.output.resolve(), self.state.public_output.resolve()}
        if not any(root in path.parents for root in allowed_outputs) or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        total = path.stat().st_size
        start, end = 0, total - 1
        range_header = self.headers.get("Range", "")
        if range_header.startswith("bytes="):
            try:
                left, right = range_header[6:].split("-", 1)
                start = int(left) if left else 0
                end = int(right) if right else total - 1
                end = min(end, total - 1)
            except ValueError:
                start, end = 0, total - 1
        length = max(0, end - start + 1)
        self.send_response(206 if range_header else 200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{urllib.parse.quote(path.name)}")
        if range_header:
            self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
        self.end_headers()
        with path.open("rb") as handle:
            handle.seek(start)
            remaining = length
            while remaining:
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self) -> None:
        self.state.cleanup_public_cache()
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        if path in {"/", "/index.html"}:
            self._serve_static("index.html")
            return
        static = {
            "/app.css": "app.css",
            "/app.js": "app.js",
            "/sw.js": "sw.js",
            "/manifest.webmanifest": "manifest.webmanifest",
            "/logo.png": "logo.png",
        }
        if path in static:
            self._serve_static(static[path])
            return
        if path == "/api/config":
            if not self._authorized():
                self._json({"error": "pairing_required"}, 401)
                return
            self._json({
                "name": APP_NAME,
                "version": APP_VERSION,
                "shareUrl": self.state.share_url,
                "output": str(self.state.output),
                "publicMode": self._is_public(),
                "retentionHours": PUBLIC_FILE_TTL // 3600,
            })
            return
        if path == "/api/jobs":
            if not self._authorized():
                self._json({"error": "pairing_required"}, 401)
                return
            with self.state.lock:
                values = reversed(list(self.state.jobs.values()))
                if self._is_public():
                    owner = self._client_key()
                    values = (item for item in values if item.get("public") and item.get("owner") == owner)
                jobs = [self.state.public_job(item) for item in values]
            self._json({"jobs": jobs[:20]})
            return
        if path == "/api/qr.png":
            if not self._authorized():
                self._json({"error": "pairing_required"}, 401)
                return
            qr = qrcode.QRCode(version=None, box_size=8, border=3)
            qr.add_data(self.state.share_url)
            qr.make(fit=True)
            image = qr.make_image(fill_color="#151515", back_color="#F4F0E8")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            body = buffer.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/file":
            if not self._authorized():
                self._json({"error": "pairing_required"}, 401)
                return
            query = urllib.parse.parse_qs(parsed.query)
            self._serve_download(query.get("job", [""])[0], query.get("file", [""])[0])
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if not self._authorized():
            self._json({"error": "pairing_required"}, 401)
            return
        try:
            payload = self._read_json()
            public = self._is_public()
            if parsed.path == "/api/analyze":
                if public and not self.state.allow_request(self._client_key(), "analyze"):
                    self._json({"error": "解析请求过于频繁，请稍后再试。"}, 429)
                    return
                url = str(payload.get("url", "")).strip()
                if not url.startswith(("http://", "https://")):
                    raise ValueError("请输入有效链接。")
                if public:
                    url = validate_public_url(url)
                browser = None if public else (str(payload.get("browser") or "") or None)
                with yt_dlp.YoutubeDL(public_media_options() if public else media_options(browser)) as ydl:
                    info = ydl.extract_info(url, download=False)
                formats = info.get("formats") or []
                heights = sorted({int(item["height"]) for item in formats if item.get("height")}, reverse=True)
                thumb = str(info.get("thumbnail") or "")
                self._json({
                    "title": str(info.get("title") or "未知媒体"),
                    "duration": str(info.get("duration_string") or "—"),
                    "source": str(info.get("extractor_key") or info.get("extractor") or "网页"),
                    "thumbnail": thumb,
                    "qualities": heights[:12],
                    "formatCount": len(formats),
                })
                return
            if parsed.path == "/api/download":
                if public and not self.state.allow_request(self._client_key(), "download"):
                    self._json({"error": "每位访客每小时最多创建 3 个下载任务。"}, 429)
                    return
                self._json(self.state.create_job(payload, public=public, owner=self._client_key()), 202)
                return
            if parsed.path == "/api/cancel":
                job_id = str(payload.get("id") or "")
                self._json({"cancelled": self.state.cancel_job(job_id, public=public, owner=self._client_key())})
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as exc:
            self._json({"error": friendly_error(exc)}, 400)
        except Exception as exc:
            self._json({"error": friendly_error(exc)}, 500)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], state: State):
        self.state = state
        super().__init__(address, Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    if args.smoke_test:
        assert resource_path("web", "index.html").is_file()
        assert media_options()
        print(f"{APP_NAME} {APP_VERSION} smoke test passed")
        return
    state = State(args.port)
    server = Server((HOST, args.port), state)
    local_url = f"http://127.0.0.1:{args.port}/?token={urllib.parse.quote(state.token)}"
    print(f"{APP_NAME} {APP_VERSION}")
    print(f"Computer: {local_url}")
    print(f"iPhone:   {state.share_url}")
    print("Keep this window open while using the phone.")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(local_url)).start()
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
