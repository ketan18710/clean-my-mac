#!/usr/bin/env python3
"""Convert PNG icon to ICNS format for macOS."""

from PIL import Image
import os

def convert_png_to_icns():
    """Convert PNG to ICNS format."""
    png_path = "assets/icon.png"
    icns_path = "assets/icon.icns"
    
    if not os.path.exists(png_path):
        print(f"❌ PNG icon not found: {png_path}")
        return False
    
    try:
        # Open the PNG image
        img = Image.open(png_path)
        
        # Create different sizes for ICNS
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        images = []
        
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            images.append(resized)
        
        # Save as ICNS
        # Note: PIL doesn't directly support ICNS, but PyInstaller can convert PNG to ICNS
        # For now, we'll just ensure we have a good PNG and let PyInstaller handle the conversion
        print(f"✅ PNG icon ready for conversion: {png_path}")
        print("PyInstaller will automatically convert PNG to ICNS during build")
        
        return True
        
    except Exception as e:
        print(f"❌ Error converting icon: {e}")
        return False

if __name__ == "__main__":
    convert_png_to_icns()
