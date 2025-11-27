from PySide6.QtGui import QPixmap, QTransform, QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect, QSize, QPointF
from typing import Optional, List
from constants import WB_MAX_HALF_SIZE, WB_MIN_DIVISOR
from PIL import Image
import os

from image_helpers import ResizeHelper


class ImageModel:
    """
    Represents the loaded image and its transformation state.
    Maintains original and current pixmap, rotation angle, and file path.
    Supports loading from file or clipboard, and 90° rotations.
    """
    def __init__(self, path: Optional[str] = None):
        self.path: Optional[str] = path
        self.original_pixmap: Optional[QPixmap] = None
        self.current_pixmap: Optional[QPixmap] = None
        self.size: Optional[QSize] = None

    def apply_to_current(self, new_pixmap: QPixmap):
        """Apply a new pixmap and save to history."""
        if new_pixmap and not new_pixmap.isNull():
            self.original_pixmap = new_pixmap.copy()
            self.current_pixmap = new_pixmap.copy()
            self.size = new_pixmap.size()

    def load_from_path(self, path: str) -> bool:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            print(f"Failed to load image: {path}")
            return False

        self.path = path
        self.original_pixmap = pixmap.copy()
        self.current_pixmap = pixmap
        self.size = pixmap.size()
        return True

    def reload_from_path(self) -> bool:
        """Reload current image from its original path."""
        if not self.path:
            return False
        # Reload from the same path
        return self.load_from_path(self.path)

    def load_from_clipboard(self) -> bool:
        """Load image from system clipboard and add to history as a new state."""
        clipboard = QApplication.clipboard()
        pixmap = clipboard.pixmap()
        if pixmap.isNull():
            return False

        self.original_pixmap = pixmap.copy()
        self.current_pixmap = pixmap.copy()
        self.size = pixmap.size()
        self.path = None
        return True

    def _apply_transform(self, transform: QTransform):
        """Apply a QTransform and update internal state."""
        if not self.current_pixmap:
            return
        self.current_pixmap = self.current_pixmap.transformed(transform, self._transform_mode())
        self.size = self.current_pixmap.size()

    def rotate_90_clockwise(self):
        self._apply_transform(QTransform().rotate(90))

    def rotate_90_counterclockwise(self):
        self._apply_transform(QTransform().rotate(-90))

    def flip_horizontal(self):
        self._apply_transform(QTransform().scale(-1, 1))


    def flip_vertical(self):
        self._apply_transform(QTransform().scale(1, -1))

    def resize(self, width: int, height: int):
        """Resize current pixmap using PIL for better quality."""
        if not self.current_pixmap:
            return
        qimage_resized = ResizeHelper.resize_pixmap(self.current_pixmap, width, height)
        self.current_pixmap = QPixmap.fromImage(qimage_resized)
        self.size = self.current_pixmap.size()

    def save(self, path: str, format: str = "JPEG", quality: int = 95):
        """Save current pixmap using Pillow."""
        if not self.current_pixmap:
            return False
        qimage = self.current_pixmap.toImage()
        img = Image.fromqimage(qimage)

        if format.lower() in ("jpg", "jpeg"):
            img.save(path, "JPEG", quality=quality, optimize=True)
        elif format.lower() == "png":
            img.save(path, "PNG")
        elif format.lower() == "webp":
            img.save(path, "WEBP", quality=quality, method=4)
        elif format.lower() == "bmp":
            img.save(path, "BMP")
        else:
            img.save(path, format)

        return True

    def apply_white_balance_from_point(self, x: int, y: int):
        """
        Apply white balance correction so that the sampled neutral point becomes gray.
        Uses green channel as reference. Gains are clamped to prevent extreme shifts.
        Window size is adaptive based on image dimensions using WB_MAX_HALF_SIZE and WB_MIN_DIVISOR.
        """
        if not self.current_pixmap:
            return
        qimage = self.current_pixmap.toImage()
        if not qimage.valid(x, y):
            return

        # Adaptive window size based on image resolution
        w, h = qimage.width(), qimage.height()
        min_dim = min(w, h)
        max_window_by_size = max(1, min_dim // WB_MIN_DIVISOR)
        half_window = min(WB_MAX_HALF_SIZE, max_window_by_size)

        total_r = total_g = total_b = 0
        count = 0
        for dx in range(-half_window, half_window + 1):
            for dy in range(-half_window, half_window + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    pixel = qimage.pixel(nx, ny)
                    b_val = pixel & 0xFF
                    g_val = (pixel >> 8) & 0xFF
                    r_val = (pixel >> 16) & 0xFF
                    total_r += r_val
                    total_g += g_val
                    total_b += b_val
                    count += 1

        if count == 0 or total_g == 0:
            return

        r = total_r / count
        g = total_g / count
        b = total_b / count

        if r == 0 or b == 0:
            return

        # Compute gains using green as reference
        gain_r = g / r
        gain_b = g / b

        # Clamp gains to avoid extreme color shifts
        gain_r = max(0.25, min(4.0, gain_r))
        gain_b = max(0.25, min(4.0, gain_b))

        # Apply gains using Pillow
        img = Image.fromqimage(qimage)
        if img.mode == "RGB":
            r_band, g_band, b_band = img.split()
            r_band = r_band.point(lambda x: min(255, int(x * gain_r)))
            b_band = b_band.point(lambda x: min(255, int(x * gain_b)))
            corrected = Image.merge("RGB", (r_band, g_band, b_band))
        elif img.mode == "RGBA":
            r_band, g_band, b_band, a_band = img.split()
            r_band = r_band.point(lambda x: min(255, int(x * gain_r)))
            b_band = b_band.point(lambda x: min(255, int(x * gain_b)))
            corrected = Image.merge("RGBA", (r_band, g_band, b_band, a_band))
        else:
            # Fallback: convert to RGB
            img = img.convert("RGB")
            r_band, g_band, b_band = img.split()
            r_band = r_band.point(lambda x: min(255, int(x * gain_r)))
            b_band = b_band.point(lambda x: min(255, int(x * gain_b)))
            corrected = Image.merge("RGB", (r_band, g_band, b_band))

        # Update model state
        qimage_out = corrected.toqimage()
        self.current_pixmap = QPixmap.fromImage(qimage_out)
        self.size = self.current_pixmap.size()
        # Treat corrected image as new base for further edits
        if self.original_pixmap is not None:
            self.original_pixmap = self.current_pixmap.copy()

    def _transform_mode(self):
        from PySide6.QtCore import Qt
        return Qt.SmoothTransformation


class NavigatorModel:
    """
    Manages navigation between image files in a directory.
    Handles tracking current directory, listing image files, and moving between them.
    """

    def __init__(self):
        self.current_directory: Optional[str] = None
        self.image_paths: List[str] = []
        self.current_file_index: int = -1
        self.max_path_length = 50

    def set_current_path(self, path: str):
        """Set current path and initialize file list in directory."""
        if not path:
            return False

        directory = os.path.dirname(path)
        filename = os.path.basename(path)

        # Only reload if directory changed
        if directory != self.current_directory:
            self.current_directory = directory
            self.image_paths = self._get_image_paths_in_directory(directory)

        # Find index of current file
        try:
            self.current_file_index = self.image_paths.index(path)
            return True
        except ValueError:
            # If path not found, try to find by filename only (fallback)
            for i, img_path in enumerate(self.image_paths):
                if os.path.basename(img_path) == filename:
                    self.current_file_index = i
                    return True
            self.current_file_index = -1
            return False

    def _get_image_paths_in_directory(self, directory: str) -> List[str]:
        """Get sorted list of full image file paths in directory."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
        paths = []

        try:
            for filename in os.listdir(directory):
                ext = os.path.splitext(filename)[1].lower()
                if ext in image_extensions:
                    paths.append(os.path.join(directory, filename))
        except OSError:
            pass  # Directory access error

        # Sort paths alphabetically by filename
        paths.sort(key=lambda x: os.path.basename(x).lower())
        return paths

    def get_next_path(self) -> Optional[str]:
        """Get path to next image file."""
        if not self.image_paths or self.current_file_index < 0:
            return None

        next_index = (self.current_file_index + 1) % len(self.image_paths)
        return self.image_paths[next_index]

    def get_previous_path(self) -> Optional[str]:
        """Get path to previous image file."""
        if not self.image_paths or self.current_file_index < 0:
            return None

        prev_index = (self.current_file_index - 1) % len(self.image_paths)
        return self.image_paths[prev_index]

    def navigate(self, direction: str) -> Optional[str]:
        """Navigate to next/previous image and return new path."""
        if direction == "next":
            new_path = self.get_next_path()
        elif direction == "previous":
            new_path = self.get_previous_path()
        else:
            return None

        if new_path:
            self.current_file_index = self.image_paths.index(new_path)
            return new_path
        return None

    def has_next(self) -> bool:
        """Check if next image exists."""
        return bool(self.get_next_path())

    def has_previous(self) -> bool:
        """Check if previous image exists."""
        return bool(self.get_previous_path())

    @property
    def total_count(self) -> int:
        """Get total number of image files."""
        return len(self.image_paths)

    @property
    def current_filename(self) -> Optional[str]:
        """Get current filename without path."""
        if 0 <= self.current_file_index < len(self.image_paths):
            return os.path.basename(self.image_paths[self.current_file_index])
        return None

    @property
    def next_filename(self) -> Optional[str]:
        """Get next filename without path."""
        next_path = self.get_next_path()
        return os.path.basename(next_path) if next_path else None

    @property
    def previous_filename(self) -> Optional[str]:
        """Get previous filename without path."""
        prev_path = self.get_previous_path()
        return os.path.basename(prev_path) if prev_path else None

    def format_path_for_display(self, path: Optional[str]) -> str:
        """Format path for display (truncate if too long)."""
        if not path:
            return ""
        if len(path) > self.max_path_length:
            return os.path.basename(path)
        return path


class CropArea:
    """
    Represents the selected rectangular region for cropping.
    Tracks active state and coordinates of the selection.
    """
    def __init__(self):
        self.rect: QRect = QRect()
        self.is_active: bool = False

    def set_rect(self, rect: QRect):
        self.rect = rect
        self.is_active = True

    def reset(self):
        self.rect = QRect()
        self.is_active = False


class ViewState:
    """
    Manages the view state: zoom level, offset, and fit-to-window mode.
    Controls how the image is displayed within the viewport.
    """
    def __init__(self):
        self.zoom_factor: float = 1.0
        self.offset: QPointF = QPointF(0, 0)
        self.fit_to_window: bool = True
        self.auto_fit_enabled: bool = True

    def reset_zoom(self):
        self.zoom_factor = 1.0
        self.fit_to_window = True

    def apply_zoom(self, factor: float):
        self.zoom_factor *= factor
        self.fit_to_window = False


class ClipboardModel:
    """
    Wrapper for system clipboard operations.
    Provides methods to copy and paste QPixmap objects.
    """
    def __init__(self):
        self.clipboard = QApplication.clipboard()

    def copy_image(self, pixmap: QPixmap):
        self.clipboard.setPixmap(pixmap)

    def paste_image(self) -> Optional[QPixmap]:
        pixmap = self.clipboard.pixmap()
        return pixmap if not pixmap.isNull() else None

