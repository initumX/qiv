import os, sys, subprocess

from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QStatusBar, QFileDialog,
    QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QIcon

from models import ImageModel, NavigatorModel, ViewState, ClipboardModel
from image_helpers import ExifHelper, ResizeHelper, SaveHelper, move_to_trash
from image_view import ImageView, ToolMode
import resources_rc


class MainWindow(QMainWindow):
    """
    Main application window that coordinates models, views, and user actions.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt Image Viewer")
        self.setGeometry(100, 100, 1024, 768)
        self.setWindowIcon(QIcon(":/icons/qiv.svg"))
        self.setFocusPolicy(Qt.StrongFocus)

        # Models
        self.image_model = ImageModel()
        self.navigator_model = NavigatorModel()
        self.view_state = ViewState()
        self.clipboard_model = ClipboardModel()

        # Setup UI and load optional file from CLI
        self.setup_ui()
        self.load_file_from_args()

    def setup_ui(self):
        """Initialize central widget, actions, menus, toolbar, and status bar."""
        self.view = ImageView(self)
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)

        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._create_status_bar()

    def _create_actions(self):
        """Define all user-triggered actions."""
        # File actions
        self.open_action = QAction(QIcon(":/icons/folder-open.svg"), "Open", self)
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.triggered.connect(self.open_image)

        self.save_action = QAction(QIcon(":/icons/save.svg"), "Save", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.triggered.connect(lambda: self._safe_call(self.save_image))

        self.reload_action = QAction(QIcon(":/icons/reload.svg"), "Reload", self)
        self.reload_action.setShortcut("F5")
        self.reload_action.triggered.connect(lambda: self._safe_call(self.reload_image))

        self.new_window_action = QAction(QIcon(":/icons/new-file.svg"), "New Window", self)
        self.new_window_action.setShortcut("Ctrl+N")
        self.new_window_action.triggered.connect(self.new_window)

        self.delete_action = QAction(QIcon(":/icons/trash.svg"), "Move to Trash", self)
        self.delete_action.setShortcut("Delete")
        self.delete_action.triggered.connect(lambda: self._safe_call(self.delete_current_file))

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Q")
        self.exit_action.triggered.connect(self.close)

        # Edit actions
        self.rotate_cw_action = QAction(QIcon(":/icons/cw.svg"), "Rotate CW", self)
        self.rotate_cw_action.setShortcut("R")
        self.rotate_cw_action.triggered.connect(lambda: self._safe_call(self.rotate_cw))

        self.rotate_ccw_action = QAction(QIcon(":/icons/ccw.svg"), "Rotate CCW", self)
        self.rotate_ccw_action.setShortcut("L")
        self.rotate_ccw_action.triggered.connect(lambda: self._safe_call(self.rotate_ccw))

        self.flip_h_action = QAction(QIcon(":/icons/flip-h.svg"), "Flip Horizontal", self)
        self.flip_h_action.setShortcut("H")
        self.flip_h_action.triggered.connect(lambda: self._safe_call(self.flip_horizontal))

        self.flip_v_action = QAction(QIcon(":/icons/flip-v.svg"), "Flip Vertical", self)
        self.flip_v_action.setShortcut("V")
        self.flip_v_action.triggered.connect(lambda: self._safe_call(self.flip_vertical))

        self.crop_action = QAction(QIcon(":/icons/crop.svg"), "Crop", self)
        self.crop_action.setShortcut(QKeySequence.Cut)
        self.crop_action.triggered.connect(lambda: self._safe_call(self.crop_image))

        self.copy_action = QAction(QIcon(":/icons/copy.svg"), "Copy", self)
        self.copy_action.setShortcut(QKeySequence.Copy)
        self.copy_action.triggered.connect(lambda: self._safe_call(self.copy_image))

        self.paste_action = QAction(QIcon(":/icons/paste.svg"), "Paste", self)
        self.paste_action.setShortcut(QKeySequence.Paste)
        self.paste_action.triggered.connect(self.paste_image)

        self.resize_action = QAction(QIcon(":/icons/resize.svg"), "Resize", self)
        self.resize_action.setShortcut("Ctrl+T")
        self.resize_action.triggered.connect(lambda: self._safe_call(self.resize_image))

        # Zoom actions
        self.zoom_in_action = QAction(QIcon(":/icons/zoom-in.svg"), "Zoom In", self)
        self.zoom_in_action.setShortcut("+")
        self.zoom_in_action.triggered.connect(lambda: self._safe_call(self.view.zoom_in))

        self.zoom_out_action = QAction(QIcon(":/icons/zoom-out.svg"), "Zoom Out", self)
        self.zoom_out_action.setShortcut("-")
        self.zoom_out_action.triggered.connect(lambda: self._safe_call(self.view.zoom_out))

        self.original_size_action = QAction(QIcon(":/icons/zoom-original.svg"), "Original Size", self)
        self.original_size_action.setShortcut("=")
        self.original_size_action.triggered.connect(lambda: self._safe_call(self.view.reset_zoom))

        self.fit_to_window_action = QAction(QIcon(":/icons/zoom-fit.svg"), "Fit To Window", self)
        self.fit_to_window_action.setShortcut("W")
        self.fit_to_window_action.triggered.connect(lambda: self._safe_call(self.view.fit_to_view))

        self.loupe_action = QAction(QIcon(":/icons/loupe.svg"), "Loupe (1:1 Preview)", self)
        self.loupe_action.setShortcut("Ctrl+L")
        self.loupe_action.triggered.connect(lambda: self._safe_call(self.toggle_loupe_mode))

        # Navigation actions
        self.next_action = QAction(QIcon(":/icons/arrow-right.svg"), "Next Image", self)
        self.next_action.setShortcut("N")
        self.next_action.triggered.connect(self.next_image)

        self.previous_action = QAction(QIcon(":/icons/arrow-left.svg"), "Previous Image", self)
        self.previous_action.setShortcut("Shift+N")
        self.previous_action.triggered.connect(self.previous_image)

        # Info / tool actions
        self.exif_action = QAction(QIcon(":/icons/info.svg"), "Show EXIF", self)
        self.exif_action.triggered.connect(lambda: self._safe_call(self.show_exif))

        self.wb_action = QAction(QIcon(":/icons/wb.svg"), "White Balance (Click Neutral)", self)
        self.wb_action.triggered.connect(lambda: self._safe_call(self.toggle_wb_mode))

        # Help
        self.help_action = QAction(QIcon(":/icons/help.svg"), "About", self)
        self.help_action.setShortcut("F1")
        self.help_action.triggered.connect(self.show_help)

    def _create_menus(self):
        """Build the menu bar."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self.new_window_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.reload_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.delete_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

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

        view_menu = menu_bar.addMenu("Zoom")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addSeparator()
        view_menu.addAction(self.fit_to_window_action)
        view_menu.addAction(self.original_size_action)

        go_menu = menu_bar.addMenu("Go")
        go_menu.addAction(self.previous_action)
        go_menu.addAction(self.next_action)

        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction(self.help_action)

    def _create_toolbar(self):
        """Build the main toolbar."""
        toolbar = self.addToolBar("Tools")
        # File group
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.new_window_action)
        toolbar.addAction(self.save_action)
        toolbar.addAction(self.reload_action)
        toolbar.addAction(self.delete_action)
        toolbar.addSeparator()
        # Navigation
        toolbar.addAction(self.previous_action)
        toolbar.addAction(self.next_action)
        toolbar.addSeparator()
        # Edit
        toolbar.addAction(self.crop_action)
        toolbar.addAction(self.copy_action)
        toolbar.addAction(self.paste_action)
        toolbar.addAction(self.resize_action)
        toolbar.addAction(self.wb_action)
        toolbar.addSeparator()
        # Transform
        toolbar.addAction(self.rotate_cw_action)
        toolbar.addAction(self.rotate_ccw_action)
        toolbar.addAction(self.flip_h_action)
        toolbar.addAction(self.flip_v_action)
        toolbar.addSeparator()
        # Zoom
        toolbar.addAction(self.loupe_action)
        toolbar.addAction(self.zoom_in_action)
        toolbar.addAction(self.zoom_out_action)
        toolbar.addAction(self.fit_to_window_action)
        toolbar.addAction(self.original_size_action)
        toolbar.addSeparator()
        # Info & help
        toolbar.addAction(self.exif_action)
        toolbar.addSeparator()
        toolbar.addAction(self.help_action)

    def _create_status_bar(self):
        """Initialize status bar with persistent widgets."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.zoom_label = QLabel("Zoom: -")
        self.size_label = QLabel("Size: -")
        self.status_bar.addPermanentWidget(self.size_label)
        self.status_bar.addPermanentWidget(self.zoom_label)

    def _safe_call(self, func, message="No image loaded"):
        """Execute function only if an image is loaded."""
        if not self.image_model.current_pixmap or self.image_model.current_pixmap.isNull():
            self.status_bar.showMessage(message)
            return
        func()

    def load_file_from_args(self):
        """Load image from command-line argument if provided."""
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            if os.path.isfile(file_path) and self.image_model.load_from_path(file_path):
                self.navigator_model.set_current_path(file_path)
                self.display_image()
                self._update_status_info()
                formatted_path = self.navigator_model.format_path_for_display(file_path)
                self.status_bar.showMessage(f"Opened: {formatted_path}")

    def open_image(self):
        """Open an image file via dialog."""
        home_dir = os.path.expanduser("~")
        dialog = QFileDialog(self, "Open Image", home_dir, "Images (*.jpg *.jpeg *.png *.webp *.gif)")
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        if dialog.exec() == QFileDialog.Accepted:
            path = dialog.selectedFiles()[0]
            if path and self.image_model.load_from_path(path):
                self.navigator_model.set_current_path(path)
                self.display_image()
                self._update_status_info()
                formatted_path = self.navigator_model.format_path_for_display(path)
                self.view.set_tool_mode(ToolMode.NONE, f"Opened: {formatted_path}")

    def reload_image(self):
        """Reload the current image from disk."""
        if self.image_model.path and self.image_model.reload_from_path():
            self.display_image()
            self.status_bar.showMessage(f"Reloaded: {self.image_model.path}")
        else:
            self.status_bar.showMessage("No file to reload" if not self.image_model.path else "Failed to reload image")
        self.view.setFocus()

    def new_window(self):
        """Launch a new instance of the application."""
        subprocess.Popen([sys.executable, sys.argv[0]])
        self.view.setFocus()

    def _navigate_image(self, direction):
        """Navigate to next/previous image."""
        new_path = self.navigator_model.navigate(direction)
        if new_path and self.image_model.load_from_path(new_path):
            self.display_image()
            self._update_status_info()
            formatted = self.navigator_model.format_path_for_display(new_path)
            self.status_bar.showMessage(f"Loaded: {formatted}")
        else:
            self.status_bar.showMessage(f"No {direction} image")

    def next_image(self):
        self.view.set_tool_mode(ToolMode.NONE)
        self._navigate_image("next")

    def previous_image(self):
        self.view.set_tool_mode(ToolMode.NONE)
        self._navigate_image("previous")

    def _update_status_info(self):
        """Update status bar with file index, filename, dimensions, and megapixels."""
        if self.image_model.current_pixmap:
            size_px = self.image_model.current_pixmap.size()
            w, h = size_px.width(), size_px.height()
            mp = w * h / 1_000_000
            size_str = f"{w}×{h} ({mp:.1f} MP)"
        else:
            size_str = "??×?? (?.? MP)"

        if self.navigator_model.total_count > 0:
            idx = self.navigator_model.current_file_index + 1
            total = self.navigator_model.total_count
            name = self.navigator_model.current_filename
            self.size_label.setText(f"{idx}/{total} — {name} {size_str}")
        else:
            if self.image_model.path:
                name = os.path.basename(self.image_model.path)
                self.size_label.setText(f"{name} {size_str}")
            else:
                self.size_label.setText(f"Pasted image {size_str}")

    def paste_image(self):
        """Load image from clipboard."""
        if self.image_model.load_from_clipboard():
            self.display_image()
            self.status_bar.showMessage("Pasted image from clipboard")
        self.view.setFocus()

    def display_image(self):
        """Update scene with current pixmap."""
        self.scene.clear()
        self.view.set_pixmap(self.image_model.current_pixmap)

    def rotate_cw(self):
        self.view.set_tool_mode(ToolMode.NONE)
        self.image_model.rotate_90_clockwise()
        self.display_image()

    def rotate_ccw(self):
        self.view.set_tool_mode(ToolMode.NONE)
        self.image_model.rotate_90_counterclockwise()
        self.display_image()

    def flip_horizontal(self):
        self.view.set_tool_mode(ToolMode.NONE)
        self.image_model.flip_horizontal()
        self.display_image()

    def flip_vertical(self):
        self.view.set_tool_mode(ToolMode.NONE)
        self.image_model.flip_vertical()
        self.display_image()

    def toggle_wb_mode(self):
        self.view.set_tool_mode(ToolMode.WHITE_BALANCE)

    def toggle_loupe_mode(self):
        self.view.set_tool_mode(ToolMode.LOUPE)

    def apply_white_balance(self, x: int, y: int):
        self.image_model.apply_white_balance_from_point(x, y)
        self.display_image()

    def crop_image(self):
        if not self.image_model.current_pixmap:
            self.status_bar.showMessage("No image to crop")
            return
        self.view.set_tool_mode(ToolMode.CROP)

    def finalize_crop(self):
        if not self.image_model.current_pixmap or not self.view.crop_area.is_active:
            return
        rect = self.view.crop_area.rect
        cropped = self.image_model.current_pixmap.copy(rect)
        self.image_model.apply_to_current(cropped)
        self.clipboard_model.copy_image(cropped)
        self.status_bar.showMessage("Cropped image copied to clipboard")
        self.view.crop_area.reset()
        self.display_image()

    def copy_image(self):
        """Copy full image or selection to clipboard."""
        if not self.image_model.current_pixmap:
            return
        if self.view.crop_area.is_active and not self.view.crop_area.rect.isNull():
            cropped = self.image_model.current_pixmap.copy(self.view.crop_area.rect)
            self.clipboard_model.copy_image(cropped)
            self.status_bar.showMessage("Selected area copied to clipboard")
        else:
            self.clipboard_model.copy_image(self.image_model.current_pixmap)
            self.status_bar.showMessage("Full image copied to clipboard")
        self.view.setFocus()

    def show_exif(self):
        if not self.image_model.path:
            self.status_bar.showMessage("No image loaded from file")
            return
        success = ExifHelper.show_exif_data(self, self.image_model.path)
        if not success:
            self.status_bar.showMessage("No EXIF data or failed to read")
        self.view.setFocus()

    def save_image(self):
        if not self.image_model.current_pixmap:
            return
        initial_path = self.image_model.path or ""
        if initial_path:
            name, ext = os.path.splitext(initial_path)
            if ext.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
                initial_path = name

        dialog = QFileDialog(self, "Save Image", initial_path,
                             "JPEG (*.jpg *.jpeg);;PNG (*.png);;WEBP (*.webp)")
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        if dialog.exec() != QFileDialog.Accepted:
            return

        path = dialog.selectedFiles()[0]
        selected_filter = dialog.selectedNameFilter()
        path = SaveHelper.ensure_extension(path, selected_filter)

        if path.lower().endswith((".jpg", ".jpeg")):
            quality = SaveHelper.get_quality_for_format(self, "JPEG")
            if quality is None:
                return
            success = self.image_model.save(path, "JPEG", quality)
        elif path.lower().endswith(".webp"):
            quality = SaveHelper.get_quality_for_format(self, "WEBP")
            if quality is None:
                return
            success = self.image_model.save(path, "WEBP", quality)
        elif path.lower().endswith(".png"):
            success = self.image_model.save(path, "PNG")
        else:
            if not any(path.lower().endswith(e) for e in ['.jpg', '.jpeg', '.png', '.webp']):
                path += '.png'
            success = self.image_model.save(path, "PNG")

        if success:
            saved_dir = os.path.dirname(path)
            if (self.navigator_model.current_directory and
                os.path.samefile(saved_dir, self.navigator_model.current_directory)):
                self.navigator_model.image_paths = self.navigator_model._get_image_paths_in_directory(saved_dir)
                try:
                    self.navigator_model.current_file_index = self.navigator_model.image_paths.index(path)
                except ValueError:
                    pass
            if path == self.image_model.path:
                self.image_model.path = path
            self.status_bar.showMessage(f"Saved: {path}")
        else:
            self.status_bar.showMessage(f"Failed to save: {path}")

    def resize_image(self):
        self.view.set_tool_mode(ToolMode.NONE)
        if not self.image_model.current_pixmap:
            return
        w, h = ResizeHelper.resize_with_aspect_ratio(
            self,
            self.image_model.current_pixmap,
            self.image_model.current_pixmap.width(),
            self.image_model.current_pixmap.height()
        )
        if w is not None and h is not None:
            self.image_model.resize(w, h)
            self.display_image()
            self.status_bar.showMessage(f"Resized to {w}×{h}")

    def delete_current_file(self):
        self.view.set_tool_mode(ToolMode.NONE)
        if not self.image_model.path:
            self.status_bar.showMessage("No file to delete")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Move '{os.path.basename(self.image_model.path)}' to trash?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
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
                    self.display_image()
            else:
                self.status_bar.showMessage("Failed to move file to trash")

    def show_help(self):
        self.view.set_tool_mode(ToolMode.NONE)
        from about_dialog import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec()
