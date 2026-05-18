import sys
from PIL import Image, ImageDraw

def add_rounded_corners(im, rad):
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2 - 1, rad * 2 - 1), fill=255)
    alpha = Image.new('L', im.size, 255)
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    return im

def main():
    try:
        im = Image.open('app_icon.png').convert('RGBA')
        
        # Apple standard for rounded corners is roughly width * 0.225
        # The generated image has a bit of padding usually, but let's just apply a standard squircle-like radius
        w, h = im.size
        # The generated icon already has a rounded square drawn inside it, surrounded by black.
        # We need to crop out the black box. Let's find the bounding box of the non-black area,
        # or we just crop the center. Actually, the user's screenshot shows the rounded square is surrounded by dark background.
        # Let's crop it tightly. The generated image is usually 1024x1024.
        # The rounded square in the generated image usually occupies most of the image, let's assume a margin.
        
        # Let's just create a rounded rectangle mask with a 20% margin if needed, but it's easier to just guess the margin.
        # Looking at the icon, the margin is about 10-15%. 
        # Let's crop it.
        margin = int(w * 0.12)
        im_cropped = im.crop((margin, margin, w - margin, h - margin))
        
        w_c, h_c = im_cropped.size
        # Apply rounded corners to the cropped image
        rad = int(w_c * 0.22)
        im_rounded = add_rounded_corners(im_cropped, rad)
        
        # Resize back to 1024x1024
        im_final = im_rounded.resize((1024, 1024), Image.Resampling.LANCZOS)
        im_final.save('app_icon_transparent.png')
        print("Successfully created app_icon_transparent.png")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
