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
from datetime import datetime
from stat import S_IFDIR, S_IFREG
import errno


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
        self.full_metadata = self.fetchAllMetadata()
        self.local_metadata = {}
        self.local_metadata_file_path = '/tmp/dropbox/metadata.json'
        if os.path.exists(self.local_metadata_file_path):
            with open(self.local_metadata_file_path, 'r') as f:
                try:
                    self.local_metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading metadata from file: {e}")
        for k, v in self.local_metadata.items():
            v['uploaded'] = True
        print("Model initialized")

    def stop(self):
        self.synchronizeThread.stop()
        self.downloadingThread.stop()
        self.thread.join()

    @lockWrapper
    def updateFullMetadata(self):
        self.full_metadata = self.fetchAllMetadata()

    def fetchAllMetadata(self):
        """
        List all files and folders in the Dropbox and save their metadata to a file in JSON format.
        """
        try:
            files,_ = self.dbx.list_folder("", recursive=True)
            return self.formatMetadata(files)
        except Exception as e:
            print(e)
            return None
        
    def fetchOneMetadata(self, path:str) -> dict:
        '''
        get the metadata of the file
        '''
        try:
            file = {path: self.dbx.getmetadata(path)}
            return self.formatMetadata(file)
        except Exception as e:
            logger.error(e)
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
            logger.error(e)
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
        logger.warning(f"Ready to flush, metadata: {metadata}")
        with open(self.local_metadata_file_path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                logger.warning(f"Flushing metadata to file, metadata: {metadata}")
                self.mutex.acquire()
                json.dump(metadata, f, indent=4)
                self.mutex.release()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def flushMetadataAsync(self, metadata:dict):
        '''
        flush the metadata to the file asynchronously
        '''
        flushThread = threading.Thread(target=self.flushMetadata, args=(metadata,))
        flushThread.start()

    @lockWrapper
    def getattr(self, path:str):
        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        now = time.time()
        default_attrs = {
            'st_atime': now,
            'st_ctime': now,
            'st_mtime': now,
            'st_gid': os.getgid(),
            'st_uid': os.getuid(),
        }
        if path == "/":
            return {'st_mode': (S_IFDIR | 0o755), **default_attrs}
        remote_metadata = self.fetchOneMetadata(path)
        remote_metadata = remote_metadata.get(path) if remote_metadata is not None else None
        if path in self.local_metadata:
            local_v = self.local_metadata[path]
            ret = os.stat(local_path) if os.path.exists(local_path) else default_attrs

            if not local_v['uploaded']:
                return {
                    "st_atime": ret.st_atime,
                    "st_ctime": ret.st_ctime,
                    "st_gid": ret.st_gid,
                    "st_mode": ret.st_mode,
                    "st_mtime": ret.st_mtime,
                    "st_nlink": ret.st_nlink,
                    "st_size": ret.st_size,
                    "st_uid": ret.st_uid,
                }
            elif remote_metadata and remote_metadata.get("type") == "file":
                lct = datetime.fromisoformat(local_v["mtime"])
                rmt = datetime.fromisoformat(remote_metadata["mtime"])
                if lct > rmt:
                    return {
                        **ret,
                        "st_mtime": lct.timestamp(),  # Assume lct is datetime object
                    }
                else:
                    return {
                        **default_attrs,
                        "st_mtime": rmt.timestamp(),  # Assume rmt is datetime object
                        "st_size": remote_metadata['size'],
                        'st_mode': (S_IFREG | 0o644),
                    }
        if remote_metadata is not None:
            return {
                **default_attrs,
                "st_mtime": int(now) if remote_metadata['type'] == 'folder' else int(datetime.fromisoformat(remote_metadata["mtime"]).timestamp()),
                'st_mode': (S_IFDIR | 0o755) if remote_metadata["type"] == "folder" else (S_IFREG | 0o644),
                'st_nlink': 2 if remote_metadata["type"] == "folder" else 1,
                'st_size': remote_metadata['size'] if remote_metadata['size'] is not None else 0,
            }
        raise OSError(errno.ENOENT, "No such file or directory")    
    
    @lockWrapper
    def readdir(self, path:str):
        remote_metadata = self.fetchDirMetadata(path)

        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        if not os.path.exists(local_path):
            os.makedirs(local_path, exist_ok=True)
        
        direntries = ['.', '..']
        for local_key in list(self.local_metadata.keys()):
            if not self.local_metadata[local_key]["uploaded"]: # False if file hasn't been uploaded
                m_name = self.local_metadata[local_key]["name"]
                direntries.append(m_name)
        if remote_metadata is not None:
            for m_path in remote_metadata.keys():
                # if os.path.dirname(m_path.lstrip('/')) == path.lstrip('/'):
                m_name = remote_metadata[m_path]["name"]
                if m_name not in direntries:
                    direntries.append(m_name)
        return direntries

    @lockWrapper
    def write(self, path:str, new_size) -> int:
        '''
        upload the file to dropbox
        '''
        # self.metadata[path]["uploaded"] = False
        self.local_metadata[path]["size"] = new_size
        self.local_metadata[path]["mtime"] = time.time()
        if len(path) == 0 or path[0] != "/":
            path = "/" + path
        try:
            self.synchronizeThread.addTask(self.rootdir+path, path)
            return 0
        except Exception as e:
            logger.error(e)
            return -1

    @lockWrapper
    def createFolder(self, path:str, mode) -> int:
        '''
        create a folder in the dropbox
        '''
        # create remotely
        self.dbx.mkdir("/" + path)
        # create locally
        new_path = os.path.join(self.rootdir, path)
        os.mkdir(new_path, mode)
        dir_name = os.path.basename("/" + path)
        new_file_metadata = {
            "name": dir_name, 
            "size": 0,
            "type": "folder",
            "mtime": None,
            "uploaded": True
        }
        self.local_metadata["/" + path] = new_file_metadata
        self.flushMetadataAsync(self.local_metadata)
        return 0
    
    @lockWrapper
    def createFile(self, path:str, mode) -> int:
        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        ret = os.open(local_path, os.O_CREAT | os.O_WRONLY, mode)
        file_name = os.path.basename(path)
        new_file_metadata = {
            "name": file_name, 
            "size": 0,
            "type": "file",
            "mtime": time.time(),
            "uploaded": False
            }
        self.local_metadata[path] = new_file_metadata
        self.flushMetadataAsync(self.local_metadata)
        # print(f"create, current metatdata {self.metadata}")
        return ret
    
    @lockWrapper
    def deleteFolder(self, path:str) -> int:
        '''
        delete a file in the dropbox
        '''
        # remove remotely
        try:
            self.dbx.delete("/" + path)
        except Exception as e:
            logger.error(e)
            return -1
        # remove locally
        new_path = os.path.join(self.rootdir, path)
        if os.path.exists(new_path):
            try:
                os.rmdir(new_path)
            except Exception as e:
                logger.error(e)
                return -1
            # update metadata
            keys_to_delete = [k for k in self.local_metadata.keys() if k.startswith("/" + path)]
            for key in keys_to_delete:
                self.local_metadata.pop(key)
            self.flushMetadataAsync(self.local_metadata)
        return 0
        
    @lockWrapper
    def deleteFile(self, path:str) -> int:
        '''
        delete a file in the dropbox
        '''
        # remove remotely
        try:
            self.dbx.delete("/" + path)
        except Exception as e:
            logger.error(e)
            return -1
        # remove locally
        new_path = os.path.join(self.rootdir, path)
        if os.path.exists(new_path):
            try:
                os.unlink(new_path)
            except Exception as e:
                logger.error(e)
                return -1
            # update metadata
            if path in self.local_metadata:
                self.local_metadata.pop("/" + path)
            self.flushMetadataAsync(self.local_metadata)
        return 0

    @lockWrapper
    def open_file(self, path, local_path, flags):
        try: 
            remote_metadata = self.fetchOneMetadata(path)
            remote_metadata = remote_metadata.get(path) if remote_metadata is not None else None
            if remote_metadata is None:
                return -1
            if not os.path.exists(local_path):
                self.download_file(path, local_path) # trigger download
                self.local_metadata[path] = remote_metadata
                self.flushMetadataAsync(self.local_metadata)
                # self.metadata[path] = metadata_from_db[path]
            else:
                local_v = self.local_metadata[path]
                if local_v["uploaded"]:
                    # db_v = metadata_from_db.get(path)
                    # if db_v is None:
                    #     raise FuseOSError(errno.ENOENT)
                    lct = datetime.fromisoformat(local_v["mtime"])
                    rmt = datetime.fromisoformat(remote_metadata["mtime"])
                    if rmt > lct:
                        # self.metadata[path] = metadata_from_db[path]
                        # self.metadata[path] = remote_metadata
                        self.open_file(path, local_path)
                        self.local_metadata[path] = remote_metadata
                        self.flushMetadataAsync(self.local_metadata)
        except FileNotFoundError as e:
            logger.error(f"Error opening file: {e}")
            return -1
        except Exception as e:
            logger.error(f"Error opening file: {e}")
            return -1
        return os.open(local_path, flags)

    @lockWrapper
    def download_file(self, path, local_path):
        lockfile_path = f"{local_path}.lock"
        with open(lockfile_path, 'w') as lockfile:
            try:
                fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB) # throw an exception if the file is locked
                self.dbx.download(path, local_path)
            except BlockingIOError:
                fcntl.flock(lockfile, fcntl.LOCK_EX) # blocked until the file is unlocked
            finally:
                if os.path.exists(lockfile_path):
                    os.remove(lockfile_path)
        
    @lockWrapper
    def move(self, old:str, new:str) -> int:
        '''
        rename a file in the dropbox
        '''
        # remote move
        try:
            self.dbx.move("/" + old, "/" + new)
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return -1
        # local move
        old_path = os.path.join(self.rootdir, old)
        new_path = os.path.join(self.rootdir, new)
        if os.path.exists(old_path):
            new_path_dir = os.path.dirname(new_path)
            if not os.path.exists( new_path_dir):
                os.makedirs(new_path_dir)
            try:
                os.rename(old_path, new_path)
            except Exception as e:
                logger.error(f"Error moving file: {e}")
                return -1
            # metadata update
            if old in self.local_metadata:
                m_type = self.local_metadata[old]["type"]
                self.local_metadata[new] = self.metadata.pop("/" + old)
                self.local_metadata[new]["name"] = os.path.basename(new_path)
                self.local_metadata[new]["mtime"] = time.time()
                
                if m_type == "folder":
                    old_prefix = old + '/'
                    new_prefix = new + '/'
                    keys_to_update = [k for k in self.local_metadata.keys() if k.startswith(old_prefix)]
                    for key in keys_to_update:
                        new_key = new_prefix + key[len(old_prefix):]
                        self.local_metadata[new_key] = self.local_metadata.pop(key)
                        self.local_metadata[new_key]["mtime"] = time.time()
            else:
                remote_metadata = self.fetchOneMetadata("/" + new)
                if remote_metadata is not None:
                    self.local_metadata["/" + new] = remote_metadata.get("/" + new)
            self.flushMetadataAsync(self.local_metadata)
        return 0
    
    def getSpaceUsage(self) -> dict:
        '''
        get the space usage of the dropbox
        '''
        try:
            return self.dbx.users_get_space_usage()
        except Exception as e:
            logger.error(e)
            return None

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