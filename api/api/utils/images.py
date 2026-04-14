from io import BytesIO

from PIL import Image


def create_thumbnail(image_bytes: BytesIO, size = (300, 400), quality=90):
    try:
        with Image.open(image_bytes) as img:
            # Convert to RGBA if necessary
            # This preserves transparency for WebP
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")

            # Maintains the aspect ratio automatically
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Save to WebP in a memory buffer
            output_buffer = BytesIO()
            img.save(output_buffer, format="WEBP", quality=quality)

            return output_buffer

    except Exception as e:
        print(f"Error processing image: {e}")
        return None
