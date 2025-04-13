#!/usr/bin/env python
import os
from PIL import Image, ImageDraw, ImageFont

# Ensure the output directory exists
output_dir = 'static/tasks/img/latex'
os.makedirs(output_dir, exist_ok=True)

# Define formulas and their labels (simple text representations)
formulas = {
    'frac': 'a/b',
    'sqrt': '√x',
    'power': 'xⁿ',
    'index': 'xᵢ',
    'sum': 'Σ',
    'integral': '∫',
    'prod': 'Π',
    'limit': 'lim',
    'alpha': 'α',
    'beta': 'β',
    'gamma': 'γ',
    'delta': 'δ',
    'pi': 'π',
    'cases': '{...}',
    'matrix': '[...]',
    'real': 'ℝ',
    'integer': 'ℤ',
    'natural': 'ℕ'
}

# Function to create a simple image with text
def create_formula_image(text, filename, size=(80, 40), bg_color=(255, 255, 255), text_color=(0, 0, 0)):
    # Create a new image with white background
    image = Image.new('RGBA', size, bg_color + (0,))  # Transparent background
    draw = ImageDraw.Draw(image)
    
    # Use a default font
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except IOError:
        font = ImageFont.load_default()
    
    # Calculate text size and position for centering
    text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:4]
    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
    
    # Draw the text
    draw.text(position, text, font=font, fill=text_color)
    
    # Save the image
    image.save(filename, 'PNG')

# Generate images for each formula
for name, formula_text in formulas.items():
    print(f"Generating image for {name}...")
    output_path = os.path.join(output_dir, f"{name}.png")
    create_formula_image(formula_text, output_path)

print("All LaTeX formula images have been generated!") 