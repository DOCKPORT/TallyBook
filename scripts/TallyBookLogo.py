#!/usr/bin/env python3
from PIL import Image, ImageDraw
import os

def create_logo():
    # Dimensions
    width, height = 1024, 1024
    
    # Colors
    transparent = (0, 0, 0, 0)
    bg_color = "#121212"   # Deep Charcoal
    orange_accent = "#FF9500"  # Vibrant Financial Orange
    
    # Create image with transparency
    img = Image.new('RGBA', (width, height), transparent)
    draw = ImageDraw.Draw(img)
    
    # 1. Draw the App Icon Background (Rounded Square)
    icon_padding = 40 
    icon_rect = [icon_padding, icon_padding, width - icon_padding, height - icon_padding]
    draw.rounded_rectangle(icon_rect, radius=200, fill=bg_color)
    
    # Concept: "Modern Abstract Ledger"
    # Sharp, symmetrical wings representing growth and data rows.
    cx, cy = width // 2, height // 2
    
    # Geometry Proportions
    full_h = 560
    start_y = cy - (full_h // 2)
    end_y = start_y + full_h
    
    w_top = 780
    w_bottom = 220
    
    # 2. Draw the Combined Abstract Shield (Wings Touching)
    # Points: Top-Left, Top-Right, Bottom-Right, Bottom-Left
    # We can draw it as a single polygon for a perfectly solid look.
    shield_pts = [
        (cx - (w_top // 2), start_y), # Top Left
        (cx + (w_top // 2), start_y), # Top Right
        (cx + (w_bottom // 2), end_y), # Bottom Right
        (cx - (w_bottom // 2), end_y)  # Bottom Left
    ]
    draw.polygon(shield_pts, fill=orange_accent)
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tallybook_app_icon.png")
    img.save(output_path)
    print(f"App icon saved to {output_path}")

if __name__ == "__main__":
    create_logo()
