from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QPen, QColor
from PySide6.QtCore import Qt, QRectF
from models import CropArea

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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            current_pos = self.mapToScene(event.pos())

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
        elif event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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
        """Handle Esc key to clear selection."""
        if event.key() == Qt.Key_Escape:
            self._clear_selection()
            event.accept()
        else:
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

    def wheelEvent(self, event):
        """Zoom in/out with Ctrl + mouse wheel."""
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

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
        """Zoom in, focusing on selection if available."""
        if self.crop_area.is_active and not self.crop_area.rect.isNull():
            # Zoom to selection
            self._zoom_to_selection(1.25)
        else:
            # Normal zoom
            self.scale(1.25, 1.25)
        self.update_zoom_display()

    def zoom_out(self):
        """Zoom out, focusing on selection if available."""
        if self.crop_area.is_active and not self.crop_area.rect.isNull():
            # Zoom out from selection
            self._zoom_to_selection(0.8)
        else:
            # Normal zoom
            self.scale(0.8, 0.8)
        self.update_zoom_display()

    def _zoom_to_selection(self, scale_factor):
        """Zoom with focus on the selected area."""
        if not self.crop_area.is_active or self.crop_area.rect.isNull():
            return

        # Get the center of the selection in scene coordinates
        selection_center = self.crop_area.rect.center()

        # Apply the scale factor
        self.scale(scale_factor, scale_factor)

        # Center the view on the selection center
        self.centerOn(selection_center)

    def reset_zoom(self):
        """Reset to original size (1:1)."""
        self.resetTransform()
        # Do NOT refit to view — we want 1:1 pixel ratio
        # Center on selection if available, otherwise on the whole image
        if self.crop_area.is_active and not self.crop_area.rect.isNull():
            # If there's an active selection, center on it
            self.centerOn(self.crop_area.rect.center())
        else:
            # Otherwise, center on the whole image
            self.centerOn(self.scene().itemsBoundingRect().center())
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