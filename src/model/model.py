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
import dropbox
from functools import wraps
from loguru import logger
import json


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

    def triggerDownload(self):
        self.downloadingThread.addTask()
    
    @lockWrapper
    def read(self, path:str, file:str) -> int:
        '''
        download the file from dropbox
        '''
        try:
            self.dbx.download(path, file)
            return 0
        except Exception as e:
            print(e)
            return -1
    
    @lockWrapper
    def write(self, path:str) -> int:
        '''
        upload the file to dropbox
        '''
        if len(path) == 0 or path[0] != "/":
            path = "/" + path
        try:

            self.synchronizeThread.addTask(self.rootdir+path, path)
            return 0
        except Exception as e:
            print(e)
            return -1
        
    def listFolder(self, path:str) -> dict:
        '''
        list the folder in the dropbox
        '''
        try:
            return self.dbx.list_folder(path)
        except Exception as e:
            print(e)
            return None
        
    @lockWrapper
    def getmetadata(self, path:str) -> dict:
        '''
        get the metadata of the file
        '''
        try:
            return self.dbx.getmetadata(path)
        except Exception as e:
            print(e)
            return None
        
    @lockWrapper
    def downloadAll(self) -> int:
        '''
        download all the files in the dropbox
        '''
        self.downloadingThread.addTask()

    @lockWrapper
    def clearAll(self) -> int:
        '''
        clear all the files in the dropbox
        '''
        for filename in os.listdir(self.rootdir):
            file_path = os.path.join(self.rootdir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(e)
                return -1
        return 0

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
        self.dbx.download(path, local_path)
        
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

    @lockWrapper
    def saveMetadataToFile(self):
        """
        List all files and folders in the Dropbox and save their metadata to a file in JSON format.
        """
        data_to_save = {}
        metadata_file_path = '/tmp/dropbox/metadata.json'
        try:
            files,_ = self.dbx.list_folder("", recursive=True)
            
            for k, v in files.items():
                if isinstance(v,dropbox.files.FileMetadata):
                    mtime = max(v.client_modified, v.server_modified).isoformat()
                    data_to_save[v.path_display] = {
                    "name": v.name,
                    "size": v.size,
                    "type": "file",
                    "mtime": mtime,
                    "uploaded": True
                    }
                elif isinstance(v, dropbox.files.FolderMetadata):
                    data_to_save[v.path_display] = {
                    "name": v.name,
                    "size": None, 
                    "type": "folder",
                    "mtime": None,
                    "uploaded": True
                    }
            
            with open(metadata_file_path, "w") as f:
                json.dump(data_to_save, f, indent=4)

            # print(data_to_save)
            
            return data_to_save 
        
        except Exception as e:
            
            print(e)
            return {}
            

    def initialize_placeholders(self, path):
        try:
            with open(path, 'r') as f:
                metadata = json.load(f)
        except FileNotFoundError:
            print("Metadata file not found, attempting to download...")
        
        for item in metadata:
            if item["type"] == "folder":
                dir_path = os.path.join(self.rootdir, item["path_display"].lstrip('/'))
                # print("dir_path ", dir_path)
                os.makedirs(dir_path, exist_ok=True)
              


WORKING_DIR = "/home/yl910/SmartSync-Linux/"
if __name__ == "__main__":
    print("Hello World")
    if len(sys.argv) != 2:
        print("Usage: {} <token>".format(sys.argv[0]))
        sys.exit(1)

    TOKEN = sys.argv[1]
    db = DropboxInterface(TOKEN)
    rootdir = os.path.join(WORKING_DIR, "cache")
    swapdir = os.path.join(WORKING_DIR, "swap")
    model = DropBoxModel(db, rootdir, swapdir)
    model.clearAll()
    model.saveMetadataToFile()
    # logging.basicConfig(filename='dropbox.log', level=logging.DEBUG)
    fuse = FUSE(
        FuseDropBox(rootdir, model),
        os.path.join(WORKING_DIR, "dropbox"),
        foreground=True,
        allow_other=True,
    )