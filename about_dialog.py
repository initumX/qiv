from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QLabel, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices, QPalette
from PySide6.QtCore import QUrl

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Qt Image Viewer (qiv)")
        self.setModal(True)  # Block parent window
        self.resize(500, 400)  # Set initial size

        layout = QVBoxLayout(self)

        # Caption
        title_label = QLabel("Qt Image Viewer (qiv)")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")

        # Text with HTML
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)
        text_browser.setHtml(self.get_about_text())

        # "Close" Button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)

        layout.addWidget(title_label)
        layout.addWidget(text_browser)
        layout.addWidget(button_box)

    def get_about_text(self):
        return """
        <h3>About Qt Image Viewer</h3>
        <p>A lightweight and fast image viewer and editor built with PySide6.</p>

        <h4>Features:</h4>
        <ul>
            <li>View photo/screenshots: JPG/JPEG, WebP, PNG</li>
            <li>Basic editing: Rotate, flip, crop, copy/paste, resize</li>
            <li>White balance feature</li>
            <li>Saving with quality control</li>
            <li>Zoom in/out, fit to window, original size</li>
            <li>Handy panning with arrows or middle mouse button</li>
            <li>File navigation (next/previous in folder)</li>
            <li>EXIF data display</li>
            <li>Thumbnails/Open Folder: Dialog window with thumbnails (uses caching and threads)</li>
            <li>...</li>
        </ul>
        
        <h4>Hotkeys:</h4>
        <ul> 
            <li>Navigation: arrows or mouse wheel scrolling </li>
            <li>Zooming in/out by mouse: Ctrl+mouse wheel scrolling</li>
            <li>Zooming in/out by keyboard: + and - </li>
            <li>Original size: double click or = </li>
            <li>Fit to window: right click or w </li>
            <li>Panning by mouse: push down mouse wheel and move mouse </li>
            <li>Panning by keyboard: Ctrl+arrows </li>
            <li>Cancel selected tool (crop/white balance/loupe): right click </li>
            <li>Rotate: R and Shift+R </li>
            <li>Flip: F and Shift+F  </li>
            <li>Loupe: L </li>
            <li>White Balance: B </li>
            <li>Resize: Ctrl+R </li>
        </ul>
        
        <h4>Version:</h4>
        <p>0.0.5</p>

        <h4>Author:</h4>
        <p>initum.x</p>

        <h4>Contact (feel free to write):</h4>
        <p>Email: <a href="mailto:initum.x@gmail.com">initum.x@gmail.com</a></p>
        
        <h4>Source:</h4>
        <p>GitHub: <a href="https://github.com/initumX/qiv">https://github.com/initumX/qiv</a></p>

        <h4>License:</h4>
        <p>MIT License</p>

        <h4>Credits:</h4>
        <p>Thanks to Flaticons for free icons <a href="https://www.flaticon.com/">www.flaticon.com</a></p>
        <p>Thanks to Svgrepo for free icons <a href="https://www.svgrepo.com/">https://www.svgrepo.com/</a></p>
        <p>Thanks to the PySide6 team and the open-source community.</p>
        <p>Thanks to Free Internet.</p>
        """
