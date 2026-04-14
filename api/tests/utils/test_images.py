from io import BytesIO
from pathlib import Path

from api.utils.images import create_thumbnail


def test_thumbnail():
    image_path = "/Users/ibabiankou/repos/narrator/out/84efd0c9-80b5-46f4-bf13-44b3726baf25/images/page0_XOb18.jpg"
    image_buffer = BytesIO(open(image_path, "rb").read())

    thumbnail_bytes = create_thumbnail(image_buffer)

    dir_path = str(Path(image_path).parent)
    thumbnail_path = f"{dir_path}/thumbnail.webp"

    with open(thumbnail_path, "wb") as f:
        f.write(thumbnail_bytes.getvalue())
