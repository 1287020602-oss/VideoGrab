import importlib.util
import json
import os
import queue
import sys
import threading
from pathlib import Path


APP_PATH = Path(__file__).parents[1] / "outputs" / "VideoGrab" / "app.py"
sys.path.insert(0, str(APP_PATH.parent))
spec = importlib.util.spec_from_file_location("videograb_app", APP_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def make_app():
    app = object.__new__(module.VideoGrabApp)
    app.language = "zh"
    app.settings_data = {"filename_format": "title_id", "keep_history": True}
    app.events = queue.Queue()
    app.cancel_event = threading.Event()
    return app


def test_helpers():
    assert module.format_selector(2160) == "bv*[height<=2160]+ba/b[height<=2160]"
    assert module.format_selector(None) == "bv*+ba/b"
    app = make_app()
    options = app._base_options(None)
    assert Path(options["ffmpeg_location"]).name == "ffmpeg.exe"
    assert Path(options["js_runtimes"]["node"]["path"]).name == "node.exe"
    assert app.t("download") == "下载"
    app.language = "en"
    assert app.t("download") == "Download"
    assert module.VideoGrabApp.default_settings()["font_scale"] == 100


def test_icon_system():
    icon_module_path = APP_PATH.with_name("iconset.py")
    icon_spec = importlib.util.spec_from_file_location("videograb_icons", icon_module_path)
    icon_module = importlib.util.module_from_spec(icon_spec)
    assert icon_spec.loader is not None
    icon_spec.loader.exec_module(icon_module)
    names = [
        "download", "browser", "history", "settings", "video", "cover", "audio", "mp3",
        "folder", "link", "clipboard", "location", "analyze", "play", "pause", "cancel",
        "retry", "queue", "open_file", "more", "success", "info", "warning", "error",
        "session", "lock", "downloading", "completed", "type",
    ]
    for name in names:
        image = icon_module.render_icon(name)
        assert image.size == (96, 96)
        assert image.getbbox() is not None, name


def test_download_pipeline():
    app = make_app()
    calls = []

    class FakeYDL:
        def __init__(self, options):
            self.options = options
            calls.append(options)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, _url, download):
            assert download is True
            hook = self.options["progress_hooks"][0]
            hook({"status": "downloading", "total_bytes": 100, "downloaded_bytes": 50, "_speed_str": "1 MiB/s", "_eta_str": "1"})
            hook({"status": "finished"})
            return {"title": "QA media"}

    original = module.yt_dlp.YoutubeDL
    module.yt_dlp.YoutubeDL = FakeYDL
    try:
        app._download_worker("https://example.com/video", Path("C:/VideoGrab-QA"), 1080, True, True, True, None)
    finally:
        module.yt_dlp.YoutubeDL = original

    events = []
    while not app.events.empty():
        events.append(app.events.get_nowait())
    kinds = [kind for kind, _value in events]
    assert kinds.count("progress") >= 2
    assert "success" in kinds
    assert kinds[-1] == "done"
    assert len(calls) == 2
    assert calls[0]["writethumbnail"] is True
    assert any(item["key"] == "FFmpegExtractAudio" for item in calls[1]["postprocessors"])


def test_font_scale_persistence():
    data_dir = Path(__file__).parent / "font-scale-persistence"
    os.environ["VIDEOGRAB_DATA_DIR"] = str(data_dir)
    root = module.ctk.CTk()
    root.withdraw()
    app = module.VideoGrabApp(root)
    app.change_font_scale(115)
    root.update_idletasks()
    saved = json.loads((data_dir / "settings.json").read_text(encoding="utf-8"))
    assert saved["font_scale"] == 115
    assert app.settings_data["font_scale"] == 115
    root.destroy()


if __name__ == "__main__":
    test_helpers()
    test_icon_system()
    test_download_pipeline()
    test_font_scale_persistence()
    print("VideoGrab core tests passed")
