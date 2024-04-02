# interface layer to the dropbox api
import dropbox
import zipfile
import os
import time
import datetime
import contextlib
from loguru import logger

@contextlib.contextmanager
def stopwatch(message):
    """Context manager to print how long a block of code took."""
    t0 = time.time()
    try:
        yield
    finally:
        t1 = time.time()
        print('Total elapsed time for %s: %.3f' % (message, t1 - t0))

class DropboxInterface:
    def __init__(self, token):
        self.dbx = dropbox.Dropbox(token)
        
    def list_folder(self, path, recursive=False):
        res = self.dbx.files_list_folder(path, recursive=recursive)
        rv = {}
        for entry in res.entries:
            rv[entry.name] = entry
        return rv
    
    def upload(self, file, path, overwrite=False):
        """Upload a file.

        Return the request response, or None in case of error.
        """
        mode = (dropbox.files.WriteMode.overwrite
                if overwrite
                else dropbox.files.WriteMode.add)
        mtime = os.path.getmtime(file)
        print(file)
        with open(file, 'rb') as f:
            data = f.read()
        with stopwatch('upload %d bytes' % len(data)):
            try:
                if len(data) <= 150 * 1024 * 1024:
                    res = self.dbx.files_upload(
                        data, path, mode,
                        client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                        mute=True,
                        autorename=True)
                    logger.warning(f'uploaded as {res.name}')
                    return res
                else:
                    self.upload_large_file(file, path, len(data))
                    logger.warning(f'uploaded as {path}')
            except dropbox.exceptions.ApiError as err:
                print('*** API error', err)
                return None
        

    def upload_large_file(self, file, path, size):
        CHUNK_SIZE = 10 * 1024 * 1024
        logger.warning(f"Uploading {file} to {path} with size {size}")
        with open(file, "rb") as f:
            upload_session_start_result = self.dbx.files_upload_session_start(f.read(CHUNK_SIZE))
            cursor = dropbox.files.UploadSessionCursor(session_id=upload_session_start_result.session_id,
                                                        offset=f.tell())
            commit = dropbox.files.CommitInfo(path=path, mode=dropbox.files.WriteMode.overwrite)

            while f.tell() < size:
                #logger.warning(f"Uploaded {f.tell()} of {size}")
                if (size - f.tell()) <= CHUNK_SIZE:
                    self.dbx.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit)
                else:
                    self.dbx.files_upload_session_append_v2(f.read(CHUNK_SIZE), cursor)
                    cursor.offset = f.tell()

    def download(self, path, file):
        self.dbx.files_download_to_file(file, path)

    def download_folder(self, path, file, rootdir):
        zip_file_path = file + ".zip"
        self.dbx.files_download_zip_to_file(zip_file_path, path)
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(rootdir)
        os.remove(zip_file_path)

    def mkdir(self, path):
        self.dbx.files_create_folder(path)
    
    def delete(self, path):
        self.dbx.files_delete(path)

    def getmetadata(self, path):
        rc = self.dbx.files_get_metadata(path)
        ret = {}
        ret["name"] = rc.name
        ret["preview_url"] = rc.preview_url

        return ret 
    
    def move(self, from_path, to_path):
        self.dbx.files_move(from_path, to_path, autorename=True)

    def users_get_space_usage(self):
        try:
            usage = self.dbx.users_get_space_usage()
            total_space = usage.allocation.get_individual().allocated
            used_space = usage.used
            return total_space, used_space
        except dropbox.exceptions.ApiError as err:
            print(f"API Error: {err}")
            return 0, 0

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: {} <token>".format(sys.argv[0]))
        sys.exit(1)
    rootPath = "/home/tq22/ece566/SmartSync-Linux/cache"
    db = DropboxInterface(sys.argv[1])
    dic = db.list_folder("")
    for k, v in dic.items():
        print(k, v)

    