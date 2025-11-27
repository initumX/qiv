from PySide6.QtGui import QPixmap, QTransform, QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect, QSize, Qt
from typing import Optional, List
from constants import WB_MAX_HALF_SIZE, WB_MIN_DIVISOR
from PIL import Image
import os
from image_helpers import ResizeHelper, WhiteBalanceHelper


class ImageModel:
    """
    Represents the loaded image and its transformation state.
    """
    def __init__(self, path: Optional[str] = None):
        self.path: Optional[str] = path
        self.current_pixmap: Optional[QPixmap] = None
        self.size: Optional[QSize] = None

    def apply_to_current(self, pixmap: QPixmap):
        """Centralized method to update current and original pixmap."""
        if pixmap.isNull():
            return
        self.current_pixmap = pixmap.copy()
        self.size = pixmap.size()

    def load_from_path(self, path: str) -> bool:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            print(f"Failed to load image: {path}")
            return False
        self.path = path
        self.apply_to_current(pixmap)
        return True

    def reload_from_path(self) -> bool:
        if not self.path:
            return False
        return self.load_from_path(self.path)

    def load_from_clipboard(self) -> bool:
        clipboard = QApplication.clipboard()
        pixmap = clipboard.pixmap()
        if pixmap.isNull():
            return False
        self.path = None
        self.apply_to_current(pixmap)
        return True

    def _apply_transform(self, transform: QTransform):
        if not self.current_pixmap:
            return
        transformed = self.current_pixmap.transformed(transform, Qt.SmoothTransformation)
        self.apply_to_current(transformed)

    def rotate_90_clockwise(self):
        self._apply_transform(QTransform().rotate(90))

    def rotate_90_counterclockwise(self):
        self._apply_transform(QTransform().rotate(-90))

    def flip_horizontal(self):
        self._apply_transform(QTransform().scale(-1, 1))

    def flip_vertical(self):
        self._apply_transform(QTransform().scale(1, -1))

    def resize(self, width: int, height: int):
        if not self.current_pixmap:
            return
        qimage_resized = ResizeHelper.resize_pixmap(self.current_pixmap, width, height)
        self.apply_to_current(QPixmap.fromImage(qimage_resized))

    def save(self, path: str, format: str = "JPEG", quality: int = 95) -> bool:
        if not self.current_pixmap:
            return False
        qimage = self.current_pixmap.toImage()
        img = Image.fromqimage(qimage)

        opts = {}
        if format.lower() in ("jpg", "jpeg"):
            opts = {"quality": quality, "optimize": True}
        elif format.lower() == "webp":
            opts = {"quality": quality, "method": 4}

        try:
            img.save(path, format.upper(), **opts)
            return True
        except Exception:
            return False

    def apply_white_balance_from_point(self, x: int, y: int):
        if not self.current_pixmap:
            return
        new_pixmap = WhiteBalanceHelper.apply_white_balance(
            self.current_pixmap, x, y,
            WB_MAX_HALF_SIZE, WB_MIN_DIVISOR
        )
        if new_pixmap and not new_pixmap.isNull():
            self.apply_to_current(new_pixmap)

