from __future__ import annotations

import io
import json
import os
import queue
import re
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from urllib.request import Request, urlopen

import customtkinter as ctk
import qrcode
import yt_dlp
from PIL import Image, ImageOps

from iconset import IconFactory
from mobile.server import DEFAULT_PORT as MOBILE_PORT
from mobile.server import HOST as MOBILE_HOST
from mobile.server import Server as MobileServer
from mobile.server import State as MobileState
from mobile.server import normalize_proxy
from mobile.server import active_proxy


APP_NAME = "VideoGrab"
APP_VERSION = "2.3.2"


def bundled_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def app_data_dir() -> Path:
    override = os.environ.get("VIDEOGRAB_DATA_DIR")
    if override:
        path = Path(override)
    else:
        path = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_download_dir() -> Path:
    path = Path.home() / "Downloads" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_selector(height: int | None) -> str:
    limit = f"[height<={height}]" if height else ""
    return f"bv*{limit}+ba/b{limit}"


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return fallback


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


TEXT = {
    "zh": {
        "tagline": "下载 · 解析 · 创作",
        "download": "下载",
        "browser": "浏览器",
        "history": "历史记录",
        "settings": "设置",
        "browser_session": "浏览器登录状态",
        "browser_session_help": "登录后可访问受限内容。",
        "open_browser": "打开浏览器",
        "download_title": "下载媒体",
        "download_subtitle": "从常见视频网站和网页链接保存视频、封面或 MP3。",
        "url_label": "输入视频链接",
        "url_placeholder": "粘贴 YouTube、B站、抖音、TikTok、Instagram 或其他视频页面链接",
        "paste": "粘贴",
        "analyze": "解析",
        "analyzing": "正在解析…",
        "output": "输出内容",
        "video": "视频",
        "cover": "封面",
        "quality": "画质",
        "save_to": "保存位置",
        "change": "更改",
        "ready_title": "准备解析",
        "ready_help": "输入视频链接即可开始。",
        "analysis_progress": "正在读取媒体来源、格式、封面与元数据…",
        "analysis_complete": "解析完成",
        "formats_found": "发现 {count} 种格式",
        "duration": "时长",
        "source": "来源",
        "available": "可用内容",
        "download_selected": "下载所选内容",
        "cancel": "取消",
        "open_folder": "打开文件夹",
        "recent_downloads": "最近下载",
        "clear": "清空",
        "no_recent": "暂无下载记录",
        "ready": "就绪",
        "no_active": "暂无活动下载",
        "downloading": "下载中",
        "preparing": "正在准备下载…",
        "download_complete": "下载完成",
        "download_cancelled": "下载已取消",
        "processing_failed": "处理失败",
        "link_invalid": "请输入以 http:// 或 https:// 开头的有效视频链接。",
        "choose_content": "请至少选择视频、封面或 MP3 中的一项。",
        "folder_error": "无法创建保存文件夹：\n{error}",
        "open_after_question": "下载已经完成。是否打开保存文件夹？",
        "copyright": "请只下载你拥有版权或已获得许可的内容；本工具不绕过 DRM。",
        "browser_title": "浏览器登录状态",
        "browser_subtitle": "需要登录的视频页面，可读取本机浏览器的登录状态后解析。",
        "browser_none": "不使用",
        "browser_edge": "Microsoft Edge",
        "browser_chrome": "Google Chrome",
        "browser_tip_title": "什么时候需要使用？",
        "browser_tip": "遇到仅登录可见、年龄验证或个人订阅内容时，选择已登录的浏览器。浏览器数据只在本机读取。建议先关闭对应浏览器再开始解析。",
        "use_this_browser": "使用此浏览器",
        "selected": "已选择",
        "history_title": "下载历史",
        "history_subtitle": "查看最近保存的媒体，并快速打开所在文件夹。",
        "clear_history": "清空历史",
        "open_location": "打开位置",
        "settings_title": "设置",
        "settings_subtitle": "自定义 VideoGrab 的下载与处理方式。",
        "language": "界面语言",
        "language_help": "选择应用显示语言，切换后立即生效。",
        "font_size": "界面字号",
        "font_size_help": "苹方 PingFang SC / 微软雅黑 UI · 调整应用内文字整体大小，切换后立即生效。",
        "font_small": "小 90%",
        "font_standard": "标准 100%",
        "font_large": "大 115%",
        "font_extra_large": "特大 130%",
        "chinese": "中文",
        "english": "English",
        "default_folder": "默认下载文件夹",
        "default_folder_help": "选择下载文件的默认保存位置。",
        "default_quality": "默认视频画质",
        "default_quality_help": "选择下载时优先使用的画质。",
        "filename_format": "文件命名格式",
        "filename_format_help": "定义下载文件的命名方式。",
        "filename_title_id": "标题 + 视频 ID",
        "filename_title": "仅标题",
        "filename_source_title": "来源 + 标题",
        "browser_source": "浏览器登录状态",
        "browser_source_help": "选择用于认证下载的浏览器。",
        "open_after": "下载完成后打开文件夹",
        "open_after_help": "下载完成时自动打开保存位置。",
        "keep_history": "保留下载历史",
        "keep_history_help": "在此设备上保存下载历史。",
        "media_parser": "媒体解析器",
        "media_parser_help": "当前 yt-dlp 版本：{version}",
        "check_version": "查看版本",
        "privacy": "隐私说明",
        "privacy_help": "浏览器数据和下载内容仅保留在你的设备上，VideoGrab 不会上传这些数据。",
        "restore_defaults": "恢复默认",
        "save_settings": "保存设置",
        "saved": "设置已保存",
        "version_message": "当前媒体解析器版本：{version}\n\n网站规则会变化，解析失效时通常需要更新 yt-dlp。",
        "confirm_clear": "确定要清空下载历史吗？",
        "media_unknown": "未命名媒体",
        "duration_unknown": "时长未知",
        "webpage": "网页",
        "recognized": "已识别 · {source} · {duration}",
        "processing": "正在处理{phase}…",
        "phase_video": "视频",
        "phase_cover": "封面",
        "download_progress": "{phase}下载中 {percent:.1f}%  {speed}  剩余 {eta}",
        "finishing": "{phase}下载完成，正在处理…",
        "failed_detail": "处理失败：{detail}\n\n链接可能需要登录、已被删除、受地区限制，或网站最近更改了接口。",
        "active_download": "正在下载：{title}",
        "saved_items": "已保存：{items}",
        "none": "无",
        "best": "最佳画质",
    },
    "en": {
        "tagline": "Download · Analyze · Create",
        "download": "Download",
        "browser": "Browser",
        "history": "History",
        "settings": "Settings",
        "browser_session": "Browser session",
        "browser_session_help": "Sign in to access restricted media.",
        "open_browser": "Open browser",
        "download_title": "Download media",
        "download_subtitle": "Save video, cover art, or MP3 from popular sites and media pages.",
        "url_label": "Enter a video URL",
        "url_placeholder": "Paste a YouTube, Bilibili, TikTok, Instagram, or other media-page URL",
        "paste": "Paste",
        "analyze": "Analyze",
        "analyzing": "Analyzing…",
        "output": "Output",
        "video": "Video",
        "cover": "Cover",
        "quality": "Quality",
        "save_to": "Destination",
        "change": "Change",
        "ready_title": "Ready to analyze",
        "ready_help": "Enter a video URL to get started.",
        "analysis_progress": "Reading source, formats, cover, and metadata…",
        "analysis_complete": "Analysis complete",
        "formats_found": "{count} formats found",
        "duration": "Duration",
        "source": "Source",
        "available": "Available",
        "download_selected": "Download selected",
        "cancel": "Cancel",
        "open_folder": "Open folder",
        "recent_downloads": "Recent downloads",
        "clear": "Clear",
        "no_recent": "No downloads yet",
        "ready": "Ready",
        "no_active": "No active downloads",
        "downloading": "Downloading",
        "preparing": "Preparing download…",
        "download_complete": "Download complete",
        "download_cancelled": "Download cancelled",
        "processing_failed": "Processing failed",
        "link_invalid": "Enter a valid video URL beginning with http:// or https://.",
        "choose_content": "Select at least one item: video, cover, or MP3.",
        "folder_error": "Could not create the destination folder:\n{error}",
        "open_after_question": "The download is complete. Open the destination folder?",
        "copyright": "Download only content you own or are permitted to save. VideoGrab does not bypass DRM.",
        "browser_title": "Browser session",
        "browser_subtitle": "Use a signed-in local browser session for media pages that require login.",
        "browser_none": "None",
        "browser_edge": "Microsoft Edge",
        "browser_chrome": "Google Chrome",
        "browser_tip_title": "When should I use this?",
        "browser_tip": "Select a signed-in browser for login-only, age-gated, or subscribed content. Browser data is read locally. Close that browser before analyzing for the best result.",
        "use_this_browser": "Use this browser",
        "selected": "Selected",
        "history_title": "Download history",
        "history_subtitle": "Review recently saved media and open its destination folder.",
        "clear_history": "Clear history",
        "open_location": "Open location",
        "settings_title": "Settings",
        "settings_subtitle": "Customize how VideoGrab downloads and processes media.",
        "language": "Interface language",
        "language_help": "Choose the display language. Changes apply immediately.",
        "font_size": "Interface text size",
        "font_size_help": "PingFang SC / Microsoft YaHei UI · Adjust app text immediately.",
        "font_small": "Small 90%",
        "font_standard": "Standard 100%",
        "font_large": "Large 115%",
        "font_extra_large": "Extra large 130%",
        "chinese": "中文",
        "english": "English",
        "default_folder": "Default download folder",
        "default_folder_help": "Choose where downloads are saved by default.",
        "default_quality": "Default video quality",
        "default_quality_help": "Select the preferred quality for downloads.",
        "filename_format": "Filename format",
        "filename_format_help": "Choose how downloaded files are named.",
        "filename_title_id": "Title + video ID",
        "filename_title": "Title only",
        "filename_source_title": "Source + title",
        "browser_source": "Browser session source",
        "browser_source_help": "Choose a browser for authenticated downloads.",
        "open_after": "Open folder after completion",
        "open_after_help": "Open the destination automatically when a download finishes.",
        "keep_history": "Keep download history",
        "keep_history_help": "Save download history on this device.",
        "media_parser": "Media parser",
        "media_parser_help": "Current yt-dlp version: {version}",
        "check_version": "View version",
        "privacy": "Privacy",
        "privacy_help": "Browser data and downloaded content stay on your device. VideoGrab does not upload them.",
        "restore_defaults": "Restore defaults",
        "save_settings": "Save settings",
        "saved": "Settings saved",
        "version_message": "Current media parser version: {version}\n\nSite rules change over time; updating yt-dlp usually fixes new extraction issues.",
        "confirm_clear": "Clear all download history?",
        "media_unknown": "Untitled media",
        "duration_unknown": "Unknown duration",
        "webpage": "Web page",
        "recognized": "Recognized · {source} · {duration}",
        "processing": "Processing {phase}…",
        "phase_video": "video",
        "phase_cover": "cover",
        "download_progress": "Downloading {phase} {percent:.1f}%  {speed}  ETA {eta}",
        "finishing": "{phase} download complete; processing…",
        "failed_detail": "Processing failed: {detail}\n\nThe link may require login, be unavailable, region-limited, or the site may have changed.",
        "active_download": "Downloading: {title}",
        "saved_items": "Saved: {items}",
        "none": "None",
        "best": "Best quality",
    },
}

