# import os
# import time
# import pytest
# from unittest.mock import patch, Mock
# from src.model.downloading_thread import DownloadingThread
# from src.utils.utils import FileInfo
# import shutil

# class TestDownloadingThread:

#     @pytest.fixture(autouse=True)
#     def setup_downloading_thread(self):
#         """setup downloading instance for testing"""
#         dbx_interface_mock = Mock() 
#         self.tmp_dir = "tst/tmp"
#         self.root_dir = "tst/root"
#         self.downloading_thread = DownloadingThread(dbx_interface_mock, self.tmp_dir, self.root_dir)
#         os.makedirs("tst/tmp", exist_ok=True)
#         os.makedirs("tst/root", exist_ok=True)
#         yield
#         # cleanup all files and directories created during testing
#         # call rm -rf tst/tmp tst/root
#         shutil.rmtree("tst")

    
#     def test_stop(self):
#         self.downloading_thread.stop()
#         assert self.downloading_thread.stop_ == True

#     def test_update_sync_map(self):
#         """test updateSyncMap updates the syncMap with the path and timestamp"""
#         test_path = "some/path"
#         test_timestamp = 123456789
#         self.downloading_thread.updateSyncMap(test_path, test_timestamp)
        
#         assert self.downloading_thread.syncMap[test_path] == test_timestamp

#     def test_retrieve_download_list(self, setup_downloading_thread):
#         """test retrieveDownloadList returns a list of files to download"""
#         os.makedirs("tst/root/dir", exist_ok=True)
#         # write something to the file
#         test_path = "tst/root/file1"
#         test_path2 = "tst/root/dir/file2"
#         with open(test_path, "w") as f:
#             f.write("test")
#         with open(test_path2, "w") as f:
#             f.write("test")
#         metadata = {
#             "/file1": FileInfo("/file1", 0, 123, "hash1", "rev1"),
#             "/dir/file2": FileInfo("/dir/file2",1732090396, 123, "hash2", "rev2"),
#         }
#         mtime = self.downloading_thread.retrieveLocalMTime()
#         download_list = self.downloading_thread.retrieveDownloadList(metadata, mtime)
#         assert download_list == ["/dir/file2"]

#     def test_retrieve_local_mtime(self):
#         """test retrieveLocalMTime returns the local modified time"""
#         os.makedirs("tst/root/dir", exist_ok=True)
#         # write something to the file
#         test_path = "tst/root/testfile.txt"
#         test_path2 = "tst/root/dir/testfile2.txt"
#         with open(test_path, "w") as f:
#             f.write("test")
#         with open(test_path2, "w") as f:
#             f.write("test")
#         test_mtime = 123456789
#         with patch("os.path.getmtime", return_value=test_mtime):
#             mtime = self.downloading_thread.retrieveLocalMTime()
#             assert "/testfile.txt" in mtime
#             assert mtime["/testfile.txt"] == test_mtime
#             assert "/dir/testfile2.txt" in mtime
#             assert mtime["/dir/testfile2.txt"] == test_mtime

#     def test_refresh_local_file(self):
#         """swap files from tmp to root directory"""
#         os.makedirs("tst/tmp/dir", exist_ok=True)
#         old_path = "tst/root/testfile.txt"
#         with open(old_path, "w") as f:
#             f.write("old thing")
#         # assert old file exists
#         assert os.path.exists(old_path)
#         # assert content is correct
#         with open(old_path, "r") as f:
#             assert f.read() == "old thing"
#         # write something to the file
#         test_path = "tst/tmp/testfile.txt"
#         test_path2 = "tst/tmp/dir/testfile2.txt"
#         with open(test_path, "w") as f:
#             f.write("test")
#         with open(test_path2, "w") as f:
#             f.write("test2")
#         metadata = {"/testfile.txt": FileInfo("testfile.txt", 999, 123, "hash1", "rev1"),
#                     "/dir/testfile2.txt": FileInfo("testfile2.txt", 0, 123, "hash2", "rev2")}
#         self.downloading_thread.refreshRootDir(metadata)
#         # assert testfile is moved to root directory
#         assert "/testfile.txt" in self.downloading_thread.syncMap
#         assert os.path.exists("tst/root/testfile.txt")
#         assert not os.path.exists("tst/tmp/testfile.txt")
#         assert "/dir/testfile2.txt" in self.downloading_thread.syncMap
#         assert os.path.exists("tst/root/dir/testfile2.txt")
#         assert not os.path.exists("tst/tmp/dir/testfile2.txt")
#         # assert content is correct
#         with open("tst/root/testfile.txt", "r") as f:
#             assert f.read() == "test"
#         with open("tst/root/dir/testfile2.txt", "r") as f:
#             assert f.read() == "test2"
        