class NavigatorModel:
    def __init__(self):
        self.current_directory: Optional[str] = None
        self.image_paths: List[str] = []
        self.current_file_index: int = -1
        self.max_path_length = 50
        self.SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

    def _is_image_file(self, path: str) -> bool:
        return os.path.splitext(path)[1].lower() in self.SUPPORTED_EXTENSIONS

    def get_image_paths_flat(self, directory: str) -> List[str]:
        """Get sorted list of image paths in a single directory (non-recursive)."""
        paths = []
        try:
            for filename in os.listdir(directory):
                full_path = os.path.join(directory, filename)
                if os.path.isfile(full_path) and self._is_image_file(full_path):
                    paths.append(full_path)
        except OSError:
            pass  # Directory inaccessible
        paths.sort(key=lambda p: os.path.basename(p).lower())
        return paths

    def get_image_paths_recursive(self, root_dir: str, max_depth: int = 2) -> List[str]:
        """Recursively collect image paths up to `max_depth` (root_dir = depth 0)."""
        paths = []
        try:
            for root, dirs, files in os.walk(root_dir):
                rel_root = os.path.relpath(root, root_dir)
                depth = 0 if rel_root == "." else rel_root.count(os.sep) + 1
                if depth > max_depth:
                    dirs.clear()
                    continue
                for filename in files:
                    full_path = os.path.join(root, filename)
                    if self._is_image_file(full_path):
                        paths.append(full_path)
        except OSError:
            pass
        paths.sort(key=lambda p: os.path.basename(p).lower())
        return paths

    def get_image_paths(self, directory: str, recursive: bool = False, max_depth: int = 2) -> List[str]:
        """Unified interface to get image paths."""
        if recursive:
            return self.get_image_paths_recursive(directory, max_depth)
        else:
            return self.get_image_paths_flat(directory)

    def set_current_path(self, path: str) -> bool:
        if not path:
            return False
        directory = os.path.dirname(path)
        if directory != self.current_directory:
            self.current_directory = directory
            # Use flat scan for main navigation (backward compatibility)
            self.image_paths = self.get_image_paths_flat(directory)
        try:
            self.current_file_index = self.image_paths.index(path)
            return True
        except ValueError:
            # Fallback: match by basename
            for i, p in enumerate(self.image_paths):
                if os.path.basename(p) == os.path.basename(path):
                    self.current_file_index = i
                    return True
            self.current_file_index = -1
            return False

    def get_next_path(self) -> Optional[str]:
        if not self.image_paths:
            return None
        return self.image_paths[(self.current_file_index + 1) % len(self.image_paths)]

    def get_previous_path(self) -> Optional[str]:
        if not self.image_paths:
            return None
        return self.image_paths[(self.current_file_index - 1) % len(self.image_paths)]

    def navigate(self, direction: str) -> Optional[str]:
        if direction == "next":
            path = self.get_next_path()
        elif direction == "previous":
            path = self.get_previous_path()
        else:
            return None
        if path:
            self.current_file_index = self.image_paths.index(path)
        return path

    def has_next(self) -> bool:
        return len(self.image_paths) > 1

    def has_previous(self) -> bool:
        return len(self.image_paths) > 1

    @property
    def total_count(self) -> int:
        return len(self.image_paths)

    @property
    def current_filename(self) -> Optional[str]:
        if 0 <= self.current_file_index < len(self.image_paths):
            return os.path.basename(self.image_paths[self.current_file_index])
        return None

    def format_path_for_display(self, path: str) -> str:
        if not path:
            return ""
        return os.path.basename(path) if len(path) > self.max_path_length else path

    def format_status_text(self, pixmap=None) -> str:
        """
        Returns a formatted string for the status bar based on current image and navigation state.
        """
        if pixmap and not pixmap.isNull():
            w, h = pixmap.width(), pixmap.height()
            mp = w * h / 1_000_000
            size_str = f"{w}×{h} ({mp:.1f} MP)"
        else:
            size_str = "??×?? (?.? MP)"
        if self.total_count > 0:
            idx = self.current_file_index + 1
            total = self.total_count
            name = self.current_filename or "Unknown"
            return f"{idx}/{total} — {name} {size_str}"
        else:
            if self.current_directory is None and pixmap and not pixmap.isNull():
                return f"Pasted image {size_str}"
            elif self.current_directory is not None and pixmap and not pixmap.isNull():
                name = os.path.basename(self.image_paths[0]) if self.image_paths else "Unknown"
                return f"{name} {size_str}"
            else:
                return f"Pasted image {size_str}"


class CropArea:
    def __init__(self):
        self.rect: QRect = QRect()
        self.is_active: bool = False

    def set_rect(self, rect: QRect):
        self.rect = rect
        self.is_active = not rect.isNull()

    def reset(self):
        self.rect = QRect()
        self.is_active = False

class ViewState:
    def __init__(self):
        self.zoom_factor: float = 1.0
        self.fit_to_window: bool = True
        self.auto_fit_enabled: bool = True

    def reset_zoom(self):
        self.zoom_factor = 1.0
        self.fit_to_window = True

    def apply_zoom(self, factor: float):
        self.zoom_factor *= factor
        self.fit_to_window = False


class ClipboardModel:
    def __init__(self):
        self.clipboard = QApplication.clipboard()

    def copy_image(self, pixmap: QPixmap):
        self.clipboard.setPixmap(pixmap)

    def paste_image(self) -> Optional[QPixmap]:
        pixmap = self.clipboard.pixmap()
        return pixmap if not pixmap.isNull() else None

