import time
from loguru import logger
from data import DropboxInterface
import dropbox
import queue
import os

class FileInfo():
    def __init__(self, path, timestamp, size, hash, rev) -> None:
        self.path = path
        self.timestamp = timestamp
        self.size = size
        self.hash = hash
        self.rev = rev
    def __repr__(self) -> str:
        return f"FileInfo(path={self.path}, timestamp={self.timestamp}, size={self.size}, hash={self.hash}, rev={self.rev})\n"

class DownloadingThread():

    def __init__(self, interface, tmpDir, rootDir) -> None:
        self.syncMap = {}
        self.eventQueue = queue.Queue()
        self._stop = False
        self.dbx = interface
        self.tmpDir = tmpDir
        self.rootDir = rootDir
    

    def __call__(self):
        '''
        sdownload loop
        '''
        while not self._stop:
            self.eventQueue.get(block=True)
            dList = self.getDownLoadList()
            for path in dList:
                os.makedirs(os.dirname(self.getLocalPath(path)), exist_ok=True)
                self.downloadFile(path)
        
    def addTask(self):
        '''
        add the task to the sync map
        '''
        self.eventQueue.put(True)

    def updateSyncMap(self, path, timestamp):
        '''
        update the sync map with the path and timestamp
        '''
        self.syncMap[path] = timestamp

    def downloadFile(self, path):
        '''
        download the file from dropbox
        '''
        logger.info(f"Downloading file {path}")
        try:
            self.dbx.download(path, self.getLocalPath(path))
        except Exception as e:
            logger.error(f"Error downloading file {path}: {e}")
            return -1
        return 0
    
    
    def getLocalPath(self, path):
        '''
        translate the path to the local path
        '''
        return path.replace("/", self.tmpDir)


    def getDownLoadList(self):
        '''
        get the list of files to download
        '''
        metadata = self.getFileMetadata()
        dlist = self.retrieveDownloadList(metadata)
    
    def retrieveDownloadList(self, metadata:dict):
        '''
        retrieve the list of files to download
        '''
        dList = []
        for k, v in self.syncMap.items():
            if k not in metadata:
                # download the file
                dList.append(k)
            else:
                if v > metadata[k].timestamp:
                    # download the file
                    dList.append(k)

        return dList
       
        # compare the files with the local files
    def getFileMetadata(self)->dict:
        '''
        get the metadata of the file
        '''
        ans = {}
        # get the list of files from dropbox
        files = self.dbx.list_folder("", recursive=True)
        for k,v in files.items():
            if isinstance(v, dropbox.files.FileMetadata):
                if not self.verifyFileResponse(v):
                    logger.error(f"Invalid file response from server: {v}")
                    continue
                ans[v.path_display] = FileInfo(v.path_display, v.server_modified, v.size, v.content_hash, v.rev)
            elif isinstance(v, dropbox.files.FolderMetadata):
                pass
        return ans

    def verifyFileResponse(self, fileResponse:dropbox.files.FileMetadata) -> bool:
        '''
        verify the file response
        '''
        return all(hasattr(fileResponse,attr) for attr in ["path_display", "server_modified", "size", "content_hash", "rev"])
        
                



if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: {} <token>".format(sys.argv[0]))
        sys.exit(1)
    TOKEN = sys.argv[1]
    interface = DropboxInterface(TOKEN)
    # dt = DownloadingThread(interface, "./mntdir", "./rootdir")
    # os.makedirs("/home/qf37/ece566/finalproj/SmartSync-Linux/mntdir/FUSE-TEST/d.txt", exist_ok=True)