TEXT["zh"].update({
    "mobile_pairing": "手机配对",
    "mobile_running": "手机服务正在运行",
    "mobile_title": "连接你的 iPhone",
    "mobile_help": "保持电脑和手机处于同一个 Wi-Fi，然后使用 iPhone 相机扫描二维码。",
    "mobile_open": "在电脑打开",
    "mobile_copy": "复制地址",
    "mobile_copied": "连接地址已复制。",
    "mobile_save": "下载文件保存在：下载\\VideoGrab-Mobile",
    "mobile_keep_open": "关闭 VideoGrab 主客户端会断开手机连接。",
    "mobile_port_error": "无法启动手机服务。端口 {port} 可能正被其他程序占用。",
    "online_title": "公开网页",
    "online_starting": "正在创建安全的在线地址…",
    "online_running": "公开网页正在运行",
    "online_help": "把地址或二维码发给任何人，对方打开浏览器即可使用。电脑必须保持开机并运行 VideoGrab。",
    "online_open": "打开网页",
    "online_copy": "复制公开地址",
    "online_stop": "停止公开访问",
    "online_stopped": "公开访问已停止",
    "online_failed": "无法创建公开网页，请检查网络后重试。",
    "online_missing": "缺少在线连接组件，请重新安装最新版 VideoGrab。",
    "online_limits": "公开模式不读取浏览器登录状态；每位访客每小时最多 3 个任务，文件保留 2 小时。",
    "proxy_title": "网络代理",
    "proxy_help": "YouTube 提示验证时，填写本机代理地址；留空则直连。",
    "proxy_error": "代理地址格式不正确，例如 http://127.0.0.1:7897",
    "youtube_bot_error": "YouTube 要求验证当前网络。请在“设置 → 网络代理”填写正在运行的代理地址，再重新解析；也可使用已登录的浏览器状态。",
    "proxy_offline_error": "设置的本机代理目前没有运行。请先启动代理，再重新解析 YouTube 链接。",
})
TEXT["en"].update({
    "mobile_pairing": "Mobile pairing",
    "mobile_running": "Mobile service is running",
    "mobile_title": "Connect your iPhone",
    "mobile_help": "Keep the computer and iPhone on the same Wi-Fi, then scan this QR code with Camera.",
    "mobile_open": "Open on computer",
    "mobile_copy": "Copy address",
    "mobile_copied": "Connection address copied.",
    "mobile_save": "Downloads are saved in Downloads\\VideoGrab-Mobile",
    "mobile_keep_open": "Closing VideoGrab disconnects the phone.",
    "mobile_port_error": "Could not start the mobile service. Port {port} may already be in use.",
    "online_title": "Public workspace",
    "online_starting": "Creating a secure public address…",
    "online_running": "Public workspace is online",
    "online_help": "Share the address or QR code with anyone. Keep this computer on and VideoGrab running.",
    "online_open": "Open website",
    "online_copy": "Copy public address",
    "online_stop": "Stop public access",
    "online_stopped": "Public access stopped",
    "online_failed": "Could not create the public website. Check your network and try again.",
    "online_missing": "The online connection component is missing. Reinstall the latest VideoGrab.",
    "online_limits": "Public mode disables browser sessions, allows 3 jobs per visitor per hour, and retains files for 2 hours.",
    "proxy_title": "Network proxy",
    "proxy_help": "Enter a running proxy address when YouTube requests verification; leave blank for a direct connection.",
    "proxy_error": "Invalid proxy address. Example: http://127.0.0.1:7897",
    "youtube_bot_error": "YouTube is asking this network to verify itself. Set a working proxy under Settings → Network proxy and retry, or use a signed-in browser session.",
    "proxy_offline_error": "The configured local proxy is not running. Start it, then retry the YouTube link.",
})


QUALITY_HEIGHTS = {"best": None, "2160": 2160, "1440": 1440, "1080": 1080, "720": 720, "480": 480}
QUALITY_LABELS = {
    "zh": {"best": "最佳画质", "2160": "4K (2160p)", "1440": "2K (1440p)", "1080": "1080p", "720": "720p", "480": "480p"},
    "en": {"best": "Best quality", "2160": "4K (2160p)", "1440": "2K (1440p)", "1080": "1080p", "720": "720p", "480": "480p"},
}


