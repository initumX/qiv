import os, sys, subprocess

from PySide6.QtWidgets import (
    QMainWindow, QGraphicsScene, QStatusBar, QFileDialog,
    QLabel, QMessageBox, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QIcon

from models import ImageModel, NavigatorModel, ViewState, ClipboardModel
from image_helpers import ExifHelper, ResizeHelper, SaveHelper, move_to_trash
from image_view import ImageView, ToolMode
from thumbnail_dialog import ThumbnailDialog
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
        self.open_action = self._make_action("folder-open", "Open file",
                                             QKeySequence.Open, self.open_image, False)

        self.thumbnails_action = self._make_action("thumbnails", "Thumbnails/Open folder",
                                                   "Ctrl+T", self.show_thumbnails, False)

        self.save_action = self._make_action("save", "Save",
                                             QKeySequence.Save, self.save_image, True)

        self.reload_action = self._make_action("reload", "Reload",
                                               "F5", self.reload_image, True)

        self.new_window_action = self._make_action("new-file", "New Window",
                                                   "Ctrl+N", self.new_window, False)

        self.delete_action = self._make_action("trash", "Move to Trash",
                                               "Delete", self.delete_current_file, True)

        # Edit actions
        self.rotate_cw_action = self._make_action("cw", "Rotate CW",
                                                  "R", self.rotate_cw, True)

        self.rotate_ccw_action = self._make_action("ccw", "Rotate CCW",
                                                   "L", self.rotate_ccw, True)

        self.flip_h_action = self._make_action("flip-h", "Flip Horizontal",
                                               "H", self.flip_horizontal, True)

        self.flip_v_action = self._make_action("flip-v", "Flip Vertical",
                                               "V", self.flip_vertical, True)

        self.crop_action = self._make_action("crop", "Crop",
                                            QKeySequence.Cut, self.crop_image, True)

        self.copy_action = self._make_action("copy", "Copy",
                                             QKeySequence.Copy, self.copy_image, True)

        self.paste_action = self._make_action("paste", "Paste",
                                               QKeySequence.Paste, self.paste_image, False)

        self.resize_action = self._make_action("resize", "Resize",
                                               "Ctrl+R", self.resize_image, True)

        # Zoom actions
        self.zoom_in_action = self._make_action("zoom-in", "Zoom In",
                                                "+", self.view.zoom_in, True)

        self.zoom_out_action = self._make_action("zoom-out", "Zoom Out",
                                                 "-", self.view.zoom_out, True)

        self.original_size_action = self._make_action("zoom-original", "Original Size",
                                                      "=", self.view.reset_zoom, True)

        self.fit_to_window_action = self._make_action("zoom-fit", "Fit To Window",
                                                      "W", self.view.fit_to_view, True)

        self.loupe_action = self._make_action("loupe", "Loupe (1:1 Preview)",
                                              "Ctrl+L", self.toggle_loupe_mode, True, reset_tool=False)

        # Navigation actions
        self.next_action = self._make_action("arrow-right", "Next Image",
                                             "N", self.next_image, False)

        self.previous_action = self._make_action("arrow-left", "Previous Image",
                                                 "Shift+N", self.previous_image, False)

        # Info / tool actions
        self.exif_action = self._make_action("info", "Show EXIF",
                                             "I", self.show_exif, True, reset_tool=False)

        self.wb_action = self._make_action("wb", "White Balance (Click Neutral)",
                                           "Shift+I", self.toggle_wb_mode, True, reset_tool=False)

        # Help
        self.help_action = self._make_action("help", "About",
                                             "F1", self.show_help, False)

        # Exit
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Q")
        self.exit_action.triggered.connect(self.close)

    def _make_action(self, icon_name: str, text: str,
                     shortcut, handler, needs_image=True, reset_tool=True):
        action = QAction(QIcon(f":/icons/{icon_name}.svg"), text, self)
        if shortcut:
            action.setShortcut(shortcut)

        def wrapped_handler():
            if needs_image:
                if not self.image_model.current_pixmap or self.image_model.current_pixmap.isNull():
                    self.status_bar.showMessage("No image loaded")
                    return
                if reset_tool:
                    self.view.set_tool_mode(ToolMode.NONE)
            handler()

        action.triggered.connect(wrapped_handler)
        return action

    def _create_menus(self):
        """Build the menu bar."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self.new_window_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.thumbnails_action)
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
        toolbar.addAction(self.thumbnails_action)
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

    def load_file_from_args(self):
        """Load image from command-line argument if provided."""
        if len(sys.argv) > 1:
            file_path = os.path.normpath(sys.argv[1])
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
            path = os.path.normpath(path)
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

    def show_thumbnails(self):
        initial_dir = self.navigator_model.current_directory
        if not initial_dir:
            initial_dir = QFileDialog.getExistingDirectory(
                self, "Select Folder with Images", os.path.expanduser("~")
            )
            if not initial_dir:
                return
        dialog = ThumbnailDialog(initial_dir, self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_path:
            self.open_specific_image(dialog.selected_path)

    def open_specific_image(self, path: str):
        path = os.path.normpath(path)
        if self.image_model.load_from_path(path):
            self.navigator_model.set_current_path(path)
            self.display_image()
            self._update_status_info()
            formatted = self.navigator_model.format_path_for_display(path)
            self.status_bar.showMessage(f"Opened: {formatted}")

    def _navigate_image(self, direction):
        """Navigate to next/previous image."""
        if not self.image_model.path:
            self.status_bar.showMessage("Navigation requires an image loaded from file")
            return
        self.view.set_tool_mode(ToolMode.NONE)
        new_path = self.navigator_model.navigate(direction)
        if new_path and self.image_model.load_from_path(new_path):
            self.display_image()
            self._update_status_info()
            formatted = self.navigator_model.format_path_for_display(new_path)
            self.status_bar.showMessage(f"Loaded: {formatted}")
        else:
            self.status_bar.showMessage(f"No {direction} image")

    def next_image(self):
        self._navigate_image("next")

    def previous_image(self):
        self._navigate_image("previous")

    def _update_status_info(self):
        text = self.navigator_model.format_status_text(self.image_model.current_pixmap)
        self.size_label.setText(text)

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
        self.view.setFocus()

    def rotate_cw(self):
        self.image_model.rotate_90_clockwise()
        self.display_image()

    def rotate_ccw(self):
        self.image_model.rotate_90_counterclockwise()
        self.display_image()

    def flip_horizontal(self):
        self.image_model.flip_horizontal()
        self.display_image()

    def flip_vertical(self):
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
                self.navigator_model.image_paths = self.navigator_model.get_image_paths_flat(saved_dir)
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
        path = self.image_model.path
        if not path:
            self.status_bar.showMessage("No file to delete")
            return

        filename = os.path.basename(path)
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Move '{filename}' to trash?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if not move_to_trash(path):
            self.status_bar.showMessage("Failed to move file to trash")
            return

        self.status_bar.showMessage(f"Moved to trash: {filename}")

        # Try to load next image in sequence
        next_path = None
        if self.navigator_model.has_next():
            next_path = self.navigator_model.get_next_path()
        elif self.navigator_model.has_previous():
            next_path = self.navigator_model.get_previous_path()

        if next_path and self.image_model.load_from_path(next_path):
            self.navigator_model.set_current_path(next_path)
            self.display_image()
            self._update_status_info()
        else:
            # No more images — clear
            self.image_model.path = None
            self.image_model.current_pixmap = None
            self.display_image()

    def show_help(self):
        self.view.set_tool_mode(ToolMode.NONE)
        from about_dialog import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec()
