import os
import time
import pytest
from unittest.mock import patch, Mock
from src.model.downloading_thread import DownloadingThread
from src.utils.utils import FileInfo
import shutil
from src import WORKING_DIR


class TestDropBox:

    @pytest.fixture(autouse=True)
    def setup_downloading_thread(self):
        """setup downloading instance for testing"""
        self.dropboxpath = os.path.join(WORKING_DIR, "dropbox")
        self.testpath = os.path.join(WORKING_DIR, "test")
        # start dropbox daemon
        os.system("python3 -m src -t start")
        # create a directory minic dropbox
        os.makedirs(self.testpath, exist_ok=True)