class VideoGrabApp:
    BG = "#F4F1EA"
    SURFACE = "#FFFFFF"
    SURFACE_ALT = "#FAF8F4"
    BORDER = "#DDD9D1"
    TEXT_COLOR = "#141414"
    MUTED = "#77736C"
    ACCENT = "#FF3D16"
    ACCENT_HOVER = "#E83210"
    BLUE = "#2563EB"
    GREEN = "#16A34A"
    WARNING = "#F59E0B"

    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1320x820")
        self.root.minsize(1080, 700)
        self.root.configure(fg_color=self.BG)
        try:
            self.root.iconbitmap(str(bundled_path("assets", "videograb.ico")))
        except OSError:
            pass

        self.settings_path = app_data_dir() / "settings.json"
        self.history_path = app_data_dir() / "history.json"
        defaults = self.default_settings()
        stored = read_json(self.settings_path, {})
        self.settings_data = defaults | (stored if isinstance(stored, dict) else {})
        if self.settings_data.get("language") not in ("zh", "en"):
            self.settings_data["language"] = "zh"
        if self.settings_data.get("font_scale") not in (90, 100, 115, 130):
            self.settings_data["font_scale"] = 100
        self.language = self.settings_data["language"]
        self.icons = IconFactory()
        loaded_history = read_json(self.history_path, [])
        self.history_data = loaded_history if isinstance(loaded_history, list) else []

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.busy = False
        self.busy_kind = ""
        self.current_page = "download"
        self.analysis_mode = "ready"
        self.analysis_info: dict | None = None
        self.thumbnail_bytes: bytes | None = None
        self._thumbnail_image = None
        self._logo_image = None
        self.mobile_state: MobileState | None = None
        self.mobile_server: MobileServer | None = None
        self.mobile_thread: threading.Thread | None = None
        self.mobile_popup: ctk.CTkToplevel | None = None
        self._mobile_qr_image = None
        self.online_popup: ctk.CTkToplevel | None = None
        self.online_process: subprocess.Popen[str] | None = None
        self.online_url = ""
        self._online_qr_image = None
        self._online_status_label = None
        self._online_address = None
        self._online_qr_label = None
        self._online_open_button = None
        self._online_copy_button = None

        self.url = ctk.StringVar(value="")
        self.output_dir = ctk.StringVar(value=str(self.settings_data["output_dir"]))
        self.proxy_url = ctk.StringVar(value=str(self.settings_data.get("proxy", "")))
        self.download_video = ctk.BooleanVar(value=True)
        self.download_cover = ctk.BooleanVar(value=False)
        self.download_mp3 = ctk.BooleanVar(value=False)
        self.progress = ctk.DoubleVar(value=0)
        self.status_text = ""
        self.media_title = ""

        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self._build_shell()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_events)

    @staticmethod
    def default_settings() -> dict:
        return {
            "language": "zh",
            "font_scale": 100,
            "output_dir": str(default_download_dir()),
            "quality": "1080",
            "browser": "",
            "proxy": "",
            "filename_format": "title_id",
            "open_after_complete": True,
            "keep_history": True,
        }

    def t(self, key: str, **values) -> str:
        text = TEXT[self.language].get(key, key)
        return text.format(**values) if values else text

    def _font(self, size: int, weight: str = "normal") -> ctk.CTkFont:
        family = "PingFang SC" if sys.platform == "darwin" else "Microsoft YaHei UI"
        scale = int(self.settings_data.get("font_scale", 100)) / 100
        return ctk.CTkFont(family=family, size=max(8, round(size * scale)), weight=weight)

    def _card(self, parent, **kwargs) -> ctk.CTkFrame:
        return ctk.CTkFrame(
            parent,
            fg_color=kwargs.pop("fg_color", self.SURFACE),
            border_width=kwargs.pop("border_width", 1),
            border_color=kwargs.pop("border_color", self.BORDER),
            corner_radius=kwargs.pop("corner_radius", 12),
            **kwargs,
        )

    def _build_shell(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

        shell = ctk.CTkFrame(self.root, fg_color=self.BG, corner_radius=0)
        shell.pack(fill="both", expand=True)

        font_scale = int(self.settings_data.get("font_scale", 100))
        sidebar_width = 196 + max(0, font_scale - 100) * 13 // 10
        self.sidebar = ctk.CTkFrame(shell, width=sidebar_width, fg_color=self.SURFACE, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.main = ctk.CTkFrame(shell, fg_color=self.BG, corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(22, 28))
        brand_top = ctk.CTkFrame(brand, fg_color="transparent")
        brand_top.pack(fill="x")
        logo_path = bundled_path("assets", "logo.png")
        if logo_path.exists():
            image = Image.open(logo_path).convert("RGBA")
            self._logo_image = ctk.CTkImage(light_image=image, dark_image=image, size=(44, 44))
            ctk.CTkLabel(brand_top, text="", image=self._logo_image, width=44).pack(side="left")
        ctk.CTkLabel(brand_top, text="VideoGrab", text_color=self.TEXT_COLOR, font=self._font(19, "bold")).pack(side="left", padx=(8, 0))
        tagline_indent = 0
        brand_meta = ctk.CTkFrame(brand, height=38, fg_color="transparent")
        brand_meta.pack(fill="x", pady=(1, 0))
        brand_meta.pack_propagate(False)
        ctk.CTkLabel(brand_meta, text=self.t("tagline"), text_color=self.MUTED, font=self._font(9), anchor="w").pack(side="left", padx=(tagline_indent, 0))
        mobile_badge = ctk.CTkFrame(brand_meta, width=38, height=38, fg_color="transparent")
        mobile_badge.pack(side="right")
        mobile_badge.pack_propagate(False)
        ctk.CTkButton(
            mobile_badge,
            text="",
            image=self.icons.get("mobile", self.TEXT_COLOR, 18),
            command=self.open_mobile_pairing,
            width=32,
            height=32,
            corner_radius=16,
            fg_color=self.SURFACE_ALT,
            hover_color="#F0E7E1",
            border_width=1,
            border_color=self.BORDER,
        ).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(mobile_badge, text="", width=8, height=8, corner_radius=4, fg_color=self.ACCENT).place(relx=0.78, rely=0.16, anchor="center")
        online_badge = ctk.CTkFrame(brand_meta, width=38, height=38, fg_color="transparent")
        online_badge.pack(side="right")
        online_badge.pack_propagate(False)
        ctk.CTkButton(
            online_badge,
            text="",
            image=self.icons.get("browser", self.TEXT_COLOR, 18),
            command=self.open_online_portal,
            width=32,
            height=32,
            corner_radius=16,
            fg_color=self.SURFACE_ALT,
            hover_color="#F0E7E1",
            border_width=1,
            border_color=self.BORDER,
        ).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(online_badge, text="", width=8, height=8, corner_radius=4, fg_color=self.GREEN).place(relx=0.78, rely=0.16, anchor="center")

        self.nav_buttons = {}
        nav_data = [("download", "download"), ("browser", "browser"), ("history", "history"), ("settings", "settings")]
        for page, icon_name in nav_data:
            active = page == self.current_page
            button = ctk.CTkButton(
                self.sidebar,
                text=self.t(page),
                image=self.icons.get(icon_name, self.ACCENT if active else self.TEXT_COLOR, 20),
                compound="left",
                command=lambda page=page: self._show_page(page),
                height=44,
                corner_radius=9,
                anchor="w",
                fg_color="#FFF1EC" if active else "transparent",
                hover_color="#F8EEE9",
                text_color=self.ACCENT if active else self.TEXT_COLOR,
                font=self._font(12, "bold" if active else "normal"),
            )
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[page] = button

        session = self._card(self.sidebar, fg_color=self.SURFACE_ALT)
        session.pack(side="bottom", fill="x", padx=12, pady=16)
        ctk.CTkLabel(session, text=self.t("browser_session"), image=self.icons.get("session", self.TEXT_COLOR, 18), compound="left", text_color=self.TEXT_COLOR, font=self._font(11, "bold")).pack(anchor="w", padx=12, pady=(12, 3))
        ctk.CTkLabel(session, text=self.t("browser_session_help"), text_color=self.MUTED, font=self._font(9), wraplength=142, justify="left").pack(anchor="w", padx=12)
        ctk.CTkButton(session, text=self.t("open_browser"), command=self.open_browser, height=30, corner_radius=7, fg_color=self.SURFACE, hover_color="#F0ECE5", border_width=1, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(10)).pack(fill="x", padx=10, pady=10)

        self.page_host = ctk.CTkFrame(self.main, fg_color="transparent")
        self.page_host.pack(fill="both", expand=True, padx=28, pady=(24, 14))
        self._show_page(self.current_page, update_nav=False)

        statusbar = ctk.CTkFrame(self.main, height=30, fg_color=self.SURFACE, corner_radius=0)
        statusbar.pack(fill="x", side="bottom")
        statusbar.pack_propagate(False)
        ctk.CTkLabel(statusbar, text=self.t("ready"), image=self.icons.get("success", self.MUTED, 14), compound="left", text_color=self.MUTED, font=self._font(9)).pack(side="left", padx=18)
        ctk.CTkLabel(statusbar, text=self.t("no_active") if not self.busy else self.t("downloading"), text_color=self.MUTED, font=self._font(9)).pack(side="right", padx=18)

    def _ensure_mobile_server(self) -> bool:
        if self.mobile_server is None:
            try:
                self.mobile_state = MobileState(MOBILE_PORT)
                self.mobile_server = MobileServer((MOBILE_HOST, MOBILE_PORT), self.mobile_state)
            except OSError:
                self.mobile_state = None
                self.mobile_server = None
                messagebox.showerror(APP_NAME, self.t("mobile_port_error", port=MOBILE_PORT))
                return False
            self.mobile_thread = threading.Thread(
                target=self.mobile_server.serve_forever,
                kwargs={"poll_interval": 0.5},
                daemon=True,
            )
            self.mobile_thread.start()
        return self.mobile_state is not None

    def open_mobile_pairing(self) -> None:
        if not self._ensure_mobile_server():
            return

        if self.mobile_popup is not None and self.mobile_popup.winfo_exists():
            self.mobile_popup.deiconify()
            self.mobile_popup.lift()
            self.mobile_popup.focus_force()
            return
        if self.mobile_state is None:
            return

        popup = ctk.CTkToplevel(self.root)
        self.mobile_popup = popup
        popup.title(self.t("mobile_pairing"))
        popup.geometry("520x690")
        popup.minsize(470, 620)
        popup.configure(fg_color=self.BG)
        popup.transient(self.root)
        popup.protocol("WM_DELETE_WINDOW", popup.withdraw)
        try:
            popup.iconbitmap(str(bundled_path("assets", "videograb.ico")))
        except OSError:
            pass

        shell = self._card(popup, corner_radius=18)
        shell.pack(fill="both", expand=True, padx=24, pady=24)
        ctk.CTkLabel(
            shell,
            text=f"●  {self.t('mobile_running')}",
            text_color=self.GREEN,
            font=self._font(10, "bold"),
        ).pack(anchor="w", padx=28, pady=(26, 0))
        ctk.CTkLabel(shell, text=self.t("mobile_title"), text_color=self.TEXT_COLOR, font=self._font(25, "bold")).pack(anchor="w", padx=28, pady=(13, 3))
        ctk.CTkLabel(
            shell,
            text=self.t("mobile_help"),
            text_color=self.MUTED,
            font=self._font(10),
            justify="left",
            wraplength=405,
        ).pack(anchor="w", padx=28)

        qr = qrcode.QRCode(version=None, box_size=8, border=3)
        qr.add_data(self.mobile_state.share_url)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color=self.TEXT_COLOR, back_color=self.BG).convert("RGB")
        self._mobile_qr_image = ctk.CTkImage(light_image=qr_image, dark_image=qr_image, size=(250, 250))
        qr_frame = ctk.CTkFrame(shell, width=270, height=270, fg_color=self.BG, corner_radius=16)
        qr_frame.pack(pady=(20, 12))
        qr_frame.pack_propagate(False)
        ctk.CTkLabel(qr_frame, text="", image=self._mobile_qr_image).place(relx=0.5, rely=0.5, anchor="center")

        address = ctk.CTkEntry(
            shell,
            height=38,
            corner_radius=9,
            fg_color=self.SURFACE_ALT,
            border_color=self.BORDER,
            text_color=self.MUTED,
            justify="center",
            font=self._font(8),
        )
        address.insert(0, self.mobile_state.share_url)
        address.configure(state="readonly")
        address.pack(fill="x", padx=28)

        actions = ctk.CTkFrame(shell, fg_color="transparent")
        actions.pack(fill="x", padx=28, pady=(12, 0))
        ctk.CTkButton(
            actions,
            text=self.t("mobile_open"),
            command=self._open_mobile_local,
            height=42,
            corner_radius=9,
            fg_color=self.TEXT_COLOR,
            hover_color="#333330",
            font=self._font(10, "bold"),
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(
            actions,
            text=self.t("mobile_copy"),
            command=self._copy_mobile_address,
            height=42,
            corner_radius=9,
            fg_color=self.SURFACE_ALT,
            hover_color="#EFE9E1",
            border_width=1,
            border_color=self.BORDER,
            text_color=self.TEXT_COLOR,
            font=self._font(10, "bold"),
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))
        ctk.CTkLabel(shell, text=self.t("mobile_save"), text_color=self.MUTED, font=self._font(8)).pack(anchor="w", padx=28, pady=(16, 0))
        ctk.CTkLabel(shell, text=self.t("mobile_keep_open"), text_color=self.ACCENT, font=self._font(8, "bold")).pack(anchor="w", padx=28, pady=(4, 18))
        popup.after(100, popup.focus_force)

    def _open_mobile_local(self) -> None:
        if self.mobile_state:
            webbrowser.open(f"http://127.0.0.1:{self.mobile_state.port}/?token={self.mobile_state.token}")

    def _copy_mobile_address(self) -> None:
        if not self.mobile_state:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.mobile_state.share_url)
        self.root.update()
        messagebox.showinfo(APP_NAME, self.t("mobile_copied"))

    def open_online_portal(self) -> None:
        if not self._ensure_mobile_server():
            return
        if self.online_popup is not None and self.online_popup.winfo_exists():
            self.online_popup.deiconify()
            self.online_popup.lift()
            self.online_popup.focus_force()
            if not self.online_url and not (self.online_process and self.online_process.poll() is None):
                self._start_online_tunnel()
            return

        popup = ctk.CTkToplevel(self.root)
        self.online_popup = popup
        popup.title(self.t("online_title"))
        popup.geometry("520x690")
        popup.minsize(470, 620)
        popup.configure(fg_color=self.BG)
        popup.transient(self.root)
        popup.protocol("WM_DELETE_WINDOW", popup.withdraw)
        try:
            popup.iconbitmap(str(bundled_path("assets", "videograb.ico")))
        except OSError:
            pass

        shell = self._card(popup, corner_radius=18)
        shell.pack(fill="both", expand=True, padx=24, pady=24)
        self._online_status_label = ctk.CTkLabel(shell, text=f"●  {self.t('online_starting')}", text_color=self.ACCENT, font=self._font(10, "bold"))
        self._online_status_label.pack(anchor="w", padx=28, pady=(26, 0))
        ctk.CTkLabel(shell, text=self.t("online_title"), text_color=self.TEXT_COLOR, font=self._font(25, "bold")).pack(anchor="w", padx=28, pady=(13, 3))
        ctk.CTkLabel(shell, text=self.t("online_help"), text_color=self.MUTED, font=self._font(10), justify="left", wraplength=405).pack(anchor="w", padx=28)

        qr_frame = ctk.CTkFrame(shell, width=270, height=270, fg_color=self.BG, corner_radius=16)
        qr_frame.pack(pady=(20, 12))
        qr_frame.pack_propagate(False)
        self._online_qr_label = ctk.CTkLabel(qr_frame, text="…", text_color=self.MUTED, font=self._font(26, "bold"))
        self._online_qr_label.place(relx=0.5, rely=0.5, anchor="center")

        self._online_address = ctk.CTkEntry(shell, height=38, corner_radius=9, fg_color=self.SURFACE_ALT, border_color=self.BORDER, text_color=self.MUTED, justify="center", font=self._font(8))
        self._online_address.insert(0, self.t("online_starting"))
        self._online_address.configure(state="readonly")
        self._online_address.pack(fill="x", padx=28)

        actions = ctk.CTkFrame(shell, fg_color="transparent")
        actions.pack(fill="x", padx=28, pady=(12, 0))
        self._online_open_button = ctk.CTkButton(actions, text=self.t("online_open"), command=self._open_online_url, state="disabled", height=42, corner_radius=9, fg_color=self.TEXT_COLOR, hover_color="#333330", font=self._font(10, "bold"))
        self._online_open_button.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._online_copy_button = ctk.CTkButton(actions, text=self.t("online_copy"), command=self._copy_online_url, state="disabled", height=42, corner_radius=9, fg_color=self.SURFACE_ALT, hover_color="#EFE9E1", border_width=1, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(10, "bold"))
        self._online_copy_button.pack(side="left", fill="x", expand=True, padx=(5, 0))
        ctk.CTkButton(shell, text=self.t("online_stop"), command=self._stop_online_tunnel, height=34, corner_radius=8, fg_color="transparent", hover_color="#F8EEE9", text_color=self.ACCENT, font=self._font(9, "bold")).pack(fill="x", padx=28, pady=(10, 0))
        ctk.CTkLabel(shell, text=self.t("online_limits"), text_color=self.MUTED, font=self._font(8), justify="left", wraplength=405).pack(anchor="w", padx=28, pady=(12, 18))
        popup.after(100, popup.focus_force)
        self._start_online_tunnel()

    def _start_online_tunnel(self) -> None:
        executable = bundled_path("vendor", "cloudflared.exe")
        if not executable.is_file():
            self._online_failed(self.t("online_missing"))
            return
        if self.online_process and self.online_process.poll() is None:
            return
        self.online_url = ""
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            self.online_process = subprocess.Popen(
                [str(executable), "tunnel", "--url", f"http://127.0.0.1:{MOBILE_PORT}", "--no-autoupdate"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=flags,
            )
        except OSError:
            self._online_failed(self.t("online_failed"))
            return
        threading.Thread(target=self._read_tunnel_output, daemon=True).start()

    def _read_tunnel_output(self) -> None:
        process = self.online_process
        if not process or not process.stdout:
            return
        found = False
        for line in process.stdout:
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line, re.IGNORECASE)
            if match and not found:
                found = True
                base = match.group(0).rstrip("/")
                token = self.mobile_state.token if self.mobile_state else ""
                url = f"{base}/?token={token}&mode=public"
                self.root.after(0, lambda value=url: self._online_ready(value))
        if not found and not self.online_url:
            self.root.after(0, lambda: self._online_failed(self.t("online_failed")))

    def _online_ready(self, url: str) -> None:
        self.online_url = url
        if self._online_status_label:
            self._online_status_label.configure(text=f"●  {self.t('online_running')}", text_color=self.GREEN)
        qr = qrcode.QRCode(version=None, box_size=8, border=3)
        qr.add_data(url)
        qr.make(fit=True)
        image = qr.make_image(fill_color=self.TEXT_COLOR, back_color=self.BG).convert("RGB")
        self._online_qr_image = ctk.CTkImage(light_image=image, dark_image=image, size=(250, 250))
        if self._online_qr_label:
            self._online_qr_label.configure(text="", image=self._online_qr_image)
        if self._online_address:
            self._online_address.configure(state="normal")
            self._online_address.delete(0, "end")
            self._online_address.insert(0, url)
            self._online_address.configure(state="readonly")
        if self._online_open_button:
            self._online_open_button.configure(state="normal")
        if self._online_copy_button:
            self._online_copy_button.configure(state="normal")

    def _online_failed(self, message: str) -> None:
        if self._online_status_label:
            self._online_status_label.configure(text=f"●  {message}", text_color=self.ACCENT)
        if self._online_address:
            self._online_address.configure(state="normal")
            self._online_address.delete(0, "end")
            self._online_address.insert(0, message)
            self._online_address.configure(state="readonly")

    def _open_online_url(self) -> None:
        if self.online_url:
            webbrowser.open(self.online_url)

    def _copy_online_url(self) -> None:
        if not self.online_url:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.online_url)
        self.root.update()
        messagebox.showinfo(APP_NAME, self.t("online_copy"))

    def _stop_online_tunnel(self) -> None:
        process = self.online_process
        self.online_process = None
        self.online_url = ""
        if process and process.poll() is None:
            process.terminate()
        if self._online_status_label:
            self._online_status_label.configure(text=f"●  {self.t('online_stopped')}", text_color=self.MUTED)
        if self._online_open_button:
            self._online_open_button.configure(state="disabled")
        if self._online_copy_button:
            self._online_copy_button.configure(state="disabled")

    def _on_close(self) -> None:
        self.cancel_event.set()
        self._stop_online_tunnel()
        if self.mobile_server is not None:
            self.mobile_server.shutdown()
            self.mobile_server.server_close()
            self.mobile_server = None
        self.root.destroy()

    def _show_page(self, page: str, update_nav: bool = True) -> None:
        self.current_page = page
        if update_nav:
            for name, button in self.nav_buttons.items():
                active = name == page
                button.configure(
                    fg_color="#FFF1EC" if active else "transparent",
                    text_color=self.ACCENT if active else self.TEXT_COLOR,
                    image=self.icons.get(name, self.ACCENT if active else self.TEXT_COLOR, 20),
                    font=self._font(12, "bold" if active else "normal"),
                )
        for child in self.page_host.winfo_children():
            child.destroy()
        {"download": self._build_download_page, "browser": self._build_browser_page, "history": self._build_history_page, "settings": self._build_settings_page}[page]()

    def _page_heading(self, title: str, subtitle: str, action: tuple[str, object] | None = None) -> None:
        row = ctk.CTkFrame(self.page_host, fg_color="transparent")
        row.pack(fill="x", pady=(0, 18))
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.pack(side="left")
        ctk.CTkLabel(text, text=title, text_color=self.TEXT_COLOR, font=self._font(23, "bold")).pack(anchor="w")
        ctk.CTkLabel(text, text=subtitle, text_color=self.MUTED, font=self._font(11)).pack(anchor="w", pady=(3, 0))
        if action:
            ctk.CTkButton(row, text=action[0], command=action[1], width=112, height=36, corner_radius=8, fg_color=self.SURFACE, hover_color="#F0ECE5", border_width=1, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(10)).pack(side="right", pady=5)

    def _build_download_page(self) -> None:
        self._page_heading(self.t("download_title"), self.t("download_subtitle"))

        url_card = self._card(self.page_host)
        url_card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(url_card, text=self.t("url_label"), text_color=self.TEXT_COLOR, font=self._font(11, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
        url_row = ctk.CTkFrame(url_card, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(0, 14))
        url_row.grid_columnconfigure(0, weight=1)
        self.url_entry = ctk.CTkEntry(url_row, textvariable=self.url, height=42, corner_radius=8, fg_color=self.SURFACE_ALT, border_color=self.BORDER, text_color=self.TEXT_COLOR, placeholder_text=self.t("url_placeholder"), placeholder_text_color="#AAA59D", font=self._font(11))
        self.url_entry.grid(row=0, column=0, sticky="ew")
        self.url_entry.bind("<Return>", lambda _event: self.analyze())
        ctk.CTkButton(url_row, text=self.t("paste"), image=self.icons.get("clipboard", self.TEXT_COLOR, 17), compound="left", command=self.paste_url, width=82, height=42, corner_radius=8, fg_color=self.SURFACE, hover_color="#F0ECE5", border_width=1, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(10)).grid(row=0, column=1, padx=(8, 0))
        self.analyze_button = ctk.CTkButton(url_row, text=self.t("analyzing") if self.busy_kind == "analyze" else self.t("analyze"), image=self.icons.get("analyze", "#FFFFFF", 18), compound="left", command=self.analyze, width=104, height=42, corner_radius=8, fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER, text_color="white", font=self._font(11, "bold"), state="disabled" if self.busy else "normal")
        self.analyze_button.grid(row=0, column=2, padx=(8, 0))

        controls = ctk.CTkFrame(self.page_host, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 12))
        controls.grid_columnconfigure(0, weight=3)
        controls.grid_columnconfigure(1, weight=1)
        controls.grid_columnconfigure(2, weight=4)

        output = self._card(controls)
        output.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ctk.CTkLabel(output, text=self.t("output"), text_color=self.MUTED, font=self._font(9)).pack(anchor="w", padx=12, pady=(9, 4))
        picks = ctk.CTkFrame(output, fg_color="transparent")
        picks.pack(fill="x", padx=12, pady=(0, 9))
        style = dict(fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER, border_color="#C9C4BB", text_color=self.TEXT_COLOR, font=self._font(10), checkbox_width=18, checkbox_height=18)
        media_widgets = []
        for icon_name, label, variable in (("video", self.t("video"), self.download_video), ("cover", self.t("cover"), self.download_cover), ("mp3", "MP3", self.download_mp3)):
            item = ctk.CTkFrame(picks, fg_color="transparent")
            item.pack(side="left", padx=(0 if not media_widgets else 14, 0))
            ctk.CTkLabel(item, text="", image=self.icons.get(icon_name, self.TEXT_COLOR, 17), width=18).pack(side="left", padx=(0, 4))
            check = ctk.CTkCheckBox(item, text=label, variable=variable, **style)
            check.pack(side="left")
            media_widgets.append(check)
        self.video_check, self.cover_check, self.mp3_check = media_widgets

        quality = self._card(controls)
        quality.grid(row=0, column=1, sticky="nsew", padx=6)
        ctk.CTkLabel(quality, text=self.t("quality"), text_color=self.MUTED, font=self._font(9)).pack(anchor="w", padx=12, pady=(9, 4))
        quality_values = list(QUALITY_LABELS[self.language].values())
        selected_quality = QUALITY_LABELS[self.language].get(self.settings_data["quality"], quality_values[0])
        self.quality_box = ctk.CTkComboBox(quality, values=quality_values, command=self._on_quality_changed, height=34, corner_radius=7, fg_color=self.SURFACE_ALT, border_color=self.BORDER, button_color=self.SURFACE_ALT, button_hover_color="#EEE9E1", dropdown_fg_color=self.SURFACE, dropdown_hover_color="#F5EFEA", text_color=self.TEXT_COLOR, font=self._font(10), state="readonly")
        self.quality_box.set(selected_quality)
        self.quality_box.pack(fill="x", padx=10, pady=(0, 8))

        destination = self._card(controls)
        destination.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(destination, text=self.t("save_to"), text_color=self.MUTED, font=self._font(9)).pack(anchor="w", padx=12, pady=(9, 4))
        dest_row = ctk.CTkFrame(destination, fg_color="transparent")
        dest_row.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkEntry(dest_row, textvariable=self.output_dir, height=34, corner_radius=7, fg_color=self.SURFACE_ALT, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(9)).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dest_row, text=self.t("change"), command=self.choose_folder, width=66, height=34, corner_radius=7, fg_color=self.SURFACE, hover_color="#F0ECE5", border_width=1, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(9)).pack(side="left", padx=(6, 0))

        self.analysis_frame = self._card(self.page_host)
        self.analysis_frame.pack(fill="both", expand=True, pady=(0, 12))
        self._render_analysis_panel()

        bottom = ctk.CTkFrame(self.page_host, fg_color="transparent")
        bottom.pack(fill="x")
        self.download_button = ctk.CTkButton(bottom, text=self.t("download_selected"), image=self.icons.get("download", "#FFFFFF", 20), compound="left", command=self.download, height=44, width=220, corner_radius=9, fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER, text_color="white", font=self._font(12, "bold"), state="disabled" if self.busy else "normal")
        self.download_button.pack(side="left")
        self.cancel_button = ctk.CTkButton(bottom, text=self.t("cancel"), image=self.icons.get("cancel", self.TEXT_COLOR, 17), compound="left", command=self.cancel, height=44, width=96, corner_radius=9, fg_color=self.SURFACE, hover_color="#F0ECE5", border_width=1, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(10), state="normal" if self.busy else "disabled")
        self.cancel_button.pack(side="left", padx=(8, 0))
        ctk.CTkButton(bottom, text=self.t("open_folder"), image=self.icons.get("folder", self.TEXT_COLOR, 18), compound="left", command=self.open_folder, height=44, width=128, corner_radius=9, fg_color=self.SURFACE, hover_color="#F0ECE5", border_width=1, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(10)).pack(side="right")
        ctk.CTkLabel(bottom, text=self.t("copyright"), text_color="#98938B", font=self._font(8), wraplength=430, justify="right").pack(side="right", padx=(0, 14))

    def _render_analysis_panel(self) -> None:
        for child in self.analysis_frame.winfo_children():
            child.destroy()
        if self.analysis_mode == "ready":
            center = ctk.CTkFrame(self.analysis_frame, fg_color="transparent")
            center.place(relx=0.5, rely=0.5, anchor="center")
            ctk.CTkLabel(center, text="", image=self.icons.get("download", self.ACCENT, 54)).pack()
            ctk.CTkLabel(center, text=self.t("ready_title"), text_color=self.TEXT_COLOR, font=self._font(16, "bold")).pack(pady=(2, 3))
            ctk.CTkLabel(center, text=self.t("ready_help"), text_color=self.MUTED, font=self._font(10)).pack()
            return
        if self.analysis_mode == "analyzing":
            center = ctk.CTkFrame(self.analysis_frame, fg_color="transparent")
            center.place(relx=0.5, rely=0.48, anchor="center")
            ctk.CTkLabel(center, text="", image=self.icons.get("analyze", self.ACCENT, 44)).pack()
            ctk.CTkLabel(center, text=self.t("analyzing"), text_color=self.TEXT_COLOR, font=self._font(16, "bold")).pack(pady=(4, 4))
            ctk.CTkLabel(center, text=self.t("analysis_progress"), text_color=self.MUTED, font=self._font(10)).pack()
            bar = ctk.CTkProgressBar(center, width=260, height=5, fg_color="#EEEAE3", progress_color=self.ACCENT, mode="indeterminate")
            bar.pack(pady=(16, 0))
            bar.start()
            return

        info = self.analysis_info or {}
        body = ctk.CTkFrame(self.analysis_frame, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=14)
        body.grid_columnconfigure(1, weight=1)
        preview = ctk.CTkFrame(body, width=230, height=142, fg_color="#EEEAE4", corner_radius=9)
        preview.grid(row=0, column=0, rowspan=2, sticky="nsew")
        preview.grid_propagate(False)
        if self.thumbnail_bytes:
            try:
                image = Image.open(io.BytesIO(self.thumbnail_bytes)).convert("RGB")
                image = ImageOps.fit(image, (460, 284), Image.Resampling.LANCZOS)
                self._thumbnail_image = ctk.CTkImage(light_image=image, dark_image=image, size=(230, 142))
                ctk.CTkLabel(preview, text="", image=self._thumbnail_image).place(relx=0.5, rely=0.5, anchor="center")
            except OSError:
                ctk.CTkLabel(preview, text="4K", text_color=self.MUTED, font=self._font(24, "bold")).place(relx=0.5, rely=0.5, anchor="center")
        else:
            ctk.CTkLabel(preview, text="4K", text_color=self.MUTED, font=self._font(24, "bold")).place(relx=0.5, rely=0.5, anchor="center")

        details = ctk.CTkFrame(body, fg_color="transparent")
        details.grid(row=0, column=1, sticky="nsew", padx=(18, 0))
        title = str(info.get("title") or self.media_title or self.t("media_unknown"))
        ctk.CTkLabel(details, text=title, text_color=self.TEXT_COLOR, font=self._font(16, "bold"), anchor="w", wraplength=620, justify="left").pack(fill="x")
        source = str(info.get("source") or self.t("webpage"))
        duration = str(info.get("duration") or self.t("duration_unknown"))
        ctk.CTkLabel(details, text=f"{source}  ·  {duration}", text_color=self.MUTED, font=self._font(10), anchor="w").pack(fill="x", pady=(5, 10))
        badge_row = ctk.CTkFrame(details, fg_color="transparent")
        badge_row.pack(fill="x")
        ctk.CTkLabel(badge_row, text=self.t("analysis_complete"), image=self.icons.get("success", self.GREEN, 16), compound="left", text_color=self.GREEN, fg_color="#F0FBF3", corner_radius=6, font=self._font(10, "bold"), padx=10, pady=5).pack(side="left")
        ctk.CTkLabel(badge_row, text=self.t("formats_found", count=info.get("format_count", 0)), image=self.icons.get("info", self.BLUE, 16), compound="left", text_color=self.BLUE, fg_color="#EFF5FF", corner_radius=6, font=self._font(10), padx=10, pady=5).pack(side="left", padx=(8, 0))
        if self.analysis_mode == "downloading":
            ctk.CTkLabel(details, text=self.status_text or self.t("preparing"), text_color=self.ACCENT, font=self._font(10, "bold"), anchor="w").pack(fill="x", pady=(13, 5))
            bar = ctk.CTkProgressBar(details, height=7, fg_color="#EEEAE3", progress_color=self.ACCENT)
            bar.pack(fill="x")
            bar.set(max(0.0, min(1.0, self.progress.get() / 100)))
        elif self.analysis_mode == "complete":
            ctk.CTkLabel(details, text=self.t("download_complete"), image=self.icons.get("completed", self.GREEN, 17), compound="left", text_color=self.GREEN, font=self._font(11, "bold"), anchor="w").pack(fill="x", pady=(13, 0))

        formats = info.get("format_labels") or []
        strip = ctk.CTkFrame(body, fg_color=self.SURFACE_ALT, corner_radius=8)
        strip.grid(row=1, column=1, sticky="sew", padx=(18, 0), pady=(12, 0))
        ctk.CTkLabel(strip, text=self.t("available"), text_color=self.MUTED, font=self._font(9)).pack(side="left", padx=12, pady=9)
        ctk.CTkLabel(strip, text="  ·  ".join(formats[:7]) if formats else "MP4 · MP3 · JPG", text_color=self.TEXT_COLOR, font=self._font(10, "bold")).pack(side="left", pady=9)

        recent = ctk.CTkFrame(body, fg_color="transparent")
        recent.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ctk.CTkLabel(recent, text=self.t("recent_downloads"), text_color=self.MUTED, font=self._font(9, "bold")).pack(side="left")
        if self.history_data:
            last = self.history_data[0]
            ctk.CTkLabel(recent, text=f"{last.get('title', self.t('media_unknown'))}  ·  {last.get('items', '')}", text_color=self.TEXT_COLOR, font=self._font(9)).pack(side="left", padx=(12, 0))
        else:
            ctk.CTkLabel(recent, text=self.t("no_recent"), text_color="#A19C94", font=self._font(9)).pack(side="left", padx=(12, 0))

    def _build_browser_page(self) -> None:
        self._page_heading(self.t("browser_title"), self.t("browser_subtitle"))
        cards = ctk.CTkFrame(self.page_host, fg_color="transparent")
        cards.pack(fill="x")
        cards.grid_columnconfigure((0, 1), weight=1, uniform="browser")
        for column, (browser_key, name, mark) in enumerate((("edge", "Microsoft Edge", "e"), ("chrome", "Google Chrome", "G"))):
            selected = self.settings_data.get("browser") == browser_key
            card = self._card(cards, border_color=self.ACCENT if selected else self.BORDER, border_width=2 if selected else 1)
            card.grid(row=0, column=column, sticky="nsew", padx=(0, 7) if column == 0 else (7, 0))
            ctk.CTkLabel(card, text="", image=self.icons.get("browser", "#FFFFFF", 25), fg_color=self.ACCENT if browser_key == "edge" else self.BLUE, width=46, height=46, corner_radius=23).pack(anchor="w", padx=18, pady=(18, 10))
            ctk.CTkLabel(card, text=name, text_color=self.TEXT_COLOR, font=self._font(15, "bold")).pack(anchor="w", padx=18)
            ctk.CTkLabel(card, text=self.t("browser_session_help"), text_color=self.MUTED, font=self._font(10)).pack(anchor="w", padx=18, pady=(4, 14))
            ctk.CTkButton(card, text=self.t("selected") if selected else self.t("use_this_browser"), command=lambda key=browser_key: self._select_browser(key), height=38, corner_radius=8, fg_color=self.ACCENT if selected else self.SURFACE, hover_color=self.ACCENT_HOVER if selected else "#F0ECE5", border_width=0 if selected else 1, border_color=self.BORDER, text_color="white" if selected else self.TEXT_COLOR, font=self._font(10, "bold")).pack(fill="x", padx=18, pady=(0, 18))

        tip = self._card(self.page_host, fg_color="#EFF5FF", border_color="#BDD2FF")
        tip.pack(fill="x", pady=(16, 0))
        ctk.CTkLabel(tip, text=self.t("browser_tip_title"), image=self.icons.get("info", self.BLUE, 18), compound="left", text_color=self.BLUE, font=self._font(12, "bold")).pack(anchor="w", padx=18, pady=(16, 5))
        ctk.CTkLabel(tip, text=self.t("browser_tip"), text_color="#4F6285", font=self._font(10), wraplength=850, justify="left").pack(anchor="w", padx=18, pady=(0, 16))

    def _build_history_page(self) -> None:
        self._page_heading(self.t("history_title"), self.t("history_subtitle"), (self.t("clear_history"), self.clear_history))
        scroll = ctk.CTkScrollableFrame(self.page_host, fg_color="transparent", scrollbar_button_color="#CEC9C1", scrollbar_button_hover_color="#BDB7AE")
        scroll.pack(fill="both", expand=True)
        if not self.history_data:
            empty = self._card(scroll)
            empty.pack(fill="x", pady=4)
            ctk.CTkLabel(empty, text="", image=self.icons.get("download", "#C4BFB6", 44)).pack(pady=(34, 5))
            ctk.CTkLabel(empty, text=self.t("no_recent"), text_color=self.MUTED, font=self._font(12)).pack(pady=(0, 34))
            return
        for item in self.history_data:
            row = self._card(scroll)
            row.pack(fill="x", pady=5, padx=2)
            icon = ctk.CTkLabel(row, text="", image=self.icons.get("completed", self.GREEN, 20), fg_color="#F0FBF3", width=38, height=38, corner_radius=8)
            icon.pack(side="left", padx=(12, 10), pady=10)
            text = ctk.CTkFrame(row, fg_color="transparent")
            text.pack(side="left", fill="x", expand=True, pady=10)
            ctk.CTkLabel(text, text=str(item.get("title") or self.t("media_unknown")), text_color=self.TEXT_COLOR, font=self._font(11, "bold"), anchor="w").pack(fill="x")
            ctk.CTkLabel(text, text=f"{item.get('items', '')}  ·  {item.get('date', '')}", text_color=self.MUTED, font=self._font(9), anchor="w").pack(fill="x", pady=(3, 0))
            ctk.CTkButton(row, text=self.t("open_location"), image=self.icons.get("folder", self.TEXT_COLOR, 16), compound="left", command=lambda path=item.get("folder", ""): self.open_path(path), width=104, height=34, corner_radius=7, fg_color=self.SURFACE, hover_color="#F0ECE5", border_width=1, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(9)).pack(side="right", padx=12)

    def _build_settings_page(self) -> None:
        self._page_heading(self.t("settings_title"), self.t("settings_subtitle"))
        scroll = ctk.CTkScrollableFrame(self.page_host, fg_color="transparent", scrollbar_button_color="#CEC9C1", scrollbar_button_hover_color="#BDB7AE")
        scroll.pack(fill="both", expand=True)

        self._settings_row(scroll, "browser", self.t("language"), self.t("language_help"), self._language_control)
        self._settings_row(scroll, "type", self.t("font_size"), self.t("font_size_help"), self._font_scale_control)
        self._settings_row(scroll, "folder", self.t("default_folder"), self.t("default_folder_help"), self._folder_control)
        self._settings_row(scroll, "video", self.t("default_quality"), self.t("default_quality_help"), self._quality_control)
        self._settings_row(scroll, "clipboard", self.t("filename_format"), self.t("filename_format_help"), self._filename_control)
        self._settings_row(scroll, "session", self.t("browser_source"), self.t("browser_source_help"), self._browser_control)
        self._settings_row(scroll, "browser", self.t("proxy_title"), self.t("proxy_help"), self._proxy_control)
        self._settings_row(scroll, "open_file", self.t("open_after"), self.t("open_after_help"), self._open_after_control)
        self._settings_row(scroll, "history", self.t("keep_history"), self.t("keep_history_help"), self._history_control)
        self._settings_row(scroll, "retry", self.t("media_parser"), self.t("media_parser_help", version=yt_dlp.version.__version__), self._parser_control)

        privacy = self._card(scroll, fg_color="#EFF5FF", border_color="#BDD2FF")
        privacy.pack(fill="x", padx=2, pady=(10, 5))
        ctk.CTkLabel(privacy, text=self.t("privacy"), image=self.icons.get("info", self.BLUE, 17), compound="left", text_color=self.BLUE, font=self._font(10, "bold")).pack(anchor="w", padx=14, pady=(12, 3))
        ctk.CTkLabel(privacy, text=self.t("privacy_help"), text_color="#4F6285", font=self._font(9), wraplength=760, justify="left").pack(anchor="w", padx=14, pady=(0, 12))

        actions = ctk.CTkFrame(scroll, fg_color="transparent")
        actions.pack(fill="x", padx=2, pady=(10, 16))
        ctk.CTkButton(actions, text=self.t("restore_defaults"), command=self.restore_defaults, width=112, height=40, corner_radius=8, fg_color=self.SURFACE, hover_color="#F0ECE5", border_width=1, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(10)).pack(side="right")
        ctk.CTkButton(actions, text=self.t("save_settings"), image=self.icons.get("download", "#FFFFFF", 17), compound="left", command=self.save_settings, width=142, height=40, corner_radius=8, fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER, text_color="white", font=self._font(10, "bold")).pack(side="right", padx=(0, 8))

    def _settings_row(self, parent, icon_name: str, title: str, help_text: str, control_builder) -> None:
        row = self._card(parent)
        row.pack(fill="x", padx=2, pady=4)
        ctk.CTkLabel(row, text="", image=self.icons.get(icon_name, self.TEXT_COLOR, 20), width=42).pack(side="left", padx=(10, 2), pady=12)
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True, pady=10)
        ctk.CTkLabel(text, text=title, text_color=self.TEXT_COLOR, font=self._font(10, "bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(text, text=help_text, text_color=self.MUTED, font=self._font(8), anchor="w").pack(fill="x", pady=(2, 0))
        control_builder(row)

    def _language_control(self, parent) -> None:
        control = ctk.CTkFrame(parent, width=230, height=36, fg_color="#A8ABB0", corner_radius=8)
        control.pack(side="right", padx=12)
        control.pack_propagate(False)
        for code, label in (("zh", "中文"), ("en", "English")):
            active = self.language == code
            ctk.CTkButton(
                control,
                text=label,
                command=lambda label=label: self.change_language(label),
                width=112,
                height=32,
                corner_radius=6,
                fg_color=self.ACCENT if active else self.SURFACE,
                hover_color=self.ACCENT_HOVER if active else "#F0ECE5",
                text_color="white" if active else self.TEXT_COLOR,
                font=self._font(10, "bold" if active else "normal"),
            ).pack(side="left", padx=(2, 0), pady=2)

    def _font_scale_control(self, parent) -> None:
        values = (
            (90, self.t("font_small")),
            (100, self.t("font_standard")),
            (115, self.t("font_large")),
            (130, self.t("font_extra_large")),
        )
        selected = int(self.settings_data.get("font_scale", 100))
        control = ctk.CTkFrame(parent, width=430, height=38, fg_color="#A8ABB0", corner_radius=8)
        control.pack(side="right", padx=12)
        control.pack_propagate(False)
        for scale, label in values:
            active = selected == scale
            ctk.CTkButton(
                control,
                text=label,
                command=lambda scale=scale: self.change_font_scale(scale),
                width=105,
                height=34,
                corner_radius=6,
                fg_color=self.ACCENT if active else self.SURFACE,
                hover_color=self.ACCENT_HOVER if active else "#F0ECE5",
                text_color="white" if active else self.TEXT_COLOR,
                font=self._font(9, "bold" if active else "normal"),
            ).pack(side="left", padx=(2, 0), pady=2)

    def _folder_control(self, parent) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="right", padx=12)
        ctk.CTkEntry(frame, textvariable=self.output_dir, width=310, height=34, corner_radius=7, fg_color=self.SURFACE_ALT, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(9)).pack(side="left")
        ctk.CTkButton(frame, text=self.t("change"), command=self.choose_folder, width=64, height=34, corner_radius=7, fg_color=self.SURFACE, hover_color="#F0ECE5", border_width=1, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(9)).pack(side="left", padx=(6, 0))

    def _quality_control(self, parent) -> None:
        values = list(QUALITY_LABELS[self.language].values())
        box = ctk.CTkComboBox(parent, values=values, command=self._on_quality_changed, width=230, height=34, corner_radius=7, fg_color=self.SURFACE_ALT, border_color=self.BORDER, button_color=self.SURFACE_ALT, button_hover_color="#EEE9E1", dropdown_fg_color=self.SURFACE, text_color=self.TEXT_COLOR, font=self._font(9), state="readonly")
        box.set(QUALITY_LABELS[self.language].get(self.settings_data["quality"], values[0]))
        box.pack(side="right", padx=12)

    def _filename_control(self, parent) -> None:
        mapping = self._filename_labels()
        box = ctk.CTkComboBox(parent, values=list(mapping.values()), command=self._on_filename_changed, width=230, height=34, corner_radius=7, fg_color=self.SURFACE_ALT, border_color=self.BORDER, button_color=self.SURFACE_ALT, button_hover_color="#EEE9E1", dropdown_fg_color=self.SURFACE, text_color=self.TEXT_COLOR, font=self._font(9), state="readonly")
        box.set(mapping.get(self.settings_data["filename_format"], next(iter(mapping.values()))))
        box.pack(side="right", padx=12)

    def _browser_control(self, parent) -> None:
        mapping = self._browser_labels()
        box = ctk.CTkComboBox(parent, values=list(mapping.values()), command=self._on_browser_changed, width=230, height=34, corner_radius=7, fg_color=self.SURFACE_ALT, border_color=self.BORDER, button_color=self.SURFACE_ALT, button_hover_color="#EEE9E1", dropdown_fg_color=self.SURFACE, text_color=self.TEXT_COLOR, font=self._font(9), state="readonly")
        box.set(mapping.get(self.settings_data.get("browser", ""), mapping[""]))
        box.pack(side="right", padx=12)

    def _proxy_control(self, parent) -> None:
        ctk.CTkEntry(parent, textvariable=self.proxy_url, width=230, height=34, corner_radius=7, fg_color=self.SURFACE_ALT, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(9), placeholder_text="http://127.0.0.1:7897").pack(side="right", padx=12)

    def _open_after_control(self, parent) -> None:
        switch = ctk.CTkSwitch(parent, text="", width=48, command=lambda: self.settings_data.__setitem__("open_after_complete", bool(switch.get())), fg_color="#C9C4BB", progress_color=self.ACCENT, button_color="white", button_hover_color="white")
        if self.settings_data.get("open_after_complete", True):
            switch.select()
        switch.pack(side="right", padx=18)

    def _history_control(self, parent) -> None:
        switch = ctk.CTkSwitch(parent, text="", width=48, command=lambda: self.settings_data.__setitem__("keep_history", bool(switch.get())), fg_color="#C9C4BB", progress_color=self.ACCENT, button_color="white", button_hover_color="white")
        if self.settings_data.get("keep_history", True):
            switch.select()
        switch.pack(side="right", padx=18)

    def _parser_control(self, parent) -> None:
        ctk.CTkButton(parent, text=self.t("check_version"), command=self.show_parser_version, width=100, height=34, corner_radius=7, fg_color=self.SURFACE, hover_color="#F0ECE5", border_width=1, border_color=self.BORDER, text_color=self.TEXT_COLOR, font=self._font(9)).pack(side="right", padx=12)

    def _quality_labels_inverse(self) -> dict[str, str]:
        return {label: key for key, label in QUALITY_LABELS[self.language].items()}

    def _browser_labels(self) -> dict[str, str]:
        return {"": self.t("browser_none"), "edge": "Microsoft Edge", "chrome": "Google Chrome"}

    def _filename_labels(self) -> dict[str, str]:
        return {"title_id": self.t("filename_title_id"), "title": self.t("filename_title"), "source_title": self.t("filename_source_title")}

    def _on_quality_changed(self, value: str) -> None:
        self.settings_data["quality"] = self._quality_labels_inverse().get(value, "1080")

    def _on_browser_changed(self, value: str) -> None:
        inverse = {label: key for key, label in self._browser_labels().items()}
        self.settings_data["browser"] = inverse.get(value, "")

    def _on_filename_changed(self, value: str) -> None:
        inverse = {label: key for key, label in self._filename_labels().items()}
        self.settings_data["filename_format"] = inverse.get(value, "title_id")

    def change_language(self, value: str) -> None:
        new_language = "zh" if value == "中文" else "en"
        if new_language == self.language:
            return
        self.language = new_language
        self.settings_data["language"] = new_language
        self.save_settings(show_message=False)
        self.current_page = "settings"
        self._build_shell()

    def change_font_scale(self, scale: int) -> None:
        if scale not in (90, 100, 115, 130):
            return
        if int(self.settings_data.get("font_scale", 100)) == scale:
            return
        self.settings_data["font_scale"] = scale
        self.save_settings(show_message=False)
        self.current_page = "settings"
        self._build_shell()

    def _select_browser(self, browser_key: str) -> None:
        self.settings_data["browser"] = browser_key
        self.save_settings(show_message=False)
        self._show_page("browser")

    def restore_defaults(self) -> None:
        self.settings_data = self.default_settings()
        self.language = self.settings_data["language"]
        self.output_dir.set(self.settings_data["output_dir"])
        self.proxy_url.set("")
        self.save_settings(show_message=False)
        self.current_page = "settings"
        self._build_shell()

    def save_settings(self, show_message: bool = True) -> None:
        try:
            proxy = normalize_proxy(self.proxy_url.get())
        except ValueError:
            messagebox.showerror(APP_NAME, self.t("proxy_error"))
            return
        self.settings_data["language"] = self.language
        self.settings_data["output_dir"] = self.output_dir.get().strip() or str(default_download_dir())
        self.settings_data["proxy"] = proxy
        write_json(self.settings_path, self.settings_data)
        if show_message:
            messagebox.showinfo(APP_NAME, self.t("saved"))

    def show_parser_version(self) -> None:
        messagebox.showinfo(APP_NAME, self.t("version_message", version=yt_dlp.version.__version__))

    def paste_url(self) -> None:
        try:
            value = self.root.clipboard_get().strip()
        except Exception:
            return
        if value:
            self.url.set(value)
            if hasattr(self, "url_entry"):
                self.url_entry.focus_set()

    def choose_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir.get())
        if selected:
            self.output_dir.set(selected)
            self.settings_data["output_dir"] = selected

    def open_folder(self) -> None:
        self.open_path(self.output_dir.get())

    def open_path(self, value: str) -> None:
        if not value:
            return
        path = Path(value).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
            os.startfile(path)  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def open_browser(self) -> None:
        webbrowser.open("https://www.youtube.com/")

    def clear_history(self) -> None:
        if self.history_data and not messagebox.askyesno(APP_NAME, self.t("confirm_clear")):
            return
        self.history_data = []
        write_json(self.history_path, self.history_data)
        self._show_page("history")

    @staticmethod
    def _valid_url(url: str) -> bool:
        return url.startswith(("https://", "http://")) and len(url) < 4096

    def _selected_browser(self) -> str | None:
        value = self.settings_data.get("browser")
        return value if value in ("edge", "chrome") else None

    def analyze(self) -> None:
        url = self.url.get().strip()
        if not self._valid_url(url):
            messagebox.showwarning(APP_NAME, self.t("link_invalid"))
            return
        self.analysis_mode = "analyzing"
        self.analysis_info = None
        self.thumbnail_bytes = None
        if self.current_page == "download":
            self._render_analysis_panel()
        self._start_worker("analyze", self._analyze_worker, url, self._selected_browser())

    def download(self) -> None:
        url = self.url.get().strip()
        if not self._valid_url(url):
            messagebox.showwarning(APP_NAME, self.t("link_invalid"))
            return
        want_video = self.download_video.get()
        want_cover = self.download_cover.get()
        want_mp3 = self.download_mp3.get()
        if not any((want_video, want_cover, want_mp3)):
            messagebox.showwarning(APP_NAME, self.t("choose_content"))
            return
        output = Path(self.output_dir.get()).expanduser()
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(APP_NAME, self.t("folder_error", error=exc))
            return
        self.save_settings(show_message=False)
        self.progress.set(0)
        self.status_text = self.t("preparing")
        self.analysis_mode = "downloading"
        if self.current_page == "download":
            self._render_analysis_panel()
        quality_key = self.settings_data.get("quality", "1080")
        self._start_worker(
            "download",
            self._download_worker,
            url,
            output,
            QUALITY_HEIGHTS.get(quality_key, 1080),
            want_video,
            want_cover,
            want_mp3,
            self._selected_browser(),
        )

    def cancel(self) -> None:
        self.cancel_event.set()
        self.status_text = self.t("download_cancelled")
        if self.current_page == "download":
            self._render_analysis_panel()

    def _start_worker(self, kind: str, target, *args) -> None:
        if self.worker and self.worker.is_alive():
            return
        self.cancel_event.clear()
        self.busy = True
        self.busy_kind = kind
        self._refresh_busy_controls()
        self.worker = threading.Thread(target=target, args=args, daemon=True)
        self.worker.start()

    def _refresh_busy_controls(self) -> None:
        if hasattr(self, "analyze_button") and self.analyze_button.winfo_exists():
            self.analyze_button.configure(state="disabled" if self.busy else "normal", text=self.t("analyzing") if self.busy_kind == "analyze" and self.busy else self.t("analyze"))
        if hasattr(self, "download_button") and self.download_button.winfo_exists():
            self.download_button.configure(state="disabled" if self.busy else "normal")
        if hasattr(self, "cancel_button") and self.cancel_button.winfo_exists():
            self.cancel_button.configure(state="normal" if self.busy else "disabled")

    def _base_options(self, browser: str | None = None) -> dict:
        ffmpeg = bundled_path("vendor", "ffmpeg.exe")
        node = bundled_path("vendor", "node.exe")
        options: dict = {
            "noplaylist": True,
            "windowsfilenames": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "retries": 5,
            "fragment_retries": 5,
            "continuedl": True,
        }
        if ffmpeg.exists():
            options["ffmpeg_location"] = str(ffmpeg)
        if node.exists():
            options["js_runtimes"] = {"node": {"path": str(node)}}
        if browser:
            options["cookiesfrombrowser"] = (browser,)
        proxy = active_proxy(str(self.settings_data.get("proxy", "")))
        if proxy:
            options["proxy"] = proxy
        return options

    @staticmethod
    def _format_summary(info: dict) -> tuple[int, list[str]]:
        formats = info.get("formats") or []
        labels: list[str] = []
        seen: set[str] = set()
        for item in formats:
            height = item.get("height")
            ext = str(item.get("ext") or "").upper()
            if height:
                label = f"{height}p"
            elif item.get("acodec") not in (None, "none") and item.get("vcodec") == "none":
                label = ext or "AUDIO"
            else:
                continue
            if label not in seen:
                seen.add(label)
                labels.append(label)
        labels.sort(key=lambda value: int(value[:-1]) if value.endswith("p") and value[:-1].isdigit() else 0, reverse=True)
        return len(formats), labels

    def _analyze_worker(self, url: str, browser: str | None) -> None:
        try:
            with yt_dlp.YoutubeDL(self._base_options(browser)) as ydl:
                info = ydl.extract_info(url, download=False)
            count, labels = self._format_summary(info)
            summary = {
                "title": str(info.get("title") or self.t("media_unknown")),
                "duration": str(info.get("duration_string") or self.t("duration_unknown")),
                "source": str(info.get("extractor_key") or info.get("extractor") or self.t("webpage")),
                "format_count": count,
                "format_labels": labels,
            }
            thumbnail_bytes = None
            thumbnail_url = info.get("thumbnail")
            if thumbnail_url:
                try:
                    request = Request(str(thumbnail_url), headers={"User-Agent": "Mozilla/5.0"})
                    with urlopen(request, timeout=12) as response:
                        thumbnail_bytes = response.read(5_000_000)
                except OSError:
                    pass
            self.events.put(("analysis", (summary, thumbnail_bytes)))
        except Exception as exc:
            self.events.put(("error", self._friendly_error(exc)))
        finally:
            self.events.put(("done", None))

    def _output_template(self, output: Path) -> str:
        choice = self.settings_data.get("filename_format", "title_id")
        if choice == "title":
            pattern = "%(title).180B.%(ext)s"
        elif choice == "source_title":
            pattern = "%(extractor_key)s - %(title).160B.%(ext)s"
        else:
            pattern = "%(title).180B [%(id)s].%(ext)s"
        return str(output / pattern)

    def _download_worker(self, url: str, output: Path, height: int | None, want_video: bool, want_cover: bool, want_mp3: bool, browser: str | None) -> None:
        current_job = 0
        job_count = int(want_video) + int(want_mp3) + int(want_cover and not (want_video or want_mp3))
        phase = self.t("phase_video")

        def progress_hook(data: dict) -> None:
            if self.cancel_event.is_set():
                raise RuntimeError("cancelled")
            state = data.get("status")
            if state == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                downloaded = data.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total else 0
                overall = ((current_job + percent / 100) / max(job_count, 1)) * 100
                speed = str(data.get("_speed_str", "")).strip()
                eta = str(data.get("_eta_str", "")).strip()
                self.events.put(("progress", overall))
                self.events.put(("status", self.t("download_progress", phase=phase, percent=percent, speed=speed, eta=eta)))
            elif state == "finished":
                self.events.put(("status", self.t("finishing", phase=phase)))

        common = self._base_options(browser)
        common.update({"outtmpl": self._output_template(output), "progress_hooks": [progress_hook]})
        jobs: list[tuple[str, dict]] = []
        if want_video:
            options = dict(common)
            options.update({"format": format_selector(height), "merge_output_format": "mp4", "writethumbnail": want_cover, "postprocessors": ([{"key": "FFmpegThumbnailsConvertor", "format": "jpg"}] if want_cover else [])})
            jobs.append((self.t("phase_video"), options))
        if want_mp3:
            options = dict(common)
            save_cover_here = want_cover and not want_video
            options.update({"format": "bestaudio/best", "writethumbnail": save_cover_here, "postprocessors": (([{"key": "FFmpegThumbnailsConvertor", "format": "jpg"}] if save_cover_here else []) + [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"}])})
            jobs.append(("MP3", options))
        if want_cover and not (want_video or want_mp3):
            options = dict(common)
            options.update({"skip_download": True, "writethumbnail": True, "postprocessors": [{"key": "FFmpegThumbnailsConvertor", "format": "jpg"}]})
            jobs.append((self.t("phase_cover"), options))

        try:
            info = None
            for current_job, (phase, options) in enumerate(jobs):
                if self.cancel_event.is_set():
                    raise RuntimeError("cancelled")
                self.events.put(("status", self.t("processing", phase=phase)))
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=True)
                self.events.put(("progress", ((current_job + 1) / max(job_count, 1)) * 100))
            if info is None:
                raise RuntimeError("no media returned")
            title = str(info.get("title") or self.t("media_unknown"))
            requested: list[str] = []
            if want_video:
                requested.append(self.t("video"))
            if want_cover:
                requested.append(self.t("cover"))
            if want_mp3:
                requested.append("MP3")
            self.events.put(("success", {"folder": str(output), "title": title, "items": " + ".join(requested)}))
        except Exception as exc:
            if self.cancel_event.is_set() or str(exc) == "cancelled":
                self.events.put(("cancelled", None))
            else:
                self.events.put(("error", self._friendly_error(exc)))
        finally:
            self.events.put(("done", None))

    def _friendly_error(self, exc: Exception) -> str:
        detail = str(exc).replace("ERROR:", "").strip()
        if "sign in to confirm" in detail.lower() and "not a bot" in detail.lower():
            if self.settings_data.get("proxy") and not active_proxy(str(self.settings_data["proxy"])):
                return self.t("proxy_offline_error")
            return self.t("youtube_bot_error")
        if len(detail) > 520:
            detail = detail[-520:]
        return self.t("failed_detail", detail=detail)

    def _record_history(self, result: dict) -> None:
        if not self.settings_data.get("keep_history", True):
            return
        item = {
            "title": result.get("title", self.t("media_unknown")),
            "items": result.get("items", ""),
            "folder": result.get("folder", self.output_dir.get()),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self.history_data.insert(0, item)
        self.history_data = self.history_data[:50]
        write_json(self.history_path, self.history_data)

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "analysis":
                    summary, thumbnail = value  # type: ignore[misc]
                    self.analysis_info = summary
                    self.thumbnail_bytes = thumbnail
                    self.media_title = str(summary.get("title") or "")
                    self.analysis_mode = "complete_analysis"
                    if self.current_page == "download":
                        self._render_analysis_panel()
                elif kind == "status":
                    self.status_text = str(value)
                    if self.current_page == "download" and self.analysis_mode == "downloading":
                        self._render_analysis_panel()
                elif kind == "progress":
                    self.progress.set(float(value))
                    if self.current_page == "download" and self.analysis_mode == "downloading":
                        self._render_analysis_panel()
                elif kind == "error":
                    self.analysis_mode = "ready" if self.busy_kind == "analyze" else "complete_analysis"
                    messagebox.showerror(APP_NAME, str(value))
                    if self.current_page == "download":
                        self._render_analysis_panel()
                elif kind == "cancelled":
                    self.analysis_mode = "complete_analysis" if self.analysis_info else "ready"
                    self.status_text = self.t("download_cancelled")
                    if self.current_page == "download":
                        self._render_analysis_panel()
                elif kind == "success":
                    result = value if isinstance(value, dict) else {}
                    self.media_title = str(result.get("title") or self.media_title)
                    self.progress.set(100)
                    self.analysis_mode = "complete"
                    self._record_history(result)
                    if self.current_page == "download":
                        self._render_analysis_panel()
                    if self.settings_data.get("open_after_complete", True):
                        self.open_path(str(result.get("folder") or self.output_dir.get()))
                    else:
                        messagebox.showinfo(APP_NAME, self.t("download_complete"))
                elif kind == "done":
                    self.busy = False
                    self.busy_kind = ""
                    self._refresh_busy_controls()
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)


def main() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    ctk.set_widget_scaling(0.92)
    root = ctk.CTk()
    app = VideoGrabApp(root)
    for argument in sys.argv[1:]:
        if argument.startswith("--page="):
            page = argument.split("=", 1)[1]
            if page in {"download", "browser", "history", "settings"}:
                app._show_page(page)
        elif argument.startswith("--language="):
            language = argument.split("=", 1)[1]
            if language in {"zh", "en"} and language != app.language:
                app.language = language
                app.settings_data["language"] = language
                app._build_shell()
        elif argument.startswith("--font-scale="):
            try:
                font_scale = int(argument.split("=", 1)[1])
            except ValueError:
                continue
            if font_scale in {90, 100, 115, 130}:
                app.settings_data["font_scale"] = font_scale
                app._build_shell()
        elif argument == "--mobile-pairing":
            root.after(350, app.open_mobile_pairing)
    if "--smoke-test" in sys.argv:
        root.after(2500, root.destroy)
    root.mainloop()
    if "--smoke-test" in sys.argv:
        print(f"{APP_NAME} {APP_VERSION} smoke test passed")


if __name__ == "__main__":
    main()
