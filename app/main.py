import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer
from app.ui.main_window import MainWindow
from app.ui.splash_screen import CleanMacSplashScreen, StartupManager
from app.ui.onboarding_dialog import show_onboarding_if_needed
from app.utils.dependency_manager import DependencyManager


def main() -> int:
    app = QApplication(sys.argv)
    
    # Set the app icon
    try:
        # Try to load our custom icon
        icon_path = "assets/icon.png"
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        else:
            # Fallback to a simple colored icon
            icon_pm = QPixmap(64, 64)
            icon_pm.fill(Qt.GlobalColor.blue)
            app.setWindowIcon(QIcon(icon_pm))
    except Exception:
        # Final fallback
        pass
    
    # Show splash screen immediately
    splash = CleanMacSplashScreen()
    splash.show()
    app.processEvents()
    
    # Initialize startup manager
    startup_manager = StartupManager(splash)
    
    # Check dependencies first
    splash.set_status("Checking dependencies...", 25)
    app.processEvents()
    
    dep_manager = DependencyManager()
    all_deps_available, missing_deps = dep_manager.check_all_dependencies()
    
    if not all_deps_available:
        splash.set_status("Installing missing dependencies...", 30)
        app.processEvents()
        
        # Try to install missing dependencies
        if not dep_manager.auto_install_missing():
            # If installation failed, show error and exit
            splash.close()
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Missing Dependencies")
            msg.setText("Required dependencies are missing and could not be installed automatically.")
            msg.setInformativeText(f"Missing: {', '.join(missing_deps)}\n\nPlease install manually:\npip install {' '.join(missing_deps)}")
            msg.exec()
            return 1
    
    # Start the startup sequence
    startup_manager.start_startup_sequence()
    
    # Create and show main window after a delay
    def show_main_window():
        window = MainWindow()
        window.show()
        splash.finish_loading()
        
        # Show onboarding dialog if needed (after main window is shown)
        QTimer.singleShot(500, lambda: show_onboarding_if_needed(window))
    
    # Show main window after startup sequence completes
    QTimer.singleShot(2000, show_main_window)  # 2 seconds for startup sequence
    
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
