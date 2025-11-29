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
        <p>Handy image viewer built with PySide6.</p>

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
        <style>
            table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            th, td { text-align: left; padding: 6px 8px; border: 1px solid #ccc; }
            th { background-color: #f5f5f5; }
        </style>

        <h5>Navigation & View</h5>
        <table>
            <tr><td>Next / Previous image</td><td>← → ↑ ↓ or Mouse wheel</td></tr>
            <tr><td>Zoom In / Out</td><td><code>Ctrl + Wheel</code> or <code>+</code> / <code>-</code></td></tr>
            <tr><td>Original size</td><td><code>=</code> or Double-click</td></tr>
            <tr><td>Fit to window</td><td><code>W</code> or Right-click</td></tr>
            <tr><td>Pan (move image)</td><td><code>Ctrl + Arrows</code> or Middle drag</td></tr>
        </table>

        <h5>Editing</h5>
        <table>
            <tr><td>Enter Crop mode</td><td><code>Ctrl+X</code></td></tr>
            <tr><td>Apply Crop</td><td><code>Enter</code></td></tr>
            <tr><td>Copy selection / full image</td><td><code>Ctrl+C</code></td></tr>
            <tr><td>Paste image</td><td><code>Ctrl+V</code></td></tr>
            <tr><td>White Balance</td><td><code>B</code></td></tr>
            <tr><td>Resize image</td><td><code>Ctrl+R</code></td></tr>
        </table>

        <h5>Transform</h5>
        <table>
            <tr><td>Rotate 9 0° CW / CCW</td><td><code>R</code> / <code>Shift+R</code></td></tr>
            <tr><td>Flip Horizontal / Vertical</td><td><code>F</code> / <code>Shift+F</code></td></tr>
        </table>

        <h5>File & Info</h5>
        <table>
            <tr><td>Open file</td><td><code>Ctrl+O</code></td></tr>
            <tr><td>Open folder / thumbnails</td><td><code>Ctrl+T</code></td></tr>
            <tr><td>Save image</td><td><code>Ctrl+S</code></td></tr>
            <tr><td>Reload image</td><td><code>F5</code></td></tr>
            <tr><td>Move to trash</td><td><code>Delete</code></td></tr>
            <tr><td>Show EXIF</td><td><code>I</code></td></tr>
            <tr><td>About / Help</td><td><code>F1</code></td></tr>
        </table>

        <h5>Cancel</h5>
        <table>
            <tr><td>Exit any tool (crop, WB...)</td><td><code>Esc</code> or Right-click</td></tr>
            <tr><td>Exit from app</td><td><code>Q</code></td></tr>
        </table>
        
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
