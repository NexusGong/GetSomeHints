# -*- coding: utf-8 -*-
# 滑块验证工具（登录时可能用到）
import os
from typing import List
from urllib.parse import urlparse

import cv2
import httpx
import numpy as np


class Slide:
    """识别滑块缺口位置，返回需要滑动的 x 距离。"""

    def __init__(self, gap: str, bg: str, gap_size=None, bg_size=None, out=None):
        self.img_dir = os.path.join(os.getcwd(), "temp_image")
        os.makedirs(self.img_dir, exist_ok=True)
        bg_resize = bg_size if bg_size else (340, 212)
        gap_size = gap_size if gap_size else (68, 68)
        self.bg = self._check_img(bg, "bg", bg_resize)
        self.gap = self._check_img(gap, "gap", gap_size)
        self.out = out or os.path.join(self.img_dir, "out.jpg")

    def _check_img(self, img: str, img_type: str, resize) -> str:
        if img.startswith("http"):
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.164 Safari/537.36"}
            r = httpx.get(img, headers=headers, timeout=15)
            if r.status_code != 200:
                raise Exception(f"Failed to fetch {img_type} image")
            path = os.path.join(self.img_dir, f"{img_type}.jpg")
            arr = np.asarray(bytearray(r.content), dtype="uint8")
            im = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if im is None:
                raise Exception(f"Failed to decode {img_type} image")
            if resize:
                im = cv2.resize(im, resize)
            cv2.imwrite(path, im)
            return path
        return img

    @staticmethod
    def _clear_white(img_path: str):
        img = cv2.imread(img_path)
        if img is None:
            return img_path
        rows, cols = img.shape[:2]
        min_x, min_y, max_x, max_y = 255, 255, 0, 0
        for x in range(1, rows):
            for y in range(1, cols):
                if len(set(img[x, y])) >= 2:
                    min_x, max_x = min(min_x, x), max(max_x, x)
                    min_y, max_y = min(min_y, y), max(max_y, y)
        im = img[min_x:max_x, min_y:max_y]
        path = img_path + ".crop.jpg"
        cv2.imwrite(path, im)
        return path

    def discern(self) -> int:
        gap_crop = self._clear_white(self.gap)
        g = cv2.imread(gap_crop, cv2.IMREAD_GRAYSCALE)
        if g is None:
            return 0
        slide = cv2.Canny(g, 100, 200)
        back = cv2.imread(self.bg, cv2.IMREAD_GRAYSCALE)
        if back is None:
            return 0
        back_edge = cv2.Canny(back, 100, 200)
        result = cv2.matchTemplate(back_edge, slide, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return int(max_loc[0])


def get_track_simple(distance: int) -> List[int]:
    track = []
    current, mid, t, v = 0, distance * 4 / 5, 0.2, 1.0
    while current < distance:
        a = 4 if current < mid else -3
        v = v + a * t
        move = v * t + 0.5 * a * t * t
        current += move
        track.append(round(move))
    return track


def get_tracks(distance: int, level: str = "easy") -> List[int]:
    if level == "easy":
        return get_track_simple(distance)
    from app.douyin_crawler.easing import get_tracks as get_tracks_ease
    _, tricks = get_tracks_ease(distance, seconds=2, ease_func="ease_out_expo")
    # tricks[0] is 0, rest are deltas
    return tricks[1:] if len(tricks) > 1 else tricks
