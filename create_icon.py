#!/usr/bin/env python3
"""Create a simple app icon for Clean Mac."""

from PIL import Image, ImageDraw, ImageFont
import os

def create_app_icon():
    # Create a 512x512 icon (standard macOS app icon size)
    size = 512
    img = Image.new('RGBA', (size, size), (255, 255, 255, 255))  # White background
    draw = ImageDraw.Draw(img)
    
    # Create a simple black border
    margin = 20
    border_rect = [margin, margin, size - margin, size - margin]
    draw.rounded_rectangle(border_rect, radius=50, fill=None, outline=(0, 0, 0, 255), width=8)
    
    # Draw a simple trash can icon in black
    trash_x, trash_y = size // 2, size // 2
    trash_size = 200
    
    # Trash can body (black)
    body_rect = [trash_x - trash_size//3, trash_y - trash_size//6, 
                 trash_x + trash_size//3, trash_y + trash_size//2]
    draw.rounded_rectangle(body_rect, radius=20, fill=(0, 0, 0, 255))
    
    # Trash can lid (black)
    lid_rect = [trash_x - trash_size//2, trash_y - trash_size//3, 
                trash_x + trash_size//2, trash_y - trash_size//8]
    draw.rounded_rectangle(lid_rect, radius=15, fill=(0, 0, 0, 255))
    
    # Trash can handle (black)
    handle_rect = [trash_x - trash_size//5, trash_y - trash_size//2, 
                   trash_x + trash_size//5, trash_y - trash_size//3]
    draw.rounded_rectangle(handle_rect, radius=10, fill=(0, 0, 0, 255))
    
    # Add a simple "C" for Clean Mac in the top-left corner
    font_size = 80
    try:
        # Try to use a system font
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Draw "C" in the top-left corner
    c_x, c_y = 60, 60
    draw.text((c_x, c_y), "C", font=font, fill=(0, 0, 0, 255))
    
    # Save as PNG
    img.save('assets/icon.png')
    print("Created assets/icon.png")
    
    # Also create a smaller version for the app
    small_img = img.resize((256, 256), Image.Resampling.LANCZOS)
    small_img.save('assets/icon_256.png')
    print("Created assets/icon_256.png")

if __name__ == "__main__":
    try:
        from math import cos, sin, radians
        create_app_icon()
    except ImportError:
        print("PIL not available, creating a simple placeholder icon...")
        # Create a simple text-based icon as fallback
        os.makedirs('assets', exist_ok=True)
        with open('assets/icon.png', 'w') as f:
            f.write("# Placeholder for app icon")
        print("Created placeholder icon file")
