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


def compareDirectories(dir1, dir2):
    for dirpath, dirnames, filenames in os.walk(dir1):
        for filename in filenames:
            file1 = os.path.join(dirpath, filename)
            file2 = os.path.join(dirpath.replace(dir1, dir2), filename)
            assert os.path.exists(file2)
            assert os.path.getsize(file1) == os.path.getsize(file2)


class TestDropBox:

    @pytest.fixture(autouse=True)
    def setup_downloading_thread(self):
        """setup downloading instance for testing"""

        self.dropboxpath = os.path.join(WORKING_DIR, "dropbox")
        # cleanup the directory
        shutil.rmtree(self.dropboxpath, ignore_errors=True)
        # start dropbox daemon
        self.process = subprocess.Popen(
            ["bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.process.stdin.write("python3 -m src start -t\n")
        self.process.stdin.flush()
        print("Dropbox started")
        # get the auth token
        self.auth_token = os.getenv("MY_APP_AUTH_TOKEN")
        # create a dropbox instance
        self.dropbox = DropboxInterface(self.auth_token)
        yield
        # cleanup all files and directories created during testing
        self.process.stdin.write("python3 -m src stop\n")
        self.process.stdin.flush()
        shutil.rmtree(self.dropboxpath, ignore_errors=True)

    def test_write_rm_file(self):
        # upload a file

        self.process.stdin.write(f"echo 'hello' > {self.dropboxpath}/testfile.txt\n")
        self.process.stdin.flush()
        time.sleep(10)
        res, _ = self.dropbox.list_folder("")
        print(res)
        assert len(res) == 1
        # remove the file
        self.process.stdin.write(f"rm {self.dropboxpath}/testfile.txt\n")
        time.sleep(1)
        res = self.dropbox.list_folder("")
        assert len(res) == 0


if __name__ == "__main__":
    pass
