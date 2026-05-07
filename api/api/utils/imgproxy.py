import hashlib
import hmac
import base64
import os


class ImgProxy:
    def __init__(self, hex_key:str = None, hex_salt:str = None):
        if hex_key is not None:
            self._key = bytes.fromhex(hex_key)
        else:
            self._key = bytes.fromhex(os.getenv("IMGPROXY_KEY", ""))

        if hex_salt is not None:
            self._salt = bytes.fromhex(hex_salt)
        else:
            self._salt = bytes.fromhex(os.getenv("IMGPROXY_SALT", ""))

    def _sign_imgproxy_url(self, path):
        # Calculate HMAC-SHA256
        # Pattern: hmac_sha256(key, salt + path)
        hash_obj = hmac.new(self._key, msg=self._salt + path.encode("utf-8"), digestmod=hashlib.sha256)

        # Encode to Base64URL and remove padding (=)
        signature = base64.urlsafe_b64encode(hash_obj.digest()).rstrip(b"=").decode()

        return signature

    def build_url(self, processing_options:str, source_image_path:str, seo_image_name:str):
        encoded_source = base64.urlsafe_b64encode(source_image_path.encode()).rstrip(b"=").decode()
        path = f"/{processing_options}/{encoded_source}/{seo_image_name}"
        signature = self._sign_imgproxy_url(path)
        return f"/img/{signature}{path}"

    def get_source_image(self, full_path: str) -> str:
        encoded_source = full_path.split('/')[-2]
        return base64.urlsafe_b64decode(encoded_source).decode()
