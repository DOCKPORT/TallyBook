import os
import sys
import qrcode
from PIL import Image, ImageDraw

def generate_qr(address: str, filename: str = "qr_code.png", logo_path: str = None, bg_color=(0, 0, 0, 255)):
    """
    Generates a QR code for the given address and saves it in the same directory as this script.
    Optionally overlays a logo image in the center with a rounded rectangle background.
    """
    # Use Error Correction High to ensure readability even with a logo overlay
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(address)
    qr.make(fit=True)

    # Create the QR image in RGB mode
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # If there is a logo path and it exists, overlay it in the center
    if logo_path and os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        
        # Calculate dimensions
        qr_width, qr_height = img.size
        
        # Limit logo size to max 22% of the QR code size
        max_logo_size = int(qr_width * 0.22)
        
        # Resize logo keeping aspect ratio
        logo.thumbnail((max_logo_size, max_logo_size), Image.Resampling.LANCZOS)
        
        # Calculate coordinates to center the logo
        logo_width, logo_height = logo.size
        x = (qr_width - logo_width) // 2
        y = (qr_height - logo_height) // 2
        
        # Create a blank transparent base image for the rounded rectangle background
        bg_margin = 6
        bg_width = logo_width + bg_margin * 2
        bg_height = logo_height + bg_margin * 2
        bg_logo = Image.new("RGBA", (bg_width, bg_height), (0, 0, 0, 0))
        
        # Draw the rounded black background
        draw = ImageDraw.Draw(bg_logo)
        corner_radius = 8
        draw.rounded_rectangle(
            [(0, 0), (bg_width - 1, bg_height - 1)],
            radius=corner_radius,
            fill=bg_color
        )
        
        # Paste the logo on top of the black rounded background margin
        bg_logo.paste(logo, (bg_margin, bg_margin), mask=logo)
        
        # Paste the combined background + logo on top of the QR code
        img.paste(bg_logo, (x - bg_margin, y - bg_margin), mask=bg_logo)

    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, filename)

    # Save the file
    img.save(output_path)
    print(f"Success! QR code for '{address}' saved to: {output_path}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Defaults
    addr = None
    logo_file = None
    
    if len(sys.argv) > 1:
        addr = sys.argv[1]
        if len(sys.argv) > 2:
            logo_file = sys.argv[2]
            # Try to resolve full path
            if not os.path.isabs(logo_file):
                logo_file = os.path.join(script_dir, logo_file)
    else:
        addr = input("Enter the address (URL or text) to generate a QR code for: ").strip()
        use_logo = input("Enter logo filename (e.g. sol.png) or leave blank: ").strip()
        if use_logo:
            logo_file = os.path.join(script_dir, use_logo)

    if addr:
        # Generate custom filename for this QR code based on the address
        safe_addr_part = "".join([c for c in addr if c.isalnum()])[:8]
        output_filename = f"qr_{safe_addr_part}.png" if safe_addr_part else "qr_code.png"

        generate_qr(addr, filename=output_filename, logo_path=logo_file)
    else:
        print("No address provided. Exiting.")
