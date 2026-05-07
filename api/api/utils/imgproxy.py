import hashlib
import hmac
import base64
import os


class ImgProxy:
    def __init__(self, hex_key: str = None, hex_salt: str = None):
        if hex_key is not None:
            self._key = bytes.fromhex(hex_key)
        else:
            self._key = bytes.fromhex(os.getenv("IMGPROXY_KEY", ""))

        if hex_salt is not None:
            self._salt = bytes.fromhex(hex_salt)
        else:
            self._salt = bytes.fromhex(os.getenv("IMGPROXY_SALT", ""))

        self._default_processing_options = os.getenv("DEFAULT_IMGPROXY_OPTS", "rs:fit:400:600:0/f:webp")

    def _sign_imgproxy_url(self, path):
        # Calculate HMAC-SHA256
        # Pattern: hmac_sha256(key, salt + path)
        hash_obj = hmac.new(self._key, msg=self._salt + path.encode("utf-8"), digestmod=hashlib.sha256)

        # Encode to Base64URL and remove padding (=)
        signature = base64.urlsafe_b64encode(hash_obj.digest()).rstrip(b"=").decode()

        return signature

    def build_url(self, source_image_path: str, seo_image_name: str = "cover.webp", processing_options: str = None):
        source_image_path = f"/{source_image_path}" if not source_image_path.startswith("/") else source_image_path
        encoded_source = base64.urlsafe_b64encode(source_image_path.encode()).rstrip(b"=").decode()
        path = f"/{processing_options or self._default_processing_options}/{encoded_source}/{seo_image_name}"
        signature = self._sign_imgproxy_url(path)
        return f"/img/{signature}{path}"

    def get_source_image(self, full_path: str) -> str:
        encoded_source = full_path.split('/')[-2]
        return base64.urlsafe_b64decode(encoded_source).decode()

    def get_default_options(self):
        return self._default_processing_options

    def is_img_proxy_url(self, url: str):
        return url.startswith("/img/")
