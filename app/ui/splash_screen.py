"""Splash screen for Clean Mac app startup."""

from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QFont
from app import __version__

class CleanMacSplashScreen(QSplashScreen):
    """Custom splash screen with progress indication."""
    
    def __init__(self):
        # Create a simple splash screen pixmap
        pixmap = self._create_splash_pixmap()
        super().__init__(pixmap)
        
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Progress tracking
        self._progress = 0
        self._max_progress = 100
        self._status_text = "Starting Clean Mac..."
        
        # Timer for progress updates
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_progress)
        self._timer.start(50)  # Update every 50ms
        
    def _create_splash_pixmap(self) -> QPixmap:
        """Create the splash screen pixmap."""
        width, height = 400, 300
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background with rounded corners
        painter.setBrush(Qt.GlobalColor.white)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(10, 10, width - 20, height - 20, 15, 15)
        
        # Border
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(Qt.PenStyle.SolidLine)
        painter.setPen(Qt.GlobalColor.lightGray)
        painter.drawRoundedRect(10, 10, width - 20, height - 20, 15, 15)
        
        # App title
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.darkBlue)
        painter.drawText(0, 0, width, 80, Qt.AlignmentFlag.AlignCenter, "Clean Mac")
        
        # Version
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.gray)
        painter.drawText(0, 60, width, 30, Qt.AlignmentFlag.AlignCenter, f"Version {__version__}")
        
        # Loading area
        painter.setPen(Qt.GlobalColor.darkGray)
        painter.drawText(20, 120, width - 40, 30, Qt.AlignmentFlag.AlignLeft, "Loading...")
        
        # Progress bar background
        painter.setBrush(Qt.GlobalColor.lightGray)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(20, 150, width - 40, 20, 10, 10)
        
        painter.end()
        return pixmap
    
    def _update_progress(self):
        """Update progress animation."""
        self._progress += 1
        if self._progress > self._max_progress:
            self._progress = 0
        
        # Redraw the splash screen with updated progress
        self._redraw_splash()
    
    def _redraw_splash(self):
        """Redraw the splash screen with current progress."""
        width, height = 400, 300
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background with rounded corners
        painter.setBrush(Qt.GlobalColor.white)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(10, 10, width - 20, height - 20, 15, 15)
        
        # Border
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(Qt.PenStyle.SolidLine)
        painter.setPen(Qt.GlobalColor.lightGray)
        painter.drawRoundedRect(10, 10, width - 20, height - 20, 15, 15)
        
        # App title
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.darkBlue)
        painter.drawText(0, 0, width, 80, Qt.AlignmentFlag.AlignCenter, "Clean Mac")
        
        # Version
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.gray)
        painter.drawText(0, 60, width, 30, Qt.AlignmentFlag.AlignCenter, f"Version {__version__}")
        
        # Status text
        painter.setPen(Qt.GlobalColor.darkGray)
        painter.drawText(20, 120, width - 40, 30, Qt.AlignmentFlag.AlignLeft, self._status_text)
        
        # Progress bar background
        painter.setBrush(Qt.GlobalColor.lightGray)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(20, 150, width - 40, 20, 10, 10)
        
        # Progress bar fill
        progress_width = int((width - 40) * (self._progress / self._max_progress))
        painter.setBrush(Qt.GlobalColor.blue)
        painter.drawRoundedRect(20, 150, progress_width, 20, 10, 10)
        
        # Progress percentage
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(20, 150, width - 40, 20, Qt.AlignmentFlag.AlignCenter, f"{self._progress}%")
        
        painter.end()
        self.setPixmap(pixmap)
    
    def set_status(self, text: str, progress: int = None):
        """Update status text and optionally progress."""
        self._status_text = text
        if progress is not None:
            self._progress = min(progress, self._max_progress)
        self._redraw_splash()
    
    def finish_loading(self):
        """Finish the loading animation."""
        self._timer.stop()
        self.set_status("Ready!", 100)
        QApplication.processEvents()
        QTimer.singleShot(500, self.close)  # Close after 500ms


class StartupManager:
    """Manages app startup with dependency checking and loading states."""
    
    def __init__(self, splash_screen: CleanMacSplashScreen):
        self.splash = splash_screen
        self._startup_steps = [
            ("Initializing...", 10),
            ("Checking dependencies...", 25),
            ("Loading configuration...", 40),
            ("Setting up UI...", 60),
            ("Preparing scan engine...", 80),
            ("Almost ready...", 95),
        ]
        self._current_step = 0
    
    def start_startup_sequence(self):
        """Start the startup sequence with progress updates."""
        self._run_next_step()
    
    def _run_next_step(self):
        """Run the next startup step."""
        if self._current_step >= len(self._startup_steps):
            self.splash.finish_loading()
            return
        
        text, progress = self._startup_steps[self._current_step]
        self.splash.set_status(text, progress)
        
        # Simulate work time
        QTimer.singleShot(200, self._complete_step)
    
    def _complete_step(self):
        """Complete current step and move to next."""
        self._current_step += 1
        self._run_next_step()
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are available."""
        try:
            import PySide6
            import send2trash
            import platformdirs
            return True
        except ImportError as e:
            self.splash.set_status(f"Missing dependency: {e}", 25)
            return False
