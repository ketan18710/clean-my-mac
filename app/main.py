import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    # Set a transparent app icon so dialogs don't show the default Python icon
    transparent_pm = QPixmap(1, 1)
    transparent_pm.fill(Qt.transparent)
    app.setWindowIcon(QIcon(transparent_pm))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
