from datetime import datetime
import threading
import time
from loguru import logger
from data import DropboxInterface
import dropbox
import queue
import os
from utils import FilePath, FileInfo


class DownloadingThread():
    """
    This class represents a downloading thread that is responsible for downloading files from Dropbox and updating the local files.

    Attributes:
        syncMap (dict): A dictionary that stores the synchronization map of file paths and timestamps.
        eventQueue (Queue): A queue used to manage the download events.
        _stop (bool): A flag indicating whether the thread should stop.
        dbx (interface): An interface object for Dropbox API.
        tmpDir (str): The temporary directory path.
        rootDir (str): The root directory path.
        filepath (FilePath): An object representing the file paths.
        mutex (Lock): A lock used for thread synchronization.
    """

    def __init__(self, interface, tmpDir, rootDir) -> None:
        self.syncMap = {}
        self.eventQueue = queue.Queue()
        self.stop_ = False
        self.dbx = interface
        self.tmpDir = os.path.abspath(tmpDir)
        self.rootDir = os.path.abspath(rootDir)
        self.filepath = FilePath(self.rootDir, self.tmpDir)
        self.mutex = threading.Lock()

    def __call__(self):
        '''
        sdownload loop
        '''
        while True:
            self.mutex.acquire()
            if self.stop_:
                self.mutex.release()
                break
            self.mutex.release()

            self.eventQueue.get(block=True)
            logger.info("Downloading files from Dropbox")
            print("downloading triggered")
            metadata = self.getFileMetadata()
            dList = self.getDownLoadList(metadata)
            for path in dList:
                localPath = self.filepath.getLocalPath(path)
                os.makedirs(os.path.dirname(localPath), exist_ok=True)
                self.downloadFile(path)
            self.refreshRootDir(metadata)
            

    def stop(self):
        '''
        stop the thread
        '''
        self.mutex.acquire()
        self.stop_ = True
        self.mutex.release()

    
    def refreshRootDir(self, metadata):
        """
        Moves all files and directories from src to dest using an atomic operation.

        Parameters:
        - metadata: Metadata dictionary used to update the synchronization map after moving files.
        """
        src = self.tmpDir
        dest = self.rootDir
        if not os.path.isdir(src):
            raise ValueError(f"Source is not a directory: {src}")
        if not os.path.isdir(dest):
            os.makedirs(dest)

        for root, dirs, files in os.walk(src):
            # Calculate the current directory's relative path to the source directory
            rel_path = os.path.relpath(root, src)
            dest_path = os.path.join(dest, rel_path)

            # Create corresponding directory structure in the destination for each subdirectory
            for d in dirs:
                os.makedirs(os.path.join(dest_path, d), exist_ok=True)

            # Move each file to the destination directory
            for file in files:
                src_file_path = os.path.join(root, file)
                dest_file_path = os.path.join(dest_path, file)
                os.rename(src_file_path, dest_file_path)
                # Update the sync map
                keypath = self.filepath.getRemotePath(os.path.relpath(dest_file_path, dest))
                self.updateSyncMap(keypath, metadata[keypath].timestamp)

            # Cleanup: Remove the empty source directory after moving files
            if rel_path != '.':
                try:
                    os.removedirs(root)
                except OSError:
                    # list of files is not empty
                    logger.error(f"Files Not Empty: {os.listdir(root)}")
                    logger.error(f"Failed to remove directory: {root}")


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
        print(f"Downloading file {path}")
        try:
            os.makedirs(os.path.dirname(self.filepath.getTmpPath(path)), exist_ok=True)
            self.dbx.download(path, self.filepath.getTmpPath(path))
        except Exception as e:
            logger.error(f"Error downloading file {path}: {e}")
            return -1
        return 0

    def getDownLoadList(self, metadata:dict):
        '''
        get the list of files to download
        '''
        localTimes = self.retrieveLocalMTime()
        dlist = self.retrieveDownloadList(metadata, localTimes)
        return dlist

    def retrieveLocalMTime(self):
        '''
        retrieve the local modified time
        '''
        ans = {}
        for root, dirs, files in os.walk(self.rootDir):
            for file in files:
                path = os.path.join(root, file)
                keypath = os.path.relpath(path, self.rootDir)
                ans[self.filepath.getRemotePath(keypath)] = os.path.getmtime(path)
        return ans
    
    def retrieveDownloadList(self, metadata:dict, localFiles:dict):
        '''
        retrieve the list of files to download
        '''
        dList = []
        for k, v in metadata.items():
            if k not in localFiles:
                # download the file
                dList.append(k)
            else:
                if datetime.timestamp(v.timestamp) > localFiles[k]:
                    # download the file
                    dList.append(k)

        return dList

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
        if not all(hasattr(fileResponse,attr) for attr in ["path_display", "server_modified", "size", "content_hash", "rev"]):
            return False
        if (any([fileResponse.path_display is None, fileResponse.server_modified is None, fileResponse.size is None, fileResponse.content_hash is None, fileResponse.rev is None])):
            return False
        return True
        
                



if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: {} <token>".format(sys.argv[0]))
        sys.exit(1)
    TOKEN = sys.argv[1]
    interface = DropboxInterface(TOKEN)
    dt = DownloadingThread(interface, "./mntdir", "./rootdir")
    dt.addTask()
    dt()
    # os.makedirs("/home/qf37/ece566/finalproj/SmartSync-Linux/mntdir/FUSE-TEST/d.txt", exist_ok=True)
    # metadata = {
    # "/hi.txt": FileInfo("/hi.txt", time.time(), 123, "hash1", "rev1"),
    # "/dir/another": FileInfo("/dir/another", 0, 123, "hash2", "rev2"),
    # }
    # download_list = dt.retrieveDownloadList(metadata)
    # print(download_list)
    # for root, dirs, files in os.walk("/home/qf37/ece566/finalproj/SmartSync-Linux/rootdir"):
        # print(root, dirs, files)
        # for file in files:
        #     path = os.path.join(root, file)
        #     print(path)
        #     interface.upload(path, path)