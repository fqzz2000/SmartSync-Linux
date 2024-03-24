# commandline interface for the program
import threading
from data import DropboxInterface
from lib import FUSE
import os
import shutil
from functools import wraps


class DropBoxModel():
    def __init__(self, interface, rootdir) -> None:
        self.dbx = interface
        self.rootdir = rootdir
        self.mutex = threading.Lock()

    def __del__(self):
        pass 

    @classmethod
    def lockWrapper(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.mutex.acquire()
            ret = func(self, *args, **kwargs)
            self.mutex.release()
            return ret
        return wrapper
    
    @lockWrapper
    def synchroneous(self, func):
        '''
        syncrhonize current data with dropbox
        milestone 1: only upload the file to dropbox
        '''

        pass
    
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
            self.dbx.upload(self.rootdir + path, path, True)
            return 0
        except Exception as e:
            print(e)
            return -1
        
    @lockWrapper
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
        try:
            dic = self.listFolder("")
            for k, v in dic.items():
                if len(k) == 0 or k[0] != "/":
                    k = "/" + k
                value_type = str(type(v))
                if value_type == "<class 'dropbox.files.FolderMetadata'>":
                    self.dbx.download_folder(k, self.rootdir + k, self.rootdir)
                elif value_type == "<class 'dropbox.files.FileMetadata'>":
                    self.dbx.download(k, self.rootdir + "/" + k)
                else:
                    raise Exception("Unknown type" + value_type)
            return 0
        except Exception as e:
            print(e)
            return -1

    @lockWrapper
    def clearAll(self) -> int:
        '''
        clear all the files in the dropbox
        '''
        print(os.listdir(self.rootdir))
        for filename in os.listdir(self.rootdir):
            print(filename)
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
    


if __name__ == "__main__":
    print("Hello World")