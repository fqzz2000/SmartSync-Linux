import os
import time
import pytest
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
        os.system("python3 -m src start -t")
        # get the auth token
        self.auth_token = os.getenv("MY_APP_AUTH_TOKEN")
        # create a dropbox instance
        self.dropbox = DropboxInterface(self.auth_token)
        yield
        # cleanup all files and directories created during testing
        os.system("python3 -m src stop")
        shutil.rmtree(self.dropboxpath, ignore_errors=True)

    def test_write_rm_file(self):
        # upload a file
        os.system(f"echo 'hello' > {self.dropboxpath}/testfile.txt")
        time.sleep(7)
        res, _ = self.dropbox.list_folder("")
        assert len(res) == 1
        # remove the file
        os.system(f"rm {self.dropboxpath}/testfile.txt")
        time.sleep(1)
        res = self.dropbox.list_folder("")
