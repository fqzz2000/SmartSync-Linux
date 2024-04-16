import os
import subprocess
import time
import pytest

import os
import sys

# add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
print(sys.path)

from unittest.mock import patch, Mock
from src.data.data import DropboxInterface
from src.utils.utils import FileInfo
import shutil

WORKING_DIR = os.path.expanduser("~/Desktop")


class TestDropBox:

    @pytest.fixture(autouse=True)
    def setup(self):
        token = os.environ.get("MY_APP_AUTH_TOKEN")
        self.dropbox = DropboxInterface(token)

    def test_write_rm_file(self):
        # upload a file
        os.system("echo 'hello world' > ~/Desktop/dropbox/testfile.txt")
        time.sleep(10)
        res, _ = self.dropbox.list_folder("")
        print(res)
        assert len(res) == 1
        # remove the file
        os.system("rm ~/Desktop/dropbox/testfile.txt")
        time.sleep(1)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 0

    def test_multiple_write(self):
        # upload 100 files
        for i in range(10):
            os.system(f"echo 'hello world {i}' > ~/Desktop/dropbox/testfile{i}.txt")
        time.sleep(20)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 10
        # remove the files
        for i in range(10):
            os.system(f"rm ~/Desktop/dropbox/testfile{i}.txt")
        time.sleep(5)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 0
        time.sleep(5)

    def test_write_rm_dir(self):
        # create a directory
        os.system("mkdir ~/Desktop/dropbox/testdir")
        time.sleep(10)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 1
        # remove the directory
        os.system("rm -r ~/Desktop/dropbox/testdir")
        time.sleep(1)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 0
        time.sleep(5)

    def test_write_dir_and_file_no_same_name(self):
        # create a directory
        os.system("mkdir ~/Desktop/dropbox/testdir")
        time.sleep(10)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 1
        # create a file
        os.system("echo 'hello world' > ~/Desktop/dropbox/testfile.txt")
        # create 10 files in the directory
        for i in range(10):
            os.system(
                f"echo 'hello world {i}' > ~/Desktop/dropbox/testdir/testfile{i}.txt"
            )
        # create a directory in the directory
        os.system("mkdir ~/Desktop/dropbox/testdir/testdir2")
        # create 5 files in the directory in the directory
        for i in range(5):
            os.system(
                f"echo 'hello world {i}' > ~/Desktop/dropbox/testdir/testdir2/testfile2{i}.txt"
            )
        time.sleep(40)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 2
        res, _ = self.dropbox.list_folder("", recursive=True)
        print(res.keys())
        assert len(res) == 18
        # remove the directory
        os.system("rm -r ~/Desktop/dropbox/testdir")
        time.sleep(5)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 1
        # remove the file
        os.system("rm ~/Desktop/dropbox/testfile.txt")
        time.sleep(5)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 0
        time.sleep(5)

    def test_write_dir_and_file_same_name(self):
        # create a directory
        os.system("mkdir ~/Desktop/dropbox/testdir")
        time.sleep(10)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 1
        # create a file
        os.system("echo 'hello world' > ~/Desktop/dropbox/testfile.txt")
        # create 10 files in the directory
        for i in range(10):
            os.system(
                f"echo 'hello world {i}' > ~/Desktop/dropbox/testdir/testfile{i}.txt"
            )
        # create a directory in the directory
        os.system("mkdir ~/Desktop/dropbox/testdir/testdir")
        # create 5 files in the directory in the directory
        for i in range(5):
            os.system(
                f"echo 'hello world {i}' > ~/Desktop/dropbox/testdir/testdir/testfile{i}.txt"
            )
        time.sleep(40)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 2
        res, _ = self.dropbox.list_folder("", recursive=True)
        print(res.keys())
        assert len(res) == 18
        # remove the directory
        os.system("rm -r ~/Desktop/dropbox/testdir")
        time.sleep(5)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 1
        # remove the file
        os.system("rm ~/Desktop/dropbox/testfile.txt")
        time.sleep(5)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 0
        time.sleep(5)


if __name__ == "__main__":
    pass
