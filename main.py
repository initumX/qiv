import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    window.load_file_from_args()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
