"""
Displays a scrollable grid of image thumbnails from a selected directory.
"""
import sys
import subprocess
import os
import time
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QScrollArea, QWidget, QGridLayout, QLabel,
    QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QFileDialog, QMessageBox, QMenu
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QObject, Signal, QRunnable, QThreadPool
# Modular utilities
from thumbnail_cache import load_or_create_thumbnail
from models import NavigatorModel
from image_helpers import move_to_trash
from open_in_fm import open_path_in_file_manager


class ThumbnailWorker(QRunnable):
    """Runs file scanning and thumbnail generation in background."""
    class Signals(QObject):
        progress = Signal(str)
        thumbnail_ready = Signal(str, QPixmap)
        finished = Signal()
        error = Signal(str)

    def __init__(self, directory: str, use_subfolders: bool):
        super().__init__()
        self.directory = directory
        self.use_subfolders = use_subfolders
        self.signals = self.Signals()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self.use_subfolders:
                paths = NavigatorModel().get_image_paths_recursive(self.directory, max_depth=2)
            else:
                paths = NavigatorModel().get_image_paths_flat(self.directory)
            if self._is_cancelled:
                return
            total = len(paths)
            self.signals.progress.emit(f"Found {total} images. Loading thumbnails...")
            for i, path in enumerate(paths):
                if self._is_cancelled:
                    break
                self.signals.progress.emit(f"Loading thumbnails... {i + 1}/{total}")
                thumb = load_or_create_thumbnail(path)
                if thumb and not self._is_cancelled:
                    self.signals.thumbnail_ready.emit(path, thumb)
                time.sleep(0.001)  # yield to UI thread
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))


class ThumbnailDialog(QDialog):
    def __init__(self, directory: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Thumbnails — {os.path.basename(directory) or directory}")
        self.resize(850, 650)
        self.selected_path: Optional[str] = None
        self.current_directory = directory
        self.image_paths = []
        self._path_to_widget = {}
        self._worker: Optional[ThumbnailWorker] = None
        self._progress_label = QLabel("Scanning files...")
        self._progress_label.setAlignment(Qt.AlignCenter)
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.hide()
        self._build_ui()
        self._start_scanning(use_subfolders=False)

    def _build_ui(self):
        if self.layout():
            QWidget().setLayout(self.layout())
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self._progress_label)
        main_layout.addWidget(self._scroll_area)
        btn_layout = QHBoxLayout()
        open_folder_btn = QPushButton("Open Folder…")
        open_folder_btn.clicked.connect(self._open_another_folder)
        scan_sub_btn = QPushButton("Scan Subfolders")
        scan_sub_btn.clicked.connect(self._scan_subfolders)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(open_folder_btn)
        btn_layout.addWidget(scan_sub_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

    def _create_thumbnail_widget(self, path: str, thumb: QPixmap) -> QWidget:
        """Create a widget for the given path using a pre-loaded thumbnail."""
        label = QLabel()
        label.setPixmap(thumb)
        label.setAlignment(Qt.AlignCenter)
        label.setFixedSize(256, 256)
        label.setFrameShape(QFrame.Box)
        label.setToolTip(path)

        label.mouseDoubleClickEvent = lambda e, p=path: self._select_and_accept(p)
        label.setContextMenuPolicy(Qt.CustomContextMenu)
        label.customContextMenuRequested.connect(
            lambda pos, p=path, lbl=label: self._show_context_menu(p, lbl, pos)
        )

        name_label = QLabel(os.path.basename(path))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setMaximumWidth(256)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(label)
        layout.addWidget(name_label)
        layout.setContentsMargins(0, 0, 0, 0)
        return widget

    def _add_thumbnail(self, path: str, pixmap: QPixmap):
        if path in self._path_to_widget:
            return
        widget = self._create_thumbnail_widget(path, pixmap)
        if not widget:
            return
        self.image_paths.append(path)
        self._path_to_widget[path] = widget

    def _update_grid(self):
        old_content = self._scroll_area.takeWidget()
        if old_content:
            old_content.deleteLater()

        if not self.image_paths:
            return

        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(10)
        grid.setContentsMargins(10, 10, 10, 10)

        for i, path in enumerate(self.image_paths):
            widget = self._path_to_widget.get(path)
            if widget is None:
                continue
            row = i // self._columns()
            col = i % self._columns()
            grid.addWidget(widget, row, col)

        self._scroll_area.setWidget(content)

    def _columns(self):
        return max(1, self.width() // 280)

    def _show_context_menu(self, path: str, label_widget, point):
        menu = QMenu(self)

        def open_in_current():
            self.selected_path = path
            self.accept()

        def open_in_new_window():
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable, path])
            else:
                subprocess.Popen([sys.executable, sys.argv[0], path])

        def reveal_in_file_manager():
            open_path_in_file_manager(path)

        def delete_file():
            if move_to_trash(path):
                if path in self.image_paths:
                    self.image_paths.remove(path)
                self._path_to_widget.pop(path, None)
                self._update_grid()
                QMessageBox.information(self, "Deleted", f"Moved to trash:\n{os.path.basename(path)}")
            else:
                QMessageBox.warning(self, "Error", "Failed to move file to trash.")

        menu.addAction("Open", open_in_current)
        menu.addAction("Open in New Window", open_in_new_window)
        menu.addAction("Open Path in File Manager", reveal_in_file_manager)
        menu.addAction("Move to Trash", delete_file)
        menu.exec(label_widget.mapToGlobal(point))

    def _start_scanning(self, use_subfolders: bool):
        if self._worker:
            self._worker.cancel()
        self.image_paths.clear()
        self._path_to_widget.clear()
        old_content = self._scroll_area.takeWidget()
        if old_content:
            old_content.deleteLater()
        self._progress_label.show()
        self._scroll_area.hide()
        self._worker = ThumbnailWorker(self.current_directory, use_subfolders)
        self._worker.signals.progress.connect(self._on_progress)
        self._worker.signals.thumbnail_ready.connect(self._add_thumbnail)
        self._worker.signals.finished.connect(self._on_scanning_finished)
        self._worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(self._worker)

    def _on_progress(self, message: str):
        self._progress_label.setText(message)

    def _on_scanning_finished(self):
        self._progress_label.hide()
        if self.image_paths:
            self._scroll_area.show()
            self._update_grid()
        else:
            self._progress_label.setText("No images found.")
            self._progress_label.show()

    def _on_error(self, error_msg: str):
        self._progress_label.setText(f"Error: {error_msg}")
        QMessageBox.warning(self, "Scan Error", f"Failed to load thumbnails:\n{error_msg}")

    def _select_and_accept(self, path: str):
        self.selected_path = path
        self.accept()

    def _open_another_folder(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Folder with Images", self.current_directory
        )
        if dir_path:
            self.current_directory = dir_path
            self.setWindowTitle(f"Thumbnails — {os.path.basename(dir_path)}")
            self._start_scanning(use_subfolders=False)

    def _scan_subfolders(self):
        self._start_scanning(use_subfolders=True)

    def reject(self):
        if self._worker:
            self._worker.cancel()
        super().reject()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_grid()