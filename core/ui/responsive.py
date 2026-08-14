import ctypes
import os
from dataclasses import dataclass


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class WorkArea:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.bottom - self.top


def get_workarea_rect(window):
    if os.name == "nt":
        try:
            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            rect = RECT()
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                return WorkArea(rect.left, rect.top, rect.right, rect.bottom)
        except Exception:
            pass

    return WorkArea(0, 0, window.winfo_screenwidth(), window.winfo_screenheight())


def get_workarea_size(window):
    area = get_workarea_rect(window)
    return area.width, area.height


def get_size_class(width, height):
    if width < 1280 or height < 720:
        return "compact"
    if width < 1600 or height < 900:
        return "standard"
    return "wide"


def fit_toplevel_to_workarea(window, desired_width, desired_height, min_width=None, min_height=None, margin=36):
    workarea = get_workarea_rect(window)
    width = min(desired_width, max(640, workarea.width - margin))
    height = min(desired_height, max(480, workarea.height - margin))

    if min_width is not None:
        width = max(width, min_width)
    if min_height is not None:
        height = max(height, min_height)

    window.geometry(f"{int(width)}x{int(height)}")
    return int(width), int(height)


def center_toplevel_in_workarea(window, width, height):
    workarea = get_workarea_rect(window)
    x = workarea.left + max(0, int((workarea.width - width) / 2))
    y = workarea.top + max(0, int((workarea.height - height) / 2))
    window.geometry(f"{int(width)}x{int(height)}+{x}+{y}")
    return int(x), int(y)
