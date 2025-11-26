import os
from PySide6.QtWidgets import (
    QDialog, QScrollArea, QWidget, QGridLayout, QLabel,
    QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QFileDialog
)
from PySide6.QtGui import QPixmap, Qt
from PySide6.QtCore import Qt as QtCoreQt

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

class ThumbnailDialog(QDialog):
    def __init__(self, directory: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Thumbnails — {os.path.basename(directory) or directory}")
        self.resize(800, 600)
        self.selected_path = None
        self.current_directory = directory
        self._build_ui()

    def _build_ui(self):
        # Clear layout if called repeatedly
        if self.layout():
            QWidget().setLayout(self.layout())

        # Get image paths
        self.image_paths = []
        try:
            for filename in sorted(os.listdir(self.current_directory), key=str.lower):
                ext = os.path.splitext(filename)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    self.image_paths.append(os.path.join(self.current_directory, filename))
        except OSError:
            pass

        main_layout = QVBoxLayout(self)

        if not self.image_paths:
            label = QLabel("No images found in this directory.")
            label.setAlignment(QtCoreQt.AlignCenter)
            main_layout.addWidget(label)
        else:
            # Build scrollable grid
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QWidget()
            grid = QGridLayout(content)
            grid.setSpacing(10)
            grid.setContentsMargins(10, 10, 10, 10)

            thumbnails_per_row = max(1, self.width() // 280)

            for i, path in enumerate(self.image_paths):
                row = i // thumbnails_per_row
                col = i % thumbnails_per_row

                pixmap = QPixmap(path)
                if pixmap.isNull():
                    continue
                thumb = pixmap.scaled(
                    256, 256,
                    QtCoreQt.KeepAspectRatio,
                    QtCoreQt.SmoothTransformation
                )

                label = QLabel()
                label.setPixmap(thumb)
                label.setAlignment(QtCoreQt.AlignCenter)
                label.setFixedSize(256, 256)
                label.setFrameShape(QFrame.Box)
                label.setProperty("image_path", path)
                label.mouseDoubleClickEvent = lambda e, p=path: self._select_and_accept(p)

                name_label = QLabel(os.path.basename(path))
                name_label.setAlignment(QtCoreQt.AlignCenter)
                name_label.setWordWrap(True)
                name_label.setMaximumWidth(256)

                item_widget = QWidget()
                item_layout = QVBoxLayout(item_widget)
                item_layout.addWidget(label)
                item_layout.addWidget(name_label)
                item_layout.setContentsMargins(0, 0, 0, 0)

                grid.addWidget(item_widget, row, col)

            content.setLayout(grid)
            scroll.setWidget(content)
            main_layout.addWidget(scroll)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        open_folder_btn = QPushButton("Open Folder…")
        open_folder_btn.clicked.connect(self._open_another_folder)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(open_folder_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)

        main_layout.addLayout(btn_layout)

    def _open_another_folder(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with Images",
            self.current_directory
        )
        if dir_path:
            self.current_directory = dir_path
            self.setWindowTitle(f"Thumbnails — {os.path.basename(dir_path)}")
            self._build_ui()

    def _select_and_accept(self, path: str):
        self.selected_path = path
        self.accept()