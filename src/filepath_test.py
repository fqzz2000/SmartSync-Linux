import pytest
from .utils import FilePath

def test_FilePath():
    fp = FilePath("/root", "/tmp")

    # Test getTmpPath
    assert fp.getTmpPath("/path/to/file") == "/tmp/path/to/file"
    assert fp.getTmpPath("path/to/file") == "/tmp/path/to/file"
    assert fp.getTmpPath("") == "/tmp/"

    # Test getLocalPath
    assert fp.getLocalPath("/path/to/file") == "/root/path/to/file"
    assert fp.getLocalPath("path/to/file") == "/root/path/to/file"
    assert fp.getLocalPath("") == "/root/"

    # Test getRemotePath
    assert fp.getRemotePath("") == "/"
    assert fp.getRemotePath("/path/to/file") == "/path/to/file"
    assert fp.getRemotePath("path/to/file") == "/path/to/file"
