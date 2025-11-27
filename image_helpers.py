from PySide6.QtWidgets import QInputDialog, QMessageBox, QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton
from PySide6.QtGui import QImage, QPixmap
from PIL import Image as PILImage
import exifread


def move_to_trash(path: str) -> bool:
    """Move file to trash/recycle bin."""
    try:
        import send2trash
        send2trash.send2trash(path)
        return True
    except ImportError:
        print("send2trash library not installed. Install it with: pip install send2trash")
        return False
    except Exception as e:
        print(f"Failed to move {path} to trash: {e}")
        return False

class WhiteBalanceHelper:
    @staticmethod
    def apply_white_balance(pixmap: QPixmap, x: int, y: int, max_half_size: int = 11, min_divisor: int = 200) -> QPixmap | None:
        """
        Applies white balance to a QPixmap based on a neutral point (x, y).
        Returns a new QPixmap with corrected colors, or None on error.
        """
        if pixmap.isNull():
            return None
        qimage = pixmap.toImage()
        w, h = qimage.width(), qimage.height()
        if not (0 <= x < w and 0 <= y < h):
            return None

        half = min(max_half_size, max(1, min(w, h) // min_divisor))
        total_r = total_g = total_b = count = 0
        for dy in range(-half, half + 1):
            for dx in range(-half, half + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    pixel = qimage.pixel(nx, ny)
                    r = (pixel >> 16) & 0xFF
                    g = (pixel >> 8) & 0xFF
                    b = pixel & 0xFF
                    total_r += r
                    total_g += g
                    total_b += b
                    count += 1

        if count == 0 or total_g == 0:
            return pixmap  # no change

        gain_r = min(4.0, max(0.25, total_g / total_r)) if total_r else 1.0
        gain_b = min(4.0, max(0.25, total_g / total_b)) if total_b else 1.0

        img = PILImage.fromqimage(qimage)
        if img.mode in ("RGB", "RGBA"):
            bands = img.split()
            r_new = bands[0].point(lambda v: min(255, int(v * gain_r)))
            b_new = bands[2].point(lambda v: min(255, int(v * gain_b)))
            corrected = PILImage.merge(img.mode, (r_new, bands[1], b_new) + (bands[3:] if len(bands) > 3 else ()))
        else:
            img = img.convert("RGB")
            r, g, b = img.split()
            r = r.point(lambda v: min(255, int(v * gain_r)))
            b = b.point(lambda v: min(255, int(v * gain_b)))
            corrected = PILImage.merge("RGB", (r, g, b))

        return QPixmap.fromImage(corrected.toqimage())

class SaveHelper:
    @staticmethod
    def get_quality_for_format(parent, format_name):
        """Get quality setting for lossy formats."""
        if format_name.upper() == "JPEG":
            quality, ok = QInputDialog.getInt(
                parent,
                "JPEG Quality",
                "Set JPEG Quality (75-100):",
                95,
                75,
                100,
                1
            )
            if not ok:
                return None
            return quality
        elif format_name.upper() == "WEBP":
            quality, ok = QInputDialog.getInt(
                parent,
                "WebP Quality",
                "Set WebP Quality (75-100):",
                90,
                75,
                100,
                1
            )
            if not ok:
                return None
            return quality
        return None  # For lossless formats like PNG, BMP

    @staticmethod
    def ensure_extension(path, selected_filter):
        """Add appropriate extension if not present."""
        if '.' not in path.split('/')[-1] and '.' not in path.split('\\')[-1]:
            # Determine extension based on selected filter
            if 'JPEG' in selected_filter:
                path += '.jpg'
            elif 'PNG' in selected_filter:
                path += '.png'
            elif 'WEBP' in selected_filter:
                path += '.webp'
            elif 'BMP' in selected_filter:
                path += '.bmp'
            else:
                path += '.png'  # default to PNG
        return path


class ResizeHelper:
    @staticmethod
    def resize_with_aspect_ratio(parent, pixmap, original_width, original_height):
        """Resize image with aspect ratio preservation, allowing user to specify only one dimension."""
        aspect_ratio = original_width / original_height

        # Ask user which dimension to specify
        choice, ok = QInputDialog.getItem(
            parent,
            "Resize Image",
            "Specify dimension:",
            ["Width", "Height"],
            0,
            False
        )

        if not ok:
            return None, None

        if choice == "Width":
            # User specifies width, calculate height
            target_width, ok = QInputDialog.getInt(
                parent,
                "Resize Image",
                f"Enter width (original: {original_width}):",
                original_width,
                1,
                10000,
                1
            )
            if not ok:
                return None, None
            target_height = int(target_width / aspect_ratio)

        else:  # Height
            # User specifies height, calculate width
            target_height, ok = QInputDialog.getInt(
                parent,
                "Resize Image",
                f"Enter height (original: {original_height}):",
                original_height,
                1,
                10000,
                1
            )
            if not ok:
                return None, None
            target_width = int(target_height * aspect_ratio)

        # Confirm the calculated dimensions
        reply = QMessageBox.question(
            parent,
            "Confirm Resize",
            f"Resize to {target_width}×{target_height}?\n"
            f"(Original: {original_width}×{original_height})",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return None, None

        return target_width, target_height

    @staticmethod
    def resize_pixmap(pixmap, width: int, height: int):
        """Resize pixmap using PIL for better quality."""
        qimage = pixmap.toImage()
        img = PILImage.fromqimage(qimage)
        resized = img.resize((width, height), PILImage.LANCZOS)

        # Convert PIL Image to QImage
        # Ensure the image is in RGB mode
        if resized.mode != 'RGB':
            resized = resized.convert('RGB')
        # Convert PIL Image to bytes and create QImage
        data = resized.tobytes("raw", "RGB")
        qimage_resized = QImage(data, width, height, 3 * width, QImage.Format_RGB888)
        return qimage_resized

class ExifHelper:
    @staticmethod
    def show_exif_data(parent, file_path):
        """Show EXIF data in a separate dialog."""
        if not file_path:
            return False

        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f)

            if not tags:
                return False

            # Create dialog
            dialog = QDialog(parent)
            dialog.setWindowTitle("EXIF Data")
            dialog.resize(800, 600)

            layout = QVBoxLayout(dialog)

            tree = QTreeWidget()
            tree.setHeaderLabels(["Tag", "Value"])
            tree.setColumnWidth(0, 300)

            for tag, value in tags.items():
                item = QTreeWidgetItem([str(tag), str(value)])
                tree.addTopLevelItem(item)

            layout.addWidget(tree)

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)

            dialog.exec()
            return True

        except Exception as e:
            print(f"Failed to read EXIF: {e}")
            return False
