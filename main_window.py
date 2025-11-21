import os, sys
from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QGraphicsPixmapItem,
    QStatusBar, QFileDialog, QLabel, QMessageBox
)

from PySide6.QtGui import QAction, QKeySequence, QIcon
from models import ImageModel, NavigatorModel, ViewState, ClipboardModel

from image_helpers import ExifHelper, ResizeHelper, SaveHelper, move_to_trash
from image_view import ImageView
import resources_rc


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt Image Viewer")
        self.setGeometry(100, 100, 1024, 768)
        app_icon = QIcon(":/icons/qiv.svg")
        self.setWindowIcon(app_icon)

        # Models
        self.image_model = ImageModel()
        self.navigator_model = NavigatorModel()
        self.view_state = ViewState()
        self.clipboard_model = ClipboardModel()

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        # Central widget: ImageView
        self.view = ImageView(self)
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)

        # Actions
        self.open_action = QAction(QIcon(":/icons/folder-open.svg"), "Open", self)
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.triggered.connect(self.open_image)

        self.save_action = QAction(QIcon(":/icons/save.svg"), "Save", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.triggered.connect(self.save_image)

        self.reload_action = QAction(QIcon(":/icons/reload.svg"), "Reload", self)
        self.reload_action.setShortcut("Ctrl+R")
        self.reload_action.triggered.connect(self.reload_image)

        self.new_window_action = QAction(QIcon(":/icons/new-file.svg"), "New Window", self)
        self.new_window_action.setShortcut("Ctrl+N")
        self.new_window_action.triggered.connect(self.new_window)

        self.rotate_cw_action = QAction(QIcon(":/icons/cw.svg"), "Rotate CW", self)
        self.rotate_cw_action.setShortcut("R")
        self.rotate_cw_action.triggered.connect(self.rotate_cw)

        self.rotate_ccw_action = QAction(QIcon(":/icons/ccw.svg"), "Rotate CCW", self)
        self.rotate_ccw_action.setShortcut("L")
        self.rotate_ccw_action.triggered.connect(self.rotate_ccw)

        self.flip_h_action = QAction(QIcon(":/icons/flip-h.svg"), "Flip Horizontal", self)
        self.flip_h_action.setShortcut("H")
        self.flip_h_action.triggered.connect(self.flip_horizontal)

        self.flip_v_action = QAction(QIcon(":/icons/flip-v.svg"), "Flip Vertical", self)
        self.flip_v_action.setShortcut("V")
        self.flip_v_action.triggered.connect(self.flip_vertical)

        self.crop_action = QAction(QIcon(":/icons/crop.svg"), "Crop", self)
        self.crop_action.setShortcut(QKeySequence.Cut)
        self.crop_action.triggered.connect(self.crop_image)

        self.copy_action = QAction(QIcon(":/icons/copy.svg"), "Copy", self)
        self.copy_action.setShortcut(QKeySequence.Copy)
        self.copy_action.triggered.connect(self.copy_image)

        self.paste_action = QAction(QIcon(":/icons/paste.svg"), "Paste", self)
        self.paste_action.setShortcut(QKeySequence.Paste)
        self.paste_action.triggered.connect(self.paste_image)

        self.next_action = QAction(QIcon(":/icons/arrow-right.svg"), "Next Image", self)
        self.next_action.setShortcut("N")
        self.next_action.triggered.connect(self.next_image)

        self.previous_action = QAction(QIcon(":/icons/arrow-left.svg"), "Previous Image", self)
        self.previous_action.setShortcut("Shift+N")
        self.previous_action.triggered.connect(self.previous_image)

        # Zoom Actions
        self.zoom_in_action = QAction(QIcon(":/icons/zoom-in.svg"), "Zoom In", self)
        self.zoom_in_action.setShortcut("+")
        self.zoom_in_action.triggered.connect(self.view.zoom_in)

        self.zoom_out_action = QAction(QIcon(":/icons/zoom-out.svg"), "Zoom Out", self)
        self.zoom_out_action.setShortcut("-")
        self.zoom_out_action.triggered.connect(self.view.zoom_out)

        self.original_size_action = QAction(QIcon(":/icons/zoom-original.svg"), "Original Size", self)
        self.original_size_action.setShortcut("=")
        self.original_size_action.triggered.connect(self.view.reset_zoom)

        self.fit_to_window_action = QAction(QIcon(":/icons/zoom-fit.svg"), "Fit To Window", self)
        self.fit_to_window_action.setShortcut("W")
        self.fit_to_window_action.triggered.connect(self.view.fit_to_view)

        # EXIF
        self.exif_action = QAction(QIcon(":/icons/info.svg"), "Show EXIF", self)
        self.exif_action.triggered.connect(self.show_exif)

        # Resize
        self.resize_action = QAction(QIcon(":/icons/resize.svg"), "Resize", self)
        self.resize_action.setShortcut("Ctrl+T")
        self.resize_action.triggered.connect(self.resize_image)

        self.delete_action = QAction(QIcon(":/icons/trash.svg"), "Move to Trash", self)
        self.delete_action.setShortcut("Delete")
        self.delete_action.triggered.connect(self.delete_current_file)

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence("Q"))
        self.exit_action.triggered.connect(self.close)

        self.help_action = QAction(QIcon(":/icons/help.svg"), "About", self)
        self.help_action.setShortcut("F1")
        self.help_action.triggered.connect(self.show_help)

        # Menus
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self.new_window_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.reload_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.delete_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")
        edit_menu.addAction(self.rotate_cw_action)
        edit_menu.addAction(self.rotate_ccw_action)
        edit_menu.addAction(self.flip_h_action)
        edit_menu.addAction(self.flip_v_action)
        edit_menu.addAction(self.resize_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.copy_action)
        edit_menu.addAction(self.paste_action)
        edit_menu.addAction(self.crop_action)

        # NEW: Zoom menu
        view_menu = menu_bar.addMenu("Zoom")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addSeparator()
        view_menu.addAction(self.fit_to_window_action)
        view_menu.addAction(self.original_size_action)

        # GO menu
        go_menu = menu_bar.addMenu("Go")
        go_menu.addAction(self.previous_action)
        go_menu.addAction(self.next_action)

        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction(self.help_action)

        # Toolbar
        toolbar = self.addToolBar("Tools")
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.new_window_action)
        toolbar.addAction(self.save_action)
        toolbar.addAction(self.reload_action)
        toolbar.addAction(self.delete_action)

        toolbar.addSeparator()
        toolbar.addAction(self.previous_action)
        toolbar.addAction(self.next_action)

        toolbar.addSeparator()
        toolbar.addAction(self.crop_action)
        toolbar.addAction(self.copy_action)
        toolbar.addAction(self.paste_action)

        toolbar.addSeparator()
        toolbar.addAction(self.rotate_cw_action)
        toolbar.addAction(self.rotate_ccw_action)
        toolbar.addAction(self.flip_h_action)
        toolbar.addAction(self.flip_v_action)
        toolbar.addAction(self.resize_action)

        toolbar.addSeparator()
        toolbar.addAction(self.zoom_in_action)
        toolbar.addAction(self.zoom_out_action)
        toolbar.addAction(self.fit_to_window_action)
        toolbar.addAction(self.original_size_action)

        toolbar.addSeparator()
        toolbar.addAction(self.exif_action)

        toolbar.addSeparator()
        toolbar.addAction(self.help_action)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Zoom label
        self.zoom_label = QLabel("Zoom: -")
        self.size_label = QLabel("Size: -")

        self.status_bar.addPermanentWidget(self.size_label)
        self.status_bar.addPermanentWidget(self.zoom_label)

    def load_file_from_args(self):
        """Load file passed as command-line argument."""
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            if os.path.isfile(file_path):
                if self.image_model.load_from_path(file_path):
                    self.navigator_model.set_current_path(file_path)
                    self.display_image()
                    self._update_status_info()
                    formatted_path = self.navigator_model.format_path_for_display(file_path)
                    self.status_bar.showMessage(f"Opened: {formatted_path}")
                else:
                    print(f"Could not load image: {file_path}", file=sys.stderr)
            else:
                print(f"File not found: {file_path}", file=sys.stderr)

    def open_image(self):
        home_dir = os.path.expanduser("~")
        dialog = QFileDialog(self, "Open Image", home_dir, "Images (*.png *.xpm *.jpg *.jpeg *.bmp)")
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)  # Добавлено
        if dialog.exec() == QFileDialog.Accepted:
            path = dialog.selectedFiles()[0]
            if path and self.image_model.load_from_path(path):
                self.navigator_model.set_current_path(path)
                self.display_image()
                self._update_status_info()
                formatted_path = self.navigator_model.format_path_for_display(path)
                self.status_bar.showMessage(f"Opened: {formatted_path}")

    def reload_image(self):
        """Reload current image from file."""
        if self.image_model.path:
            if self.image_model.reload_from_path():
                # Update navigator, path hadn't changed
                self.navigator_model.set_current_path(self.image_model.path)
                self.display_image()
                self.status_bar.showMessage(f"Reloaded: {self.image_model.path}")
            else:
                self.status_bar.showMessage("Failed to reload image")
        else:
            self.status_bar.showMessage("No file to reload")

    def new_window(self):
        """Create a new instance of the application."""
        import subprocess
        import sys

        main_file = sys.argv[0]
        subprocess.Popen([sys.executable, main_file])

    def _navigate_image(self, direction):
        """Generic logic for navigating to an image."""
        new_path = self.navigator_model.navigate(direction)

        if new_path and self.image_model.load_from_path(new_path):
            self.display_image()
            self._update_status_info()
            formatted_path = self.navigator_model.format_path_for_display(new_path)
            self.status_bar.showMessage(f"Loaded: {formatted_path}")
        else:
            self.status_bar.showMessage(f"No {direction} image")

    def next_image(self):
        self._navigate_image("next")

    def previous_image(self):
        self._navigate_image("previous")

    def _update_status_info(self):
        """Update status bar with current file number and total count."""
        if self.navigator_model.total_count > 0:
            current_index = self.navigator_model.current_file_index + 1  # 1-based
            total_count = self.navigator_model.total_count
            filename = self.navigator_model.current_filename

            # Update status bar
            self.size_label.setText(f"{current_index}/{total_count} - {filename}")
        else:
            if self.image_model.current_pixmap:
                size = self.image_model.current_pixmap.size()
                self.size_label.setText(f"Original Size: {size.width()}×{size.height()}")
            else:
                self.size_label.setText("Size: -")

    def paste_image(self):
        if self.image_model.load_from_clipboard():
            self.display_image()
            self.status_bar.showMessage("Pasted image from clipboard")

    def display_image(self):
        self.scene.clear()
        if self.image_model.current_pixmap:
            pixmap_item = QGraphicsPixmapItem(self.image_model.current_pixmap)
            self.scene.addItem(pixmap_item)
            self.view.setSceneRect(self.scene.itemsBoundingRect())

            # Update status-bar
            size = self.image_model.current_pixmap.size()
            self.size_label.setText(f"Original Size: {size.width()}×{size.height()}")

            # Update file navigation info
            self._update_status_info()

            # Fit in view only if image is larger than window
            self.view.fit_to_view()

    def rotate_cw(self):
        self.image_model.rotate_90_clockwise()
        self.view.clear_selection()
        self.display_image()

    def rotate_ccw(self):
        self.image_model.rotate_90_counterclockwise()
        self.view.clear_selection()
        self.display_image()

    def flip_horizontal(self):
        """Flip image horizontally."""
        self.image_model.flip_horizontal()
        # Clear selection after flip since coordinates become invalid
        self.view.clear_selection()
        self.display_image()

    def flip_vertical(self):
        """Flip image vertically."""
        self.image_model.flip_vertical()
        # Clear selection after flip since coordinates become invalid
        self.view.clear_selection()
        self.display_image()

    def crop_image(self):
        if not self.image_model.current_pixmap or not self.view.crop_area.is_active:
            return

        rect = self.view.crop_area.rect
        cropped = self.image_model.current_pixmap.copy(rect)
        self.image_model.current_pixmap = cropped
        self.image_model.original_pixmap = cropped  # Update original to cropped

        # NEW: Copy cropped image to clipboard automatically
        self.clipboard_model.copy_image(cropped)
        self.status_bar.showMessage("Cropped image copied to clipboard")

        self.view.clear_selection()

        # Reset crop area
        self.view.crop_area.reset()

        # Remove rubber band safely
        if self.view._rubber_band:
            self.scene.removeItem(self.view._rubber_band)
            self.view._rubber_band = None

        # Re-display the image
        self.display_image()

    def copy_image(self):
        """Copy current image or selected area to clipboard."""
        if not self.image_model.current_pixmap:
            return

        if self.view.crop_area.is_active and not self.view.crop_area.rect.isNull():
            cropped = self.image_model.current_pixmap.copy(self.view.crop_area.rect)
            self.clipboard_model.copy_image(cropped)
            self.status_bar.showMessage("Selected area copied to clipboard")
        else:
            self.clipboard_model.copy_image(self.image_model.current_pixmap)
            self.status_bar.showMessage("Image copied to clipboard")

    def show_exif(self):
        """Show EXIF data in a separate dialog."""

        if not self.image_model.path:
            self.status_bar.showMessage("No image loaded from file")
            return

        success = ExifHelper.show_exif_data(self, self.image_model.path)
        if not success:
            self.status_bar.showMessage("No EXIF data or failed to read")

    def save_image(self):
        """Save image with proper format handling."""
        if not self.image_model.current_pixmap:
            return

        initial_path = self.image_model.path if self.image_model.path else ""
        dialog = QFileDialog(self, "Save Image", initial_path,
                             "JPEG (*.jpg *.jpeg);;PNG (*.png);;WEBP (*.webp);;BMP (*.bmp)")
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)  # Use Qt's dialog for consistency
        dialog.setAcceptMode(QFileDialog.AcceptSave)  # Ensure it's a save dialog
        if dialog.exec() == QFileDialog.Accepted:
            selected_files = dialog.selectedFiles()
            if not selected_files:
                return
            path = selected_files[0]
            selected_filter = dialog.selectedNameFilter()

            # Add extension if not provided
            path = SaveHelper.ensure_extension(path, selected_filter)

            # Determine format from extension and handle quality
            if path.lower().endswith((".jpg", ".jpeg")):
                quality = SaveHelper.get_quality_for_format(self, "JPEG")
                if quality is None:  # User cancelled
                    return
                success = self.image_model.save(path, "JPEG", quality)
            elif path.lower().endswith(".webp"):
                quality = SaveHelper.get_quality_for_format(self, "WEBP")
                if quality is None:  # User cancelled
                    return
                success = self.image_model.save(path, "WEBP", quality)
            elif path.lower().endswith(".png"):
                success = self.image_model.save(path, "PNG")
            elif path.lower().endswith(".bmp"):
                success = self.image_model.save(path, "BMP")
            else:
                # Default to PNG if extension not recognized
                if not any(path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']):
                    path += '.png'
                success = self.image_model.save(path, "PNG")

            if success:
                if path == self.image_model.path:
                    self.image_model.path = path
                self.status_bar.showMessage(f"Saved: {path}")
            else:
                self.status_bar.showMessage(f"Failed to save: {path}")

    def resize_image(self):
        """Resize image with aspect ratio preservation."""
        if not self.image_model.current_pixmap:
            return

        width, height = ResizeHelper.resize_with_aspect_ratio(
            self,
            self.image_model.current_pixmap,
            self.image_model.current_pixmap.width(),
            self.image_model.current_pixmap.height()
        )

        if width is not None and height is not None:
            self.image_model.resize(width, height)
            self.view.clear_selection()
            self.display_image()
            self.status_bar.showMessage(f"Resized to {width}×{height}")

    def delete_current_file(self):
        """Move current file to trash."""
        if not self.image_model.path:
            self.status_bar.showMessage("No file to delete")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Move '{os.path.basename(self.image_model.path)}' to trash?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if move_to_trash(self.image_model.path):
                self.status_bar.showMessage(f"Moved to trash: {os.path.basename(self.image_model.path)}")

                if self.navigator_model.has_next():
                    next_path = self.navigator_model.get_next_path()
                    if self.image_model.load_from_path(next_path):
                        self.navigator_model.set_current_path(next_path)
                        self.display_image()
                        self._update_status_info()
                elif self.navigator_model.has_previous():
                    prev_path = self.navigator_model.get_previous_path()
                    if self.image_model.load_from_path(prev_path):
                        self.navigator_model.set_current_path(prev_path)
                        self.display_image()
                        self._update_status_info()
                else:
                    self.image_model.path = None
                    self.image_model.current_pixmap = None
                    self.image_model.original_pixmap = None
                    self.display_image()
            else:
                self.status_bar.showMessage("Failed to move file to trash")

    def show_help(self):
        """Show the About dialog."""
        from about_dialog import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec() # exec() modal one, show() - not modal


