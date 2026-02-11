# -*- coding: utf-8 -*-
# 滑动轨迹 easing，用于滑块验证
import math
from typing import List, Tuple

import numpy as np


def ease_out_expo(x):
    if x == 1:
        return 1
    return 1 - pow(2, -10 * x)


def get_tracks(distance: int, seconds: float = 2, ease_func: str = "ease_out_expo") -> Tuple[List[int], List[int]]:
    tracks = [0]
    offsets = [0]
    for t in np.arange(0.0, seconds, 0.1):
        offset = round(ease_out_expo(t / seconds) * distance)
        tracks.append(offset - offsets[-1])
        offsets.append(offset)
    return offsets, tracks
