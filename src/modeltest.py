import unittest
from unittest.mock import patch, MagicMock, mock_open
from model import DropBoxModel, DropboxInterface
import os
import tempfile
import dropbox

class TestDropBoxModel(unittest.TestCase):

    def setUp(self):
        self.mock_dbx_interface = MagicMock()
        self.rootdir = tempfile.mkdtemp()
        self.model = DropBoxModel(self.mock_dbx_interface, self.rootdir)
       

    def test_read_success(self):
        self.mock_dbx_interface.download.return_value = True
        result = self.model.read("/path/to", "file.txt")
        self.mock_dbx_interface.download.assert_called_once_with("/path/to", "file.txt")
        self.assertEqual(result, 0)

    def test_write_success(self):
        path = "/path/to/file.txt"
        result = self.model.write(path)
        self.assertEqual(result, 0)

    def test_write_path_handling(self):
        path = "path/to/file.txt"
        result = self.model.write(path)
#        self.mock_dbx_interface.upload.assert_called_once_with(self.rootdir+"/path/to/file.txt", "/path/to/file.txt", True)
        self.assertEqual(result, 0)
    
    def test_downloadAll(self):
        mock_file_metadata = MagicMock(spec=dropbox.files.FileMetadata)
        mock_folder_metadata = MagicMock(spec=dropbox.files.FolderMetadata)
      
        self.mock_dbx_interface.list_folder.return_value = {
            "file1.txt": mock_file_metadata,
            "folder1": mock_folder_metadata
        }

        self.mock_dbx_interface.download.side_effect = lambda path, file: open(file, 'w').close()
        self.mock_dbx_interface.download_folder.side_effect = lambda path, file, rootdir: os.makedirs(os.path.join(rootdir, path[1:]))

        self.model.downloadAll()
        print("Contents of self.rootdir:", os.listdir(self.rootdir))

        self.assertTrue(os.path.exists(os.path.join(self.rootdir, "file1.txt")))
        self.assertTrue(os.path.isdir(os.path.join(self.rootdir, "folder1")))

    @patch('os.path.getmtime')
    @patch('builtins.open', new_callable=mock_open, read_data=b'testdata')
    @patch('model.stopwatch')  
    def test_upload_file_success(self, mock_stopwatch, mock_open, mock_getmtime):
        mock_getmtime.return_value = 1580000000.0
        self.mock_dbx.files_upload.return_value = Mock(name='testfile.txt')

        response = self.dbx_interface.upload('testfile.txt', '/testpath/testfile.txt')

        self.assertIsNotNone(response)
        self.mock_dbx.files_upload.assert_called_once()
        mock_stopwatch.assert_called_once()  # 验证如果你正在测试计时

    def test_list_folder_success(self):
        fake_folder_metadata = dropbox.files.ListFolderResult(entries=[
            dropbox.files.FileMetadata(name='testfile1.txt'),
            dropbox.files.FolderMetadata(name='testfolder')
        ])
        self.mock_dbx.files_list_folder.return_value = fake_folder_metadata

        result = self.dbx_interface.list_folder('/testpath')

        self.assertEqual(len(result), 2)
        self.assertIn('testfile1.txt', result)
        self.assertIsInstance(result['testfile1.txt'], dropbox.files.FileMetadata)

    

  
#    def test_upload_large_file(self, mock_dropbox):
#        self.mock_dbx_interface = mock_dropbox.return_value
#        # Simulate the setup for a large file upload session
#        self.mock_dbx_interface.files_upload_session_start.return_value = MagicMock(session_id='fake_session_id')
#        self.mock_dbx_interface.files_upload_session_append_v2 = MagicMock()
#        self.mock_dbx_interface.files_upload_session_finish = MagicMock()
#
#        # Assuming the file size is greater than the chunk size (4MB in your code)
#        large_file_size = 10 * 1024 * 1024  # 10 MB
#        data_chunk = b'x' * (4 * 1024 * 1024)  # 4 MB chunk
#
#        with patch('builtins.open', unittest.mock.mock_open(read_data=data_chunk * 3)), \
#             patch('os.path.getsize', return_value=large_file_size):
#            self.interface.upload_large_file(self.file_path, self.dropbox_path, large_file_size)
#
#        mock_dbx.files_upload_session_start.assert_called_once()
#        # The exact number of calls to append and finish depends on the implementation details and the file size
#        self.assertTrue(mock_dbx.files_upload_session_append_v2.called)
#        self.assertTrue(mock_dbx.files_upload_session_finish.called)





if __name__ == '__main__':
    unittest.main()

