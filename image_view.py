from PySide6.QtWidgets import QGraphicsView, QLabel, QApplication, QGraphicsPixmapItem
from PySide6.QtGui import QPen, QColor, QPainter, QPixmap, QCursor
from PySide6.QtCore import Qt, QRectF, QPoint
from typing import Optional
from enum import Enum
from models import CropArea
from constants import WB_MIN_DIVISOR, WB_MAX_HALF_SIZE

class ToolMode(Enum):
    NONE = 0
    WHITE_BALANCE = 1
    CROP = 2
    ZOOM_FOCUS = 3
    COPY_AREA = 4

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
        self._click_timer = None
        self._tool_mode = ToolMode.NONE
        self.zoom_focus_point = None

        # --- Magnifier for WB mode ---
        self.magnifier = QLabel(self)
        self.magnifier.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.magnifier.setAttribute(Qt.WA_TranslucentBackground)
        self.magnifier.setFixedSize(138, 138)
        self.magnifier.hide()
        self.magnifier_half_size = 11

    def set_tool_mode(self, mode: ToolMode):
        # --- Exit current mode ---
        if self._tool_mode == ToolMode.WHITE_BALANCE:
            self.magnifier.hide()
            self.setMouseTracking(False)
        elif self._tool_mode in (ToolMode.CROP, ToolMode.COPY_AREA):
            self._clear_selection()

        self._tool_mode = mode

        # --- Enter new mode ---
        if mode == ToolMode.WHITE_BALANCE:
            self.setCursor(Qt.CrossCursor)
            self.setMouseTracking(True)
            self.setFocus()
            if hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage("Click on neutral area...")

        elif mode == ToolMode.CROP:
            self.setCursor(Qt.CrossCursor)
            self.setMouseTracking(False)
            self._clear_selection()
            self.setFocus()
            if hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage("Select area and press Enter to crop...")

        elif mode == ToolMode.COPY_AREA:
            self.setCursor(Qt.CrossCursor)
            self.setMouseTracking(False)
            self._clear_selection()
            self.setFocus()
            if hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage("Select area and press Enter to copy...")

        elif mode == ToolMode.ZOOM_FOCUS:
            self.setCursor(Qt.CrossCursor)
            self.setMouseTracking(False)
            self.zoom_focus_point = None
            if hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage("Click to set zoom focus...")

        elif mode == ToolMode.NONE:
            self.setCursor(Qt.ArrowCursor)
            self._clear_selection()

        else:
            # fallback
            self.setCursor(Qt.ArrowCursor)

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
        if self._tool_mode == ToolMode.ZOOM_FOCUS and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.zoom_focus_point = scene_pos
            self.set_tool_mode(ToolMode.NONE)  # выход из режима после выбора
            if hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage(f"Zoom focus set to ({int(scene_pos.x())}, {int(scene_pos.y())})")
            event.accept()
            return
        if self._tool_mode == ToolMode.WHITE_BALANCE and event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos()).toPoint()
            pixmap = self.parent().image_model.current_pixmap
            if pixmap and not pixmap.isNull():
                x = max(0, min(pos.x(), pixmap.width() - 1))
                y = max(0, min(pos.y(), pixmap.height() - 1))
                self.parent().apply_white_balance(int(x), int(y))
            self.set_tool_mode(ToolMode.NONE)
            event.accept()
            return

        # Right click → Fit to Window (works everywhere)
        if event.button() == Qt.RightButton:
            self.set_tool_mode(ToolMode.NONE)
            self.fit_to_view()
            event.accept()
            return

        if event.button() == Qt.LeftButton and self._tool_mode in (ToolMode.CROP, ToolMode.COPY_AREA):
            click_pos = event.pos()
            # Cancel any pending double-click detection for crop
            if self._click_timer is not None:
                self._click_timer.stop()
                self._click_timer = None
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
            # Cancel pending single-click action
            if self._click_timer is not None:
                self._click_timer.stop()
                self._click_timer = None

            # Double-click → Original Size
            self.reset_zoom()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _process_single_click(self, pos):
        self._click_timer = None
        current_pos = self.mapToScene(pos)

        if (self.crop_area.is_active and
                not self.crop_area.rect.contains(current_pos.toPoint())):
            self._clear_selection()
            return

        self._start_pos = current_pos
        if not self._rubber_band:
            pen = QPen(QColor(255, 0, 0), 8, Qt.DashLine)
            self._rubber_band = self.scene().addRect(
                QRectF(self._start_pos.x(), self._start_pos.y(), 0, 0),
                pen
            )
        self.crop_area.reset()

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
        else:
            self.magnifier.hide()

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
        if self._tool_mode == ToolMode.CROP:
            if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                self._apply_crop()
                event.accept()
                return
            elif event.key() == Qt.Key_Escape:
                self._exit_crop_mode()
                event.accept()
                return

        elif self._tool_mode == ToolMode.COPY_AREA:
            if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                self._apply_copy_area()
                event.accept()
                return
            elif event.key() == Qt.Key_Escape:
                self._exit_copy_area_mode()
                event.accept()
                return

        if event.key() == Qt.Key_Escape:
            # Global Esc
            self.zoom_focus_point = None
            self.set_tool_mode(ToolMode.NONE)
            if hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage("Operation cancelled")
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
            self._exit_crop_mode()
            return
        if hasattr(self.parent(), 'finalize_crop'):
            self.parent().finalize_crop()
        self.set_tool_mode(ToolMode.NONE)

    def _apply_copy_area(self):
        if not self.crop_area.is_active or self.crop_area.rect.isNull():
            self._exit_copy_area_mode()
            return
        if hasattr(self.parent(), 'copy_selected_area'):
            self.parent().copy_selected_area()
        self.set_tool_mode(ToolMode.NONE)

    def _exit_copy_area_mode(self):
        self.setCursor(Qt.ArrowCursor)
        self._clear_selection()
        if hasattr(self.parent(), 'status_bar'):
            self.parent().status_bar.showMessage("Copy selection cancelled")
        self.set_tool_mode(ToolMode.NONE)

    def _exit_crop_mode(self):
        self.setCursor(Qt.ArrowCursor)
        self._clear_selection()
        if hasattr(self.parent(), 'status_bar'):
            self.parent().status_bar.showMessage("Crop cancelled")

    def wheelEvent(self, event):
        """Zoom in/out with mouse wheel."""
        if event.angleDelta().y() > 0:
            self.zoom_out()
        else:
            self.zoom_in()
        event.accept()

    def fit_to_view(self):
        """Fit image to view only if image is larger than view."""
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

        self.update_zoom_display()

    def zoom_in(self):
        self._perform_zoom(1.25)

    def zoom_out(self):
        self._perform_zoom(0.8)

    def _perform_zoom(self, factor):
        self.set_tool_mode(ToolMode.NONE)  # выход из любых режимов
        self.scale(factor, factor)

        # Центрируем на zoom_focus_point, если задана, иначе — на центр сцены
        target = self.zoom_focus_point if self.zoom_focus_point else self.scene().itemsBoundingRect().center()
        self.centerOn(target)

        self.update_zoom_display()

    def reset_zoom(self):
        self.resetTransform()
        target = self.zoom_focus_point if self.zoom_focus_point else self.scene().itemsBoundingRect().center()
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

