# commandline interface for the program
from collections import deque
import sys
import threading
import time
from src.data.data import DropboxInterface
from src.model.uploading_thread import UploadingThread
from src.model.downloading_thread import DownloadingThread
from src.fuselayer.fuselayer import FuseDropBox
from src.lib import FUSE
import os
import shutil
from zoneinfo import ZoneInfo  # Python 3.9+
from tzlocal import get_localzone
import dropbox
from functools import wraps
from loguru import logger
import json
import fcntl


def lockWrapper(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.mutex.acquire()
        ret = func(self, *args, **kwargs)
        self.mutex.release()
        return ret
    return wrapper


class DropBoxModel():

    def __init__(self, interface, rootdir, swapdir) -> None:
        self.dbx = interface
        self.rootdir = rootdir
        self.swapdir = swapdir
        self.mutex = threading.Lock()
        self.synchronizeThread = UploadingThread(self.dbx, self.mutex)
        self.downloadingThread = DownloadingThread(self.dbx, self.swapdir, self.rootdir)
        self.thread = threading.Thread(target=self.synchronizeThread)
        self.dthread = threading.Thread(target=self.downloadingThread)
        self.thread.start()
        self.dthread.start()
        print("Model initialized")

    def stop(self):
        self.synchronizeThread.stop()
        self.downloadingThread.stop()
        self.thread.join()

    def fetchOneMetadata(self, path:str) -> dict:
        '''
        get the metadata of the file
        '''
        try:
            file = {path: self.dbx.getmetadata(path)}
            return self.formatMetadata(file)
        except Exception as e:
            print(e)
            return None

    def fetchDirMetadata(self, path:str) -> dict:
        '''
        list the folder in the dropbox
        '''
        list_folder_path = path if path != "/" else ""
        try:
            files,_ = self.dbx.list_folder(list_folder_path)
            return self.formatMetadata(files)

        except Exception as e:
            print(e)
            return None
    
    def formatMetadata(self, files) -> dict:
        '''
        format the metadata to the format that the fuse layer can understand
        '''
        metadata = {}
        local_zone = get_localzone()
        for k, v in files.items():
            if isinstance(v,dropbox.files.FileMetadata):
                mtime = max(v.client_modified, v.server_modified)
                utc_time = mtime.replace(tzinfo=ZoneInfo("UTC"))
                local_time = utc_time.astimezone(local_zone)

                metadata[v.path_display] = {
                "name": v.name,
                "size": v.size,
                "type": "file",
                "mtime": local_time.isoformat(),
                "uploaded": True
                }
            elif isinstance(v, dropbox.files.FolderMetadata):
                metadata[v.path_display] = {
                "name": v.name,
                "size": None, 
                "type": "folder",
                "mtime": None,
                "uploaded": True
                }

        return metadata

    def flushMetadata(self, metadata:dict):
        '''
        flush the metadata to the file
        '''
        metadata_file_path = '/tmp/dropbox/metadata.json'
        logger.warning(f"Ready to flush, metadata: {metadata}")
        with open(metadata_file_path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                logger.warning(f"Flushing metadata to file, metadata: {metadata}")
                json.dump(metadata, f, indent=4)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def flushMetadataAsync(self, metadata:dict):
        '''
        flush the metadata to the file asynchronously
        '''
        flushThread = threading.Thread(target=self.flushMetadata, args=(metadata,))
        flushThread.start()

    @lockWrapper
    def write(self, path:str, completion_handler) -> int:
        '''
        upload the file to dropbox
        '''
        if len(path) == 0 or path[0] != "/":
            path = "/" + path
        try:
            self.synchronizeThread.addTask(self.rootdir+path, path, completion_handler)
            return 0
        except Exception as e:
            print(e)
            return -1

    @lockWrapper
    def createFolder(self, path:str, mode) -> int:
        '''
        create a folder in the dropbox
        '''
        try:
            new_path = os.path.join(self.rootdir, path)
            os.mkdir(new_path, mode)
            self.dbx.mkdir("/" + path)
            return 0
        except Exception as e:
            print(e)
            return -1

    @lockWrapper
    def deleteFolder(self, path:str) -> int:
        '''
        delete a file in the dropbox
        '''
        try:
            new_path = os.path.join(self.rootdir, path)
            os.rmdir(new_path)
            self.dbx.delete("/" + path)
            return 0
        except Exception as e:
            print(e)
            return -1
        
    @lockWrapper
    def deleteFile(self, path:str) -> int:
        '''
        delete a file in the dropbox
        '''
        try:
            new_path = os.path.join(self.rootdir, path)
            os.unlink(new_path)
            self.dbx.delete("/" + path)
            return 0
        except Exception as e:
            print(e)
            return -1
        
    def open_file(self, path, local_path):
        lockfile_path = f"{local_path}.lock"
        with open(lockfile_path, 'w') as lockfile:
            try:
                fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB) # throw an exception if the file is locked
                self.dbx.download(path, local_path)
            except BlockingIOError:
                logger.warning(f"Fail to download")
                fcntl.flock(lockfile, fcntl.LOCK_EX) # blocked until the file is unlocked
            finally:
                if os.path.exists(lockfile_path):
                    os.remove(lockfile_path)
        
    @lockWrapper
    def move(self, old:str, new:str) -> int:
        '''
        rename a file in the dropbox
        '''
        try:
            old_path = os.path.join(self.rootdir, old)
            new_path = os.path.join(self.rootdir, new)
            os.rename(old_path, new_path)
            self.dbx.move("/" + old, "/" + new)
            return 0
        except Exception as e:
            print(e)
            return -1
    
    def getSpaceUsage(self) -> dict:
        '''
        get the space usage of the dropbox
        '''
        try:
            return self.dbx.users_get_space_usage()
        except Exception as e:
            print(e)
            return None

    # def fetchAllMetadata(self):
    #     """
    #     List all files and folders in the Dropbox and save their metadata to a file in JSON format.
    #     """
    #     # metadata = {}
    #     # metadata_file_path = '/tmp/dropbox/metadata.json'
    #     # local_zone = ZoneInfo.localzone()
    #     # local_zone = get_localzone()
    #     try:
    #         files,_ = self.dbx.list_folder("", recursive=True)
    #         return self.formatMetadata(files)
    #         # with open(metadata_file_path, "w") as f:
    #         #     json.dump(data_to_save, f, indent=4)
    #         # print(data_to_save)
    #         # return data_to_save 
        
    #     except Exception as e:
    #         print(e)
    #         return None

    # def triggerDownload(self):
    #     self.downloadingThread.addTask()
    
    # @lockWrapper
    # def read(self, path:str, file:str) -> int:
    #     '''
    #     download the file from dropbox
    #     '''
    #     try:
    #         self.dbx.download(path, file)
    #         return 0
    #     except Exception as e:
    #         print(e)
    #         return -1

    # @lockWrapper
    # def downloadAll(self) -> int:
    #     '''
    #     download all the files in the dropbox
    #     '''
    #     self.downloadingThread.addTask()

    # @lockWrapper
    # def clearAll(self) -> int:
    #     '''
    #     clear all the files in the dropbox
    #     '''
    #     for filename in os.listdir(self.rootdir):
    #         file_path = os.path.join(self.rootdir, filename)
    #         try:
    #             if os.path.isfile(file_path):
    #                 os.remove(file_path)
    #             elif os.path.islink(file_path):
    #                 os.unlink(file_path)
    #             elif os.path.isdir(file_path):
    #                 shutil.rmtree(file_path)
    #         except Exception as e:
    #             print(e)
    #             return -1
    #     return 0
    
WORKING_DIR = "/home/yl910/SmartSync-Linux/"
if __name__ == "__main__":
    # print("Hello World")
    # if len(sys.argv) != 2:
    #     print("Usage: {} <token>".format(sys.argv[0]))
    #     sys.exit(1)

    # TOKEN = sys.argv[1]
    TOKEN = ""
    db = DropboxInterface(TOKEN)
    model = DropBoxModel(db, WORKING_DIR, WORKING_DIR)
    rv = model.fetchDirMeta("/test_webhook")
    print(rv)
    one_rv = model.fetchOneMeta("/test_webhook/lyt.txt")
    print(one_rv)
    test = None
    if test:
        print("True")
    # rootdir = os.path.join(WORKING_DIR, "cache")
    # swapdir = os.path.join(WORKING_DIR, "swap")
    # model = DropBoxModel(db, rootdir, swapdir)
    # model.clearAll()
    # model.saveMetadataToFile()
    # # logging.basicConfig(filename='dropbox.log', level=logging.DEBUG)
    # fuse = FUSE(
    #     FuseDropBox(rootdir, model),
    #     os.path.join(WORKING_DIR, "dropbox"),
    #     foreground=True,
    #     allow_other=True,
    # )