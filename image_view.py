from PySide6.QtWidgets import QGraphicsView, QLabel, QApplication, QGraphicsPixmapItem
from PySide6.QtGui import QPen, QColor, QPainter, QPixmap, QCursor
from PySide6.QtCore import Qt, QRectF, QPoint
from typing import Optional
from enum import Enum
from models import CropArea
from constants import WB_MIN_DIVISOR, WB_MAX_HALF_SIZE, LOUPE_SIZES

# Zoom in/out factors
ZOOM_STEP = 1.2
ZOOM_IN_FACTOR = ZOOM_STEP
ZOOM_OUT_FACTOR = 1.0 / ZOOM_STEP

class ToolMode(Enum):
    NONE = 0
    WHITE_BALANCE = 1
    CROP = 2
    LOUPE = 3

class ImageView(QGraphicsView):
    """
    Custom QGraphicsView to handle mouse events for crop selection.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._start_pos = None
        self._rubber_band = None
        self.crop_area = CropArea()
        self._panning = False
        self._pan_start_pos = None
        self._tool_mode = ToolMode.NONE

        # --- Magnifier for WB mode ---
        self.magnifier = QLabel(self)
        self.magnifier.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.magnifier.setAttribute(Qt.WA_TranslucentBackground)
        self.magnifier.setFixedSize(138, 138)
        self.magnifier.hide()

        # --- Loupe for 1:1 preview ---
        self.loupe = QLabel(self)
        self.loupe.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.loupe.setAttribute(Qt.WA_TranslucentBackground)
        self.loupe.hide()
        self._loupe_size_index = 0

    def set_tool_mode(self, mode: ToolMode, message: Optional[str] = None):
        # --- Exit current mode ---
        if self._tool_mode == ToolMode.WHITE_BALANCE:
            self.magnifier.hide()
            self.setMouseTracking(False)
        elif self._tool_mode == ToolMode.CROP:
            self._clear_selection()
        elif self._tool_mode == ToolMode.LOUPE:
            self.loupe.hide()
            self.setMouseTracking(False)

        self._tool_mode = mode

        # --- Enter new mode ---
        if mode == ToolMode.WHITE_BALANCE:
            self.setCursor(Qt.CrossCursor)
            self.setMouseTracking(True)
            self.fit_to_view()
            self.setFocus()
            default_msg = "Click on a neutral gray area to apply white balance..."


        elif mode == ToolMode.LOUPE:
            self.setCursor(Qt.CrossCursor)
            self.setMouseTracking(True)
            self._loupe_size_index = 0
            self.loupe.show()
            self.setFocus()
            size = LOUPE_SIZES[self._loupe_size_index]
            default_msg = f"Loupe: {size}×{size} (click to cycle size)"

        elif mode == ToolMode.CROP:
            self.setCursor(Qt.CrossCursor)
            self.setMouseTracking(False)
            self._clear_selection()
            self.setFocus()
            default_msg = "Select area and press Enter to crop"

        elif mode == ToolMode.NONE:
            self.setCursor(Qt.ArrowCursor)
            self._clear_selection()
            default_msg = None

        else:
            self.setCursor(Qt.ArrowCursor)
            default_msg = None

        if message is None:
            msg = default_msg
        else:
            msg = message

        if msg is not None and hasattr(self.parent(), 'status_bar'):
            self.parent().status_bar.showMessage(msg)

    def set_pixmap(self, pixmap: Optional[QPixmap]):
        self._clear_selection()
        self.scene().clear()
        self._rubber_band = None

        if pixmap and not pixmap.isNull():
            item = QGraphicsPixmapItem(pixmap)
            self.scene().addItem(item)
            self.setSceneRect(self.scene().itemsBoundingRect())
            if self.parent():
                size = pixmap.size()
                self.parent().size_label.setText(f"Original Size: {size.width()}×{size.height()}")
                self.parent()._update_status_info()
            self.fit_to_view()
        else:
            self.setSceneRect(QRectF())
            if self.parent():
                self.parent().size_label.setText("Size:-")

    def mousePressEvent(self, event):
        if self._tool_mode == ToolMode.WHITE_BALANCE and event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos()).toPoint()
            pixmap = self.parent().image_model.current_pixmap
            if pixmap and not pixmap.isNull():
                x = max(0, min(pos.x(), pixmap.width() - 1))
                y = max(0, min(pos.y(), pixmap.height() - 1))
                self.parent().apply_white_balance(int(x), int(y))
            self.set_tool_mode(ToolMode.NONE, "White balance applied")
            event.accept()
            return

        if self._tool_mode == ToolMode.LOUPE and event.button() == Qt.LeftButton:
            self._loupe_size_index = (self._loupe_size_index + 1) % len(LOUPE_SIZES)
            new_size = LOUPE_SIZES[self._loupe_size_index]
            if hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage(f"Loupe size: {new_size}×{new_size}")
            self.mouseMoveEvent(event)  # uppdate loupe
            event.accept()
            return

        # Right click → Fit to Window (works everywhere)
        if event.button() == Qt.RightButton:
            self.set_tool_mode(ToolMode.NONE, "Fit to window")
            self.fit_to_view()
            event.accept()
            return

        if event.button() == Qt.LeftButton and self._tool_mode == ToolMode.CROP:
            click_pos = event.pos()
            self._start_pos = self.mapToScene(click_pos)
            if not self._rubber_band:
                pen = QPen(QColor(255, 0, 0), 8, Qt.DashLine)
                self._rubber_band = self.scene().addRect(
                    QRectF(self._start_pos.x(), self._start_pos.y(), 0, 0), pen
                )
            self.crop_area.reset()
            event.accept()
            return

        elif event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Double-click → Original Size
            self.reset_zoom()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if self._tool_mode == ToolMode.WHITE_BALANCE and self.parent():
            # Get coordinates on scene
            scene_pos = self.mapToScene(event.pos())
            x, y = int(scene_pos.x()), int(scene_pos.y())
            image_model = self.parent().image_model
            if image_model and image_model.current_pixmap:
                pixmap = image_model.current_pixmap
                w, h = pixmap.width(), pixmap.height()
                min_dim = min(w, h)
                half = min(WB_MAX_HALF_SIZE, max(1, min_dim // WB_MIN_DIVISOR))
                # Get rect coordinates (x, y)
                left = max(0, x - half)
                top = max(0, y - half)
                right = min(w, x + half)
                bottom = min(h, y + half)
                if right > left and bottom > top:
                    fragment = pixmap.copy(left, top, right - left, bottom - top)
                    display_size = (right - left) * 6
                    scaled = fragment.scaled(
                        display_size, display_size,
                        Qt.IgnoreAspectRatio,
                        Qt.FastTransformation
                    )
                    self.magnifier.setFixedSize(display_size, display_size)
                    self.magnifier.setPixmap(scaled)
                    self.magnifier.move(QCursor.pos() + QPoint(20, 20))
                    self.magnifier.show()
                else:
                    self.magnifier.hide()
            else:
                self.magnifier.hide()
        elif self._tool_mode == ToolMode.LOUPE and self.parent():
            scene_pos = self.mapToScene(event.pos())
            x, y = int(scene_pos.x()), int(scene_pos.y())
            image_model = self.parent().image_model
            if image_model and image_model.current_pixmap:
                pixmap = image_model.current_pixmap
                w, h = pixmap.width(), pixmap.height()
                size = LOUPE_SIZES[self._loupe_size_index]
                half = size // 2
                left = max(0, x - half)
                top = max(0, y - half)
                right = min(w, x + half)
                bottom = min(h, y + half)
                if right > left and bottom > top:
                    fragment = pixmap.copy(left, top, right - left, bottom - top)
                    self.loupe.setFixedSize(fragment.width(), fragment.height())
                    self.loupe.setPixmap(fragment)
                    self.loupe.move(QCursor.pos() + QPoint(20, 20))
                    self.loupe.show()
                else:
                    self.loupe.hide()
            else:
                self.loupe.hide()
        else:
            self.magnifier.hide()
            self.loupe.hide()

        if self._panning and self._pan_start_pos is not None:
            delta = event.pos() - self._pan_start_pos
            self._pan_start_pos = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return
        elif self._start_pos and self._rubber_band:
            current_pos = self.mapToScene(event.pos())
            rect = QRectF(self._start_pos, current_pos).normalized()
            self._rubber_band.setRect(rect)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if hasattr(self, 'magnifier') and self.magnifier:
            self.magnifier.hide()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._start_pos:
            final_pos = self.mapToScene(event.pos())
            rect = QRectF(self._start_pos, final_pos).normalized()
            # Convert to image coordinates
            # You can scale this properly if zoomed
            self.crop_area.set_rect(rect.toRect())
            self._start_pos = None

            if self.crop_area.is_active:
                size = self.crop_area.rect.size()
                if hasattr(self.parent(), 'status_bar'):
                    self.parent().status_bar.showMessage(f"Selected: {size.width()}×{size.height()} px")

        elif event.button() == Qt.MiddleButton:
            self._panning = False
            self._pan_start_pos = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            # Global Esc
            self.set_tool_mode(ToolMode.NONE, "Operation cancelled")
            return

        if self._tool_mode == ToolMode.CROP and event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self._apply_crop()
            event.accept()
            return

        super().keyPressEvent(event)

    def _clear_selection(self):
        """Clear current selection."""
        if self.crop_area.is_active:
            self.crop_area.reset()
            if self._rubber_band:
                try:
                    self.scene().removeItem(self._rubber_band)
                except RuntimeError:
                    pass
                self._rubber_band = None
            if hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage("Selection cleared")

    def _apply_crop(self):
        print(f"crop_area.is_active: {self.crop_area.is_active}")
        print(f"rect: {self.crop_area.rect}, isNull: {self.crop_area.rect.isNull()}")
        if not self.crop_area.is_active or self.crop_area.rect.isNull():
            self.set_tool_mode(ToolMode.NONE, "Crop cancelled: no valid selection")
            return
        if hasattr(self.parent(), 'finalize_crop'):
            self.parent().finalize_crop()
        self.set_tool_mode(ToolMode.NONE)

    def fit_to_view(self):
        """Fit image to view only if image is larger than view."""
        if hasattr(self.parent(), 'view_state'):
            self.parent().view_state.auto_fit_enabled = True
        self._auto_fit_limited()
        if not self.scene() or self.scene().itemsBoundingRect().isNull():
            return

        # Get image and view sizes
        image_rect = self.scene().itemsBoundingRect()
        view_rect = self.viewport().rect()

        # Check if image is larger than the view
        if (image_rect.width() > view_rect.width() or
                image_rect.height() > view_rect.height()):
            # Image is larger, so fit it to view
            self.fitInView(image_rect, Qt.KeepAspectRatio)
        else:
            # Image is smaller, center it without scaling
            self.resetTransform()  # Reset any existing scaling
            self.centerOn(image_rect.center())
            if hasattr(self.parent(), 'view_state'):
                self.parent().view_state.auto_fit_enabled = True

        self.update_zoom_display()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if (hasattr(self.parent(), 'view_state') and
                self.parent().view_state.auto_fit_enabled):
            self._auto_fit_limited()

    def _auto_fit_limited(self):
        """Fit to view only if image > viewport, otherwise show at 100%."""
        if not self.scene() or self.scene().itemsBoundingRect().isNull():
            return

        image_rect = self.scene().itemsBoundingRect()
        view_rect = self.viewport().rect()

        # Calculate scale needed to fit image in view
        sx = view_rect.width() / image_rect.width()
        sy = view_rect.height() / image_rect.height()
        scale = min(sx, sy)

        # Never scale above 100%
        if scale >= 1.0:
            # Show at original size, centered
            self.resetTransform()
            self.centerOn(image_rect.center())
        else:
            # Fit to view
            self.fitInView(image_rect, Qt.KeepAspectRatio)

        self.update_zoom_display()

    def wheelEvent(self, event):
        cursor_pos = event.position().toPoint()
        factor = ZOOM_IN_FACTOR if event.angleDelta().y() > 0 else ZOOM_OUT_FACTOR
        self._zoom_at_point(cursor_pos, factor)
        event.accept()

    def zoom_in(self):
        cursor_pos = self.mapFromGlobal(QCursor.pos())
        viewport_rect = self.viewport().rect()
        if viewport_rect.contains(cursor_pos):
            self._zoom_at_point(cursor_pos, ZOOM_IN_FACTOR)
        else:
            self._perform_zoom_simple(ZOOM_IN_FACTOR)

    def zoom_out(self):
        cursor_pos = self.mapFromGlobal(QCursor.pos())
        viewport_rect = self.viewport().rect()
        if viewport_rect.contains(cursor_pos):
            self._zoom_at_point(cursor_pos, ZOOM_OUT_FACTOR)
        else:
            self._perform_zoom_simple(ZOOM_OUT_FACTOR)

    def _zoom_at_point(self, cursor_pos, factor):
        """Zoom with cursor 'sticking' to the same image point."""
        if hasattr(self.parent(), 'view_state'):
            self.parent().view_state.auto_fit_enabled = False

        self.set_tool_mode(ToolMode.NONE)
        if not self.scene() or self.scene().itemsBoundingRect().isNull():
            return

        scene_pos_before = self.mapToScene(cursor_pos)
        self.scale(factor, factor)
        scene_pos_after = self.mapToScene(cursor_pos)
        delta = scene_pos_after - scene_pos_before
        current_center = self.mapToScene(self.viewport().rect().center())
        self.centerOn(current_center - delta)
        self.update_zoom_display()

    def _perform_zoom_simple(self, factor):
        """Fallback zoom when cursor is outside view (e.g. via keyboard focus without mouse)."""
        if hasattr(self.parent(), 'view_state'):
            self.parent().view_state.auto_fit_enabled = False

        self.set_tool_mode(ToolMode.NONE)
        if not self.scene() or self.scene().itemsBoundingRect().isNull():
            return
        self.scale(factor, factor)
        self.centerOn(self.scene().itemsBoundingRect().center())
        self.update_zoom_display()

    def reset_zoom(self):
        if hasattr(self.parent(), 'view_state'):
            self.parent().view_state.auto_fit_enabled = False

        if not self.scene() or self.scene().itemsBoundingRect().isNull():
            return

        cursor_pos = self.mapFromGlobal(QCursor.pos())
        viewport_rect = self.viewport().rect()

        if viewport_rect.contains(cursor_pos):
            target = self.mapToScene(cursor_pos)
        else:
            target = self.scene().itemsBoundingRect().center()

        self.resetTransform()
        self.centerOn(target)
        self.update_zoom_display()

    def update_zoom_display(self):
        """Update zoom label with current scale."""
        transform = self.transform()
        zoom_x = transform.m11()
        zoom_percent = int(zoom_x * 100)
        if hasattr(self.parent(), 'zoom_label'):
            self.parent().zoom_label.setText(f"Zoom: {zoom_percent}%")

    def clear_selection(self):
        """Public method to clear selection from outside."""
        self._clear_selection()
