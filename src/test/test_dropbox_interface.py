import unittest
from unittest.mock import patch, MagicMock, mock_open
import dropbox
import sys
sys.path.append('..')

from data import DropboxInterface 
class TestDropboxInterface(unittest.TestCase):
        
    def setUp(self):
        self.token = 'fake_token'  
        self.interface = DropboxInterface(self.token)

    @patch('data.dropbox.Dropbox')
    def test_list_folder(self, mock_dropbox):
        mock_response = MagicMock()
        mock_entry = MagicMock()
        mock_entry.name = 'test_file.txt'
        mock_response.entries = [mock_entry]
        mock_dropbox.return_value.files_list_folder.return_value = mock_response

        dbx_interface = DropboxInterface('fake_token')
        result = dbx_interface.list_folder('')
 
        self.assertIn('test_file.txt', result)
        self.assertEqual(mock_entry, result['test_file.txt'])


    @patch('data.dropbox.files.WriteMode')
    @patch('data.os.path.getmtime')
    @patch('data.time.gmtime')
    @patch('data.open', new_callable=unittest.mock.mock_open, read_data=b'some data')
    @patch('data.dropbox.Dropbox')
    def test_upload_small_file(self, mock_dropbox, mock_open, mock_gmtime, mock_getmtime, mock_write_mode):
      
        mock_getmtime.return_value = 1000  
        mock_gmtime.return_value = (2020, 1, 1, 0, 0, 0)
        mock_response = MagicMock()
        mock_response.name = 'test_file.txt'
        mock_dropbox().files_upload.return_value = mock_response

        dbx_interface = DropboxInterface('fake_token')
        result = dbx_interface.upload('fake_file_path', '/fake_dropbox_path')

        mock_dropbox().files_upload.assert_called_once()
        self.assertEqual(result.name, 'test_file.txt')

    @patch('data.dropbox.files.UploadSessionCursor')
    @patch('data.dropbox.files.CommitInfo')
    @patch('data.dropbox.Dropbox')
    def test_upload_large_file(self, mock_dropbox, mock_commit_info, mock_upload_session_cursor):

        mock_session_start_response = MagicMock()
        mock_session_start_response.session_id = 'fake_session_id'
        mock_dropbox().files_upload_session_start.return_value = mock_session_start_response

        file_content = b'a' * (10 * 1024 * 1024 + 1)  # 8MB + 1bytes
        m_open = mock_open(read_data=file_content)

        m_open.return_value.tell.side_effect = [0, 10 * 1024 * 1024, 4 * 1024 * 1024, 10 * 1024 * 1024 + 1, 10 * 1024 * 1024 + 1]

        with patch('data.open', m_open, create=True):
            dbx_interface = DropboxInterface('fake_token')
            dbx_interface.upload_large_file('fake_file_path', '/fake_dropbox_path', 10 * 1024 * 1024 + 1)

            mock_dropbox().files_upload_session_start.assert_called_once()
#            mock_dropbox().files_upload_session_append_v2.assert_called()
            mock_dropbox().files_upload_session_finish.assert_called_once()

    
    @patch('data.dropbox.Dropbox')
    def test_download(self, mock_dropbox):
       
        dbx_interface = DropboxInterface('fake_token')
        dbx_interface.download('/fake_dropbox_path', 'fake_file_path')
        mock_dropbox().files_download_to_file.assert_called_once_with('fake_file_path', '/fake_dropbox_path')


    @patch('data.dropbox.Dropbox')
    @patch('data.zipfile.ZipFile')
    @patch('data.os.remove')
    def test_download_folder(self, mock_remove, mock_zipfile, mock_dropbox):

        
        dbx_interface = DropboxInterface('fake_token')
        mock_zipfile.return_value.__enter__.return_value.extractall = lambda rootdir: None

        dbx_interface.download_folder('/fake_dropbox_path', 'fake_file', 'fake_rootdir')
 
        mock_dropbox().files_download_zip_to_file.assert_called_once_with('fake_file.zip', '/fake_dropbox_path')
        mock_zipfile.assert_called_once_with('fake_file.zip', 'r')
        mock_remove.assert_called_once_with('fake_file.zip')
   
    @patch('data.dropbox.Dropbox')
    def test_mkdir(self, mock_dropbox):
        
        dbx_interface = DropboxInterface('fake_token')
        dbx_interface.mkdir('/fake_dropbox_folder')
        mock_dropbox().files_create_folder.assert_called_once_with('/fake_dropbox_folder')

    @patch('data.dropbox.Dropbox')
    def test_delete(self, mock_dropbox):
        
        dbx_interface = DropboxInterface('fake_token')
        dbx_interface.delete('/fake_dropbox_file')
        mock_dropbox().files_delete.assert_called_once_with('/fake_dropbox_file')

    @patch('data.dropbox.Dropbox')
    def test_getmetadata(self, mock_dropbox):
        
        dbx_interface = DropboxInterface('fake_token')

        mock_metadata = MagicMock()
        mock_metadata.name = 'fake_name'
        mock_metadata.preview_url = 'http://fakeurl.com'
        mock_dropbox().files_get_metadata.return_value = mock_metadata


        result = dbx_interface.getmetadata('/fake_dropbox_path')

        mock_dropbox().files_get_metadata.assert_called_once_with('/fake_dropbox_path')

        self.assertEqual(result['name'], 'fake_name')
        self.assertEqual(result['preview_url'], 'http://fakeurl.com')

    @patch('data.dropbox.Dropbox')
    def test_move(self, mock_dropbox):
        
        dbx_interface = DropboxInterface('fake_token')
        dbx_interface.move('/from_path', '/to_path')
        mock_dropbox().files_move.assert_called_once_with('/from_path', '/to_path', autorename=True)

    @patch('data.dropbox.Dropbox')
    def test_users_get_space_usage(self, mock_dropbox):
        
        mock_space_usage = MagicMock()
        mock_space_usage.used = 500
        mock_space_usage.allocation.get_individual.return_value.allocated = 1000
        mock_dropbox().users_get_space_usage.return_value = mock_space_usage

        dbx_interface = DropboxInterface('fake_token')

        total_space, used_space = dbx_interface.users_get_space_usage()

        self.assertEqual(total_space, 1000)
        self.assertEqual(used_space, 500)

if __name__ == '__main__':
    unittest.main()

