"""Model definition for Open Container Format."""
from typing import List

from pydantic_xml import BaseXmlModel, element, attr


NS_CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
CONTAINER_NS_MAP = {"": NS_CONTAINER}


class RootFile(BaseXmlModel, nsmap=CONTAINER_NS_MAP):
    full_path: str = attr(name="full-path")
    media_type: str = attr(name="media-type")


class RootFiles(BaseXmlModel, tag="rootfiles", nsmap=CONTAINER_NS_MAP):
    items: List[RootFile] = element(tag="rootfile")


class Container(BaseXmlModel,
                tag="container",
                nsmap=CONTAINER_NS_MAP):
    version: str = attr(default="1.0", name="version")
    root_files: RootFiles = element(tag="rootfiles")
