from api.utils.imgproxy import ImgProxy


def hex_str(val: int):
    hex_string = hex(val)[2:]

    # Ensure an even number of characters
    if len(hex_string) % 2 != 0:
        hex_string = '0' + hex_string
    return hex_string


def test_source_decoding():
    img_proxy = ImgProxy(hex_key=hex_str(12037), hex_salt=hex_str(120314))

    source_url = "/path/to/image.jpg"
    signed_url = img_proxy.build_url("processing_options", source_url, "seo.webp")
    print(signed_url)

    decoded_source_url = img_proxy.get_source_image(signed_url)
    assert decoded_source_url == source_url

def test_no_key_or_salt():
    img_proxy = ImgProxy("", "")
    assert img_proxy._key == b''
    assert img_proxy._salt == b''

    img_proxy._sign_imgproxy_url("/full_path")
