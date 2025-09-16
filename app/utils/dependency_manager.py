"""Dependency management for Clean Mac."""

import subprocess
import sys
import importlib
from typing import List, Tuple, Optional

# Required dependencies with their import names and pip names
REQUIRED_DEPENDENCIES = [
    ("PySide6", "PySide6"),
    ("send2trash", "send2trash"),
    ("platformdirs", "platformdirs"),
    ("rich", "rich"),
]

# Optional dependencies (nice to have but not critical)
OPTIONAL_DEPENDENCIES = [
    ("PIL", "pillow"),
]

class DependencyManager:
    """Manages checking and installing required dependencies."""
    
    def __init__(self):
        self.missing_deps: List[str] = []
        self.optional_missing: List[str] = []
    
    def check_all_dependencies(self) -> Tuple[bool, List[str]]:
        """Check all required and optional dependencies.
        
        Returns:
            Tuple of (all_required_available, list_of_missing_required)
        """
        self.missing_deps = []
        self.optional_missing = []
        
        # Check required dependencies
        for import_name, pip_name in REQUIRED_DEPENDENCIES:
            if not self._check_dependency(import_name):
                self.missing_deps.append(pip_name)
        
        # Check optional dependencies
        for import_name, pip_name in OPTIONAL_DEPENDENCIES:
            if not self._check_dependency(import_name):
                self.optional_missing.append(pip_name)
        
        return len(self.missing_deps) == 0, self.missing_deps
    
    def _check_dependency(self, import_name: str) -> bool:
        """Check if a dependency can be imported."""
        try:
            importlib.import_module(import_name)
            return True
        except ImportError:
            return False
    
    def install_dependencies(self, deps: List[str]) -> bool:
        """Install missing dependencies using pip.
        
        Args:
            deps: List of package names to install
            
        Returns:
            True if all installations succeeded, False otherwise
        """
        if not deps:
            return True
        
        try:
            # Use the same Python executable that's running this script
            python_exe = sys.executable
            
            # Install packages
            cmd = [python_exe, "-m", "pip", "install"] + deps
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            print(f"Successfully installed: {', '.join(deps)}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to install dependencies: {e}")
            print(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            print(f"Unexpected error installing dependencies: {e}")
            return False
    
    def get_installation_status(self) -> str:
        """Get a human-readable status of dependency installation."""
        if not self.missing_deps and not self.optional_missing:
            return "All dependencies are available"
        
        status_parts = []
        
        if self.missing_deps:
            status_parts.append(f"Missing required: {', '.join(self.missing_deps)}")
        
        if self.optional_missing:
            status_parts.append(f"Missing optional: {', '.join(self.optional_missing)}")
        
        return "; ".join(status_parts)
    
    def auto_install_missing(self) -> bool:
        """Automatically install missing required dependencies.
        
        Returns:
            True if all required dependencies are now available
        """
        if not self.missing_deps:
            return True
        
        print(f"Installing missing dependencies: {', '.join(self.missing_deps)}")
        success = self.install_dependencies(self.missing_deps)
        
        if success:
            # Re-check to make sure installation worked
            all_available, still_missing = self.check_all_dependencies()
            return all_available
        
        return False


def check_and_install_dependencies() -> bool:
    """Convenience function to check and install dependencies.
    
    Returns:
        True if all required dependencies are available
    """
    manager = DependencyManager()
    
    # Check current status
    all_available, missing = manager.check_all_dependencies()
    
    if all_available:
        print("All required dependencies are available")
        return True
    
    print(f"Missing dependencies: {', '.join(missing)}")
    print("Attempting to install missing dependencies...")
    
    # Try to install missing dependencies
    success = manager.auto_install_missing()
    
    if success:
        print("All dependencies are now available")
    else:
        print("Failed to install some dependencies")
        print("Please install manually: pip install " + " ".join(missing))
    
    return success
