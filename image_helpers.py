from PySide6.QtWidgets import QInputDialog, QMessageBox, QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton
from PySide6.QtGui import QImage
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