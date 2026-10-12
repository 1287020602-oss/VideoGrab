from __future__ import annotations

import math

import customtkinter as ctk
from PIL import Image, ImageColor, ImageDraw


GRID = 24
RENDER_SCALE = 4


def render_icon(name: str, color: str = "#141414") -> Image.Image:
    """Render a crisp 24px, rounded 2px-stroke VideoGrab icon."""
    scale = RENDER_SCALE
    image = Image.new("RGBA", (GRID * scale, GRID * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    ink = ImageColor.getrgb(color) + (255,)
    width = 2 * scale

    def xy(value: float) -> int:
        return int(round(value * scale))

    def box(values: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
        return tuple(xy(value) for value in values)  # type: ignore[return-value]

    def dot(x: float, y: float, radius: float = 1.0) -> None:
        draw.ellipse(box((x - radius, y - radius, x + radius, y + radius)), fill=ink)

    def line(points: list[tuple[float, float]], cap: bool = True) -> None:
        pixels = [(xy(x), xy(y)) for x, y in points]
        draw.line(pixels, fill=ink, width=width, joint="curve")
        if cap:
            dot(*points[0], radius=1)
            dot(*points[-1], radius=1)

    def arc(values: tuple[float, float, float, float], start: float, end: float) -> None:
        draw.arc(box(values), start=start, end=end, fill=ink, width=width)

    def rounded_rect(values: tuple[float, float, float, float], radius: float = 2) -> None:
        draw.rounded_rectangle(box(values), radius=xy(radius), outline=ink, width=width)

    def circle(values: tuple[float, float, float, float]) -> None:
        draw.ellipse(box(values), outline=ink, width=width)

    def polygon(points: list[tuple[float, float]], fill: bool = False) -> None:
        pixels = [(xy(x), xy(y)) for x, y in points]
        if fill:
            draw.polygon(pixels, fill=ink)
        else:
            draw.line(pixels + [pixels[0]], fill=ink, width=width, joint="curve")

    if name == "download":
        line([(12, 3), (12, 14)])
        line([(7.5, 10), (12, 14.5), (16.5, 10)])
        line([(4, 17), (4, 20), (20, 20), (20, 17)])
    elif name == "downloading":
        line([(12, 3), (12, 16)])
        line([(7.5, 12), (12, 16.5), (16.5, 12)])
        line([(6, 20), (18, 20)])
    elif name == "browser":
        circle((3, 3, 21, 21))
        arc((7, 3, 17, 21), 80, 280)
        arc((7, 3, 17, 21), 260, 100)
        line([(3.5, 12), (20.5, 12)], cap=False)
    elif name == "history":
        circle((3, 3, 21, 21))
        line([(12, 7), (12, 12), (16, 14)])
    elif name == "settings":
        points: list[tuple[float, float]] = []
        for index in range(24):
            angle = -math.pi / 2 + index * math.pi / 12
            radius = 9 if index % 3 == 0 else (7.7 if index % 3 == 1 else 8.4)
            points.append((12 + math.cos(angle) * radius, 12 + math.sin(angle) * radius))
        polygon(points)
        circle((9, 9, 15, 15))
    elif name == "mobile":
        rounded_rect((6, 2.5, 18, 21.5), 2.5)
        line([(10, 5), (14, 5)], cap=False)
        line([(10.5, 18.5), (13.5, 18.5)], cap=False)
        arc((1.5, 7.5, 8.5, 14.5), 285, 75)
        arc((-1, 5, 11, 17), 300, 60)
    elif name == "folder":
        line([(3, 7), (8.5, 7), (10.5, 9), (21, 9), (21, 20), (3, 20), (3, 7)])
    elif name == "video":
        rounded_rect((3, 4, 21, 20), 2)
        polygon([(10, 8), (10, 16), (16, 12)], fill=True)
    elif name == "cover":
        rounded_rect((3, 4, 21, 20), 2)
        dot(16.5, 8.5, 1.2)
        line([(5.5, 17), (10, 12.5), (13, 15.5), (15.5, 13), (19, 17)])
    elif name == "audio":
        line([(10, 5), (19, 3), (19, 15)])
        line([(10, 5), (10, 17)])
        draw.ellipse(box((5, 15, 10, 20)), outline=ink, width=width)
        draw.ellipse(box((14, 13, 19, 18)), outline=ink, width=width)
    elif name == "mp3":
        circle((3, 3, 21, 21))
        for x, top, bottom in ((8, 10, 14), (10.5, 7.5, 16.5), (13.5, 8.5, 15.5), (16, 10, 14)):
            line([(x, top), (x, bottom)])
    elif name == "link":
        arc((2, 7, 13, 18), 42, 315)
        arc((11, 6, 22, 17), 222, 135)
        line([(8.5, 15.5), (15.5, 8.5)])
    elif name in {"clipboard", "paste"}:
        rounded_rect((5, 5, 19, 21), 2)
        rounded_rect((8, 3, 16, 8), 2)
        line([(8, 12), (16, 12)])
        line([(8, 16), (15, 16)])
    elif name == "location":
        line([(3, 8), (8, 8), (10, 10), (20, 10), (20, 20), (3, 20), (3, 8)])
        circle((13, 3, 21, 11))
        dot(17, 7, 1)
        line([(17, 11), (17, 15)])
    elif name == "analyze":
        line([(5, 19), (15, 9)])
        line([(8, 16), (11, 19)])
        for cx, cy in ((17.5, 5.5), (6, 7), (19, 15.5)):
            line([(cx, cy - 2), (cx, cy + 2)])
            line([(cx - 2, cy), (cx + 2, cy)])
    elif name == "play":
        polygon([(7, 4), (7, 20), (20, 12)], fill=False)
    elif name == "pause":
        line([(8, 5), (8, 19)])
        line([(16, 5), (16, 19)])
    elif name in {"cancel", "error"}:
        circle((3, 3, 21, 21))
        line([(8, 8), (16, 16)])
        line([(16, 8), (8, 16)])
    elif name == "retry":
        arc((4, 4, 20, 20), 38, 330)
        line([(17, 4), (20, 5), (19, 8)])
    elif name == "queue":
        line([(6, 7), (20, 7)])
        line([(6, 12), (20, 12)])
        line([(6, 17), (20, 17)])
        dot(3, 7, 1)
        dot(3, 12, 1)
        dot(3, 17, 1)
    elif name == "open_file":
        line([(11, 5), (5, 5), (5, 20), (19, 20), (19, 14)])
        line([(13, 11), (21, 3)])
        line([(16, 3), (21, 3), (21, 8)])
    elif name == "more":
        dot(5, 12, 1.5)
        dot(12, 12, 1.5)
        dot(19, 12, 1.5)
    elif name in {"success", "completed"}:
        circle((3, 3, 21, 21))
        line([(7.5, 12), (10.5, 15), (16.5, 8.5)])
    elif name == "info":
        circle((3, 3, 21, 21))
        dot(12, 7.5, 1.1)
        line([(12, 11), (12, 17)])
    elif name == "warning":
        polygon([(12, 3), (22, 20), (2, 20)])
        line([(12, 8), (12, 14)])
        dot(12, 17.5, 1.1)
    elif name == "session":
        circle((8.5, 4, 15.5, 11))
        arc((5, 10, 19, 22), 185, 355)
        circle((3, 3, 21, 21))
    elif name == "lock":
        rounded_rect((5, 10, 19, 21), 2)
        arc((8, 3, 16, 15), 180, 360)
        line([(12, 14), (12, 17)])
    elif name == "type":
        line([(4, 5), (14, 5)])
        line([(9, 5), (9, 19)])
        line([(14, 10), (20, 10)])
        line([(17, 10), (17, 19)])
    else:
        rounded_rect((4, 4, 20, 20), 3)
        dot(12, 12, 1.5)

    return image


class IconFactory:
    def __init__(self) -> None:
        self._cache: dict[tuple[str, str, int], ctk.CTkImage] = {}

    def get(self, name: str, color: str = "#141414", size: int = 20) -> ctk.CTkImage:
        key = (name, color.upper(), size)
        if key not in self._cache:
            raster = render_icon(name, color)
            self._cache[key] = ctk.CTkImage(light_image=raster, dark_image=raster, size=(size, size))
        return self._cache[key]
