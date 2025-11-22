from PySide6.QtGui import QPixmap, QTransform, QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect, QSize, QPointF
from typing import Optional, List
from collections import deque
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
        self.current_pixmap: Optional[QPixmap] = None
        self.size: Optional[QSize] = None
        self.rotation_angle: int = 0

        self._history: deque = deque(maxlen=5)
        self._future: deque = deque()

    def _save_state(self):
        """Save current pixmap to history (only if valid)."""
        if self.current_pixmap and not self.current_pixmap.isNull():
            self._history.append(self.current_pixmap.copy())
            self._future.clear()  # Clear redo stack

    # === Undo / Redo ===
    def can_undo(self) -> bool:
        return len(self._history) > 1

    def can_redo(self) -> bool:
        return len(self._future) > 0

    def undo(self):
        if self.can_undo():
            current = self._history.pop()
            self._future.append(current)
            self.current_pixmap = self._history[-1].copy()
            self.size = self.current_pixmap.size()

    def redo(self):
        if self.can_redo():
            next_state = self._future.pop()
            self._history.append(next_state)
            self.current_pixmap = next_state.copy()
            self.size = self.current_pixmap.size()

    def apply_to_current(self, new_pixmap: QPixmap):
        """Apply a new pixmap and save to history."""
        if new_pixmap and not new_pixmap.isNull():
            self._save_state()
            self.current_pixmap = new_pixmap
            self.size = new_pixmap.size()

    def load_from_path(self, path: str) -> bool:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            print(f"Failed to load image: {path}")
            return False

        self.path = path
        self.current_pixmap = pixmap
        self.size = pixmap.size()
        self.rotation_angle = 0

        self._history.clear()
        self._future.clear()
        self._history.append(pixmap.copy())

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

        # Save current state only if there's an existing non-null image
        if self.current_pixmap and not self.current_pixmap.isNull():
            self._save_state()
        else:
            # Starting fresh: clear history
            self._history.clear()
            self._future.clear()

        self.current_pixmap = pixmap.copy()
        self.size = pixmap.size()
        self.path = None
        self.rotation_angle = 0
        self._history.append(self.current_pixmap.copy())
        return True

    def rotate_90_clockwise(self):
        if not self.current_pixmap:
            return
        transform = QTransform().rotate(90)
        self.current_pixmap = self.current_pixmap.transformed(transform, self._transform_mode())
        self.rotation_angle = (self.rotation_angle + 90) % 360

    def rotate_90_counterclockwise(self):
        if not self.current_pixmap:
            return
        transform = QTransform().rotate(-90)
        self.current_pixmap = self.current_pixmap.transformed(transform, self._transform_mode())
        self.rotation_angle = (self.rotation_angle - 90) % 360

    def flip_horizontal(self):
        """Flip current pixmap horizontally."""
        if not self.current_pixmap:
            return
        transform = QTransform().scale(-1, 1)
        self.current_pixmap = self.current_pixmap.transformed(transform, self._transform_mode())
        self.size = self.current_pixmap.size()

    def flip_vertical(self):
        """Flip current pixmap vertically."""
        if not self.current_pixmap:
            return
        transform = QTransform().scale(1, -1)
        self.current_pixmap = self.current_pixmap.transformed(transform, self._transform_mode())
        self.size = self.current_pixmap.size()

    def resize(self, width: int, height: int):
        """Resize current pixmap using PIL for better quality."""
        if not self.current_pixmap:
            return
        self._save_state()
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