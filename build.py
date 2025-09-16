#!/usr/bin/env python3
"""Build script for Clean Mac app."""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_app():
    """Build the Clean Mac app using PyInstaller."""
    print("🧹 Building Clean Mac...")
    
    # Check if we're in the right directory
    if not Path("CleanMac.spec").exists():
        print("❌ Error: CleanMac.spec not found. Run this from the project root.")
        return False
    
    # Check if icon exists
    icon_path = Path("assets/icon.png")
    if not icon_path.exists():
        print("⚠️  Warning: App icon not found. Creating placeholder...")
        # Create a simple placeholder
        icon_path.parent.mkdir(exist_ok=True)
        icon_path.write_text("# Placeholder icon")
    
    # Clean previous builds
    dist_dir = Path("dist")
    build_dir = Path("build")
    
    if dist_dir.exists():
        print("🧹 Cleaning previous build...")
        shutil.rmtree(dist_dir)
    
    if build_dir.exists():
        print("🧹 Cleaning build cache...")
        shutil.rmtree(build_dir)
    
    # Build the app
    print("🔨 Building app bundle...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller", 
            "--clean",
            "CleanMac.spec"
        ], check=True, capture_output=True, text=True)
        
        print("✅ Build successful!")
        
        # Check if app was created
        app_path = dist_dir / "CleanMac.app"
        if app_path.exists():
            print(f"📦 App created: {app_path.absolute()}")
            print(f"📏 App size: {get_folder_size(app_path):.1f} MB")
            
            # Test the app
            print("🧪 Testing app...")
            test_result = subprocess.run([
                "open", "-W", str(app_path)
            ], check=False, capture_output=True, text=True)
            
            if test_result.returncode == 0:
                print("✅ App test successful!")
            else:
                print("⚠️  App test had issues, but build completed.")
            
            return True
        else:
            print("❌ App bundle not found after build.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def get_folder_size(folder_path):
    """Get the size of a folder in MB."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)  # Convert to MB

def main():
    """Main build function."""
    print("=" * 50)
    print("Clean Mac Build Script")
    print("=" * 50)
    
    success = build_app()
    
    if success:
        print("\n🎉 Build completed successfully!")
        print("\nNext steps:")
        print("1. Test the app in dist/CleanMac.app")
        print("2. Optionally code sign and notarize for distribution")
        print("3. Create a DMG installer (optional)")
    else:
        print("\n❌ Build failed. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
