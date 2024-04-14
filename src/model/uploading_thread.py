import sys
import time
from loguru import logger
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
            # logger.warning("Synchronization Tiggered")
            self.synchronize()

    def synchronize(self):
        '''
        synchronize all the files in the queue 
        if the time is greater than the max synchronization interval, then upload all the files in the queue
        otherwise, only upload the files that are older than the synchronization interval
        '''
        maxSync = time.time() - self.lastMaxSyncTime > self.maxSynInterval
        if maxSync:
            # logger.warning("Max synchronization interval reached, uploading all files")
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

        # logger.warning(f"Uploading {len(self.uploadingQueue)} files")
        while len(self.uploadingQueue) > 0:
            path, file = self.uploadingQueue.pop()
            logger.warning(f"Uploading {path} {file}")
            try:
                self.dbx.upload(path, file, True)
                self.mutex.acquire()
                self.dbx.metadata[path].uploaded = True
                self.mutex.release()
            except Exception as e:
                # print to stderr
                print(e, file=sys.stderr)
                self.mutex.acquire()
                self.dbx.metadata[path].uploaded = False
                self.mutex.release()
                return 
            # logger.warning(f"Upload {path} {file} done")


    def stop(self):
        self._stop = True
    
    def addTask(self, path:str, file:str):
        '''
        search the queue, if the file is already in the queue, update the timestamp
        otherwise, add the file to the queue
        '''
        # logger.warning(f"Task Added {path} {file}")
        self.outstandingQueue[(path, file)] = time.time()
        # change the uploaded metadata to false
        self.dbx.metadata[path].uploaded = False