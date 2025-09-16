"""First-run onboarding dialog for Clean Mac."""

from PySide6.QtWidgets import (
    QDialog, 
    QVBoxLayout, 
    QHBoxLayout, 
    QLabel, 
    QPushButton, 
    QTextEdit,
    QCheckBox,
    QGroupBox,
    QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app import __version__

class OnboardingDialog(QDialog):
    """First-run onboarding dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Clean Mac")
        self.setModal(True)
        self.resize(500, 600)
        
        # Check if this is first run
        self.is_first_run = self._check_first_run()
        
        self._setup_ui()
        self._setup_connections()
    
    def _check_first_run(self) -> bool:
        """Check if this is the first time running the app."""
        # Simple check - if no presets exist, it's first run
        from app.workers.util import load_presets
        presets = load_presets()
        return not presets  # True if presets is empty
    
    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Welcome header
        header = QLabel("Welcome to Clean Mac!")
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Version info
        version_label = QLabel(f"Version {__version__}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: gray;")
        layout.addWidget(version_label)
        
        # Main content
        if self.is_first_run:
            self._setup_first_run_content(layout)
        else:
            self._setup_help_content(layout)
        
        # Buttons
        self._setup_buttons(layout)
    
    def _setup_first_run_content(self, layout):
        """Set up content for first-time users."""
        # What is Clean Mac section
        what_group = QGroupBox("What is Clean Mac?")
        what_layout = QVBoxLayout(what_group)
        
        what_text = QTextEdit()
        what_text.setReadOnly(True)
        what_text.setMaximumHeight(100)
        what_text.setHtml("""
        <p>Clean Mac helps you identify and safely remove old, unused files to reclaim disk space on your Mac.</p>
        <p><b>Key Features:</b></p>
        <ul>
        <li>Smart file scanning using Spotlight metadata</li>
        <li>Filter by file type, age, and size</li>
        <li>Safe deletion to Trash with undo support</li>
        <li>Quick Look preview integration</li>
        </ul>
        """)
        what_layout.addWidget(what_text)
        layout.addWidget(what_group)
        
        # Permissions section
        perms_group = QGroupBox("Required Permissions")
        perms_layout = QVBoxLayout(perms_group)
        
        perms_text = QTextEdit()
        perms_text.setReadOnly(True)
        perms_text.setMaximumHeight(120)
        perms_text.setHtml("""
        <p><b>Full Disk Access</b> may be required for scanning certain directories.</p>
        <p>If you encounter permission issues:</p>
        <ol>
        <li>Go to System Settings → Privacy & Security → Full Disk Access</li>
        <li>Add Python or Clean Mac to the list</li>
        <li>Restart the application</li>
        </ol>
        <p><b>Note:</b> Clean Mac never accesses system files or app bundles.</p>
        """)
        perms_layout.addWidget(perms_text)
        
        # Open settings button
        self.open_settings_btn = QPushButton("Open Privacy Settings")
        self.open_settings_btn.setStyleSheet("QPushButton { background-color: #007AFF; color: white; padding: 8px; border-radius: 4px; }")
        perms_layout.addWidget(self.open_settings_btn)
        
        layout.addWidget(perms_group)
        
        # Safety notice
        safety_group = QGroupBox("Safety Notice")
        safety_layout = QVBoxLayout(safety_group)
        
        safety_text = QLabel("""
        <p><b>Clean Mac is designed to be safe:</b></p>
        <ul>
        <li>Never deletes system files or app bundles</li>
        <li>All deletions go to Trash for easy recovery</li>
        <li>Built-in safeguards prevent accidental deletion</li>
        <li>You can always undo the last deletion</li>
        </ul>
        """)
        safety_text.setWordWrap(True)
        safety_layout.addWidget(safety_text)
        layout.addWidget(safety_group)
    
    def _setup_help_content(self, layout):
        """Set up content for returning users."""
        help_group = QGroupBox("Quick Help")
        help_layout = QVBoxLayout(help_group)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h3>Getting Started:</h3>
        <ol>
        <li><b>Choose Roots:</b> Select folders to scan (default: Downloads, Desktop, Documents, Pictures)</li>
        <li><b>Set Filters:</b> Choose minimum age and file size thresholds</li>
        <li><b>Scan:</b> Click "Scan" to find old, unused files</li>
        <li><b>Review:</b> Check the results and select files to delete</li>
        <li><b>Delete:</b> Move selected files to Trash</li>
        </ol>
        
        <h3>Tips:</h3>
        <ul>
        <li>Use "Dry Run" to see what would be deleted without actually deleting</li>
        <li>Use Quick Look to preview files before deleting</li>
        <li>Check the "Ignore dev folders preset" to skip development files</li>
        <li>Use "Undo Last Move" to restore recently deleted files</li>
        </ul>
        """)
        help_layout.addWidget(help_text)
        layout.addWidget(help_group)
    
    def _setup_buttons(self, layout):
        """Set up dialog buttons."""
        button_layout = QHBoxLayout()
        
        # Don't show again checkbox (only for first run)
        if self.is_first_run:
            self.dont_show_again = QCheckBox("Don't show this again")
            button_layout.addWidget(self.dont_show_again)
        
        button_layout.addStretch()
        
        # Close button
        self.close_btn = QPushButton("Get Started")
        self.close_btn.setDefault(True)
        self.close_btn.setStyleSheet("QPushButton { background-color: #007AFF; color: white; padding: 8px 16px; border-radius: 4px; }")
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _setup_connections(self):
        """Set up signal connections."""
        self.close_btn.clicked.connect(self.accept)
        
        if hasattr(self, 'open_settings_btn'):
            self.open_settings_btn.clicked.connect(self._open_privacy_settings)
    
    def _open_privacy_settings(self):
        """Open macOS Privacy & Security settings."""
        import subprocess
        try:
            # Open System Settings to Privacy & Security > Full Disk Access
            subprocess.run([
                "open", 
                "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
            ], check=False)
        except Exception:
            # Fallback to general System Settings
            try:
                subprocess.run(["open", "x-apple.systempreferences:"], check=False)
            except Exception:
                QMessageBox.information(
                    self, 
                    "Settings", 
                    "Please manually open System Settings → Privacy & Security → Full Disk Access"
                )
    
    def should_show_again(self) -> bool:
        """Check if the user wants to see this dialog again."""
        if not self.is_first_run:
            return True  # Always show help for returning users
        
        return not getattr(self, 'dont_show_again', QCheckBox()).isChecked()


def show_onboarding_if_needed(parent=None) -> bool:
    """Show onboarding dialog if needed.
    
    Returns:
        True if dialog was shown, False if skipped
    """
    # Check if we should show onboarding
    from app.workers.util import load_presets
    presets = load_presets()
    show_onboarding = presets.get('show_onboarding', True)
    
    if not show_onboarding:
        return False
    
    dialog = OnboardingDialog(parent)
    result = dialog.exec()
    
    # Save preference if user checked "don't show again"
    if not dialog.should_show_again():
        presets['show_onboarding'] = False
        from app.workers.util import save_presets
        save_presets(presets)
    
    return True
