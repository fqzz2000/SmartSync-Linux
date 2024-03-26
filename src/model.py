# commandline interface for the program
from collections import deque
import sys
import threading
import time
from data import DropboxInterface
from lib import FUSE
import os
import shutil
from functools import wraps
from loguru import logger

def lockWrapper(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.mutex.acquire()
        ret = func(self, *args, **kwargs)
        self.mutex.release()
        return ret
    return wrapper


class DropBoxModel():
    class UploadingThread():
        def __init__(self, interface, lock, synchronizeInterval=5, maxSynchronizeInterval=60) -> None:
            self.outstandingQueue = {}
            self.synInterval = synchronizeInterval
            self.maxSynInterval = maxSynchronizeInterval
            self.dbx = interface
            self.lastMaxSyncTime = time.time()
            self._stop = False
            self.mutex = lock
            self.uploadingQueue = []
        
        def __call__(self):
            '''
            synchronization loop
            '''
            while not self._stop:
                time.sleep(self.synInterval)
                logger.warning("Synchronization Tiggered")
                self.synchronize()

        def synchronize(self):
            '''
            synchronize all the files in the queue 
            if the time is greater than the max synchronization interval, then upload all the files in the queue
            otherwise, only upload the files that are older than the synchronization interval
            '''
            maxSync = time.time() - self.lastMaxSyncTime > self.maxSynInterval
            if maxSync:
                logger.warning("Max synchronization interval reached, uploading all files")
                self.lastMaxSyncTime = time.time()
            if len(self.outstandingQueue) > 0:
            
                newQueue = {}
                self.mutex.acquire()
                for k,v in self.outstandingQueue.items():
                    path, file = k
                    timestamp = v
                    if maxSync:
                        self.uploadingQueue.append((path, file))
                    elif time.time() - timestamp > self.synInterval:
                        self.uploadingQueue.append((path, file))
                    else:
                        newQueue[(path, file)] = timestamp
                self.outstandingQueue = newQueue
                self.mutex.release()

            logger.warning(f"Uploading {len(self.uploadingQueue)} files")
            while len(self.uploadingQueue) > 0:
                path, file = self.uploadingQueue.pop()
                logger.warning(f"Uploading {path} {file}")
                try:
                    self.dbx.upload(path, file, True)
                except Exception as e:
                    # print to stderr
                    print(e, file=sys.stderr)
                logger.warning(f"Upload {path} {file} done")


        def stop(self):
            self._stop = True
        
        def addTask(self, path:str, file:str):
            '''
            search the queue, if the file is already in the queue, update the timestamp
            otherwise, add the file to the queue
            '''
            logger.warning(f"Task Added {path} {file}")
            if self.outstandingQueue.get((path, file), None) is not None:
                self.outstandingQueue[(path, file)] = time.time()
            else:
                self.outstandingQueue[(path, file)] = time.time()

    def __init__(self, interface, rootdir) -> None:
        self.dbx = interface
        self.rootdir = rootdir
        self.mutex = threading.Lock()
        self.synchronizeThread = self.UploadingThread(self.dbx, self.mutex)
        self.thread = threading.Thread(target=self.synchronizeThread)
        self.thread.start()
        print("Model initialized")

    def stop(self):
        self.synchronizeThread.stop()
        self.thread.join()
    
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
        

if __name__ == "__main__":
    print("Hello World")
