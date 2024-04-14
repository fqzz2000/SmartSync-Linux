#!/bin/python3
# the fuse interaction layer
import random
from src.lib import FUSE, LoggingMixIn, Operations, FuseOSError
from src.data.data import DropboxInterface
import logging
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
import errno
from collections import defaultdict
import os
from loguru import logger
import json
import time
from datetime import datetime


class FuseDropBox(LoggingMixIn, Operations):
    "Example memory filesystem. Supports only one level of files."

    def __init__(self, rootdir, dbmodel):
        self.rootdir = rootdir
#        print("ROOTDIR IS", rootdir)
        self.db = dbmodel
        logger.remove()
        logger.add("/tmp/dropbox/dropbox.log", level="INFO")
        self.metadata = {}
        self.metadata_file_path = '/tmp/dropbox/metadata.json'
        if os.path.exists(self.metadata_file_path):
            with open(self.metadata_file_path, 'r') as f:
                try:
                    self.metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading metadata from file: {e}")
        for k, v in self.metadata.items():
            v['uploaded'] = True
        
    def chmod(self, path, mode):
        logger.info(f"CHMOD CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        return os.chmod(path, mode)

    def chown(self, path, uid, gid):
        logger.info(f"CHOWN CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.chown(path, uid, gid)

    def create(self, path, mode):
        logger.info(f"CREATE CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        file_name = os.path.basename(path)
        new_file_metadata = {
            "name": file_name, 
            "size": 0,
            "type": "file",
            "mtime": time.time(),
            "uploaded": False
            }
        self.metadata[path] = new_file_metadata
        # print(f"create, current metatdata {self.metadata}")
        if path[0] == "/":
            path = path[1:]
        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        return os.open(local_path, os.O_CREAT | os.O_WRONLY, mode)
            
    def getattr(self, path, fh=None):
        logger.info(f"GETATTR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
    
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

        # remote_metadata = self.db.saveMetadataToFile()
        # db_v = remote_metadata.get(path)
        remote_metadata = self.db.fetchOneMetadata(path)
        remote_metadata = remote_metadata.get(path) if remote_metadata is not None else None

        if path in self.metadata:
            local_v = self.metadata[path]
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

    def getxattr(self, path, name, position=0):
        logger.info(f"GETXATTR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        ret = b'default'
        if path[0] == "/":
            path = path[1:]
        try:
            local_path = os.path.join(self.rootdir, path)
            if not os.path.exists(local_path):
                return ret
            else:
                ret = os.getxattr(local_path, name)
                return ret
            
        except FileNotFoundError:
            raise FuseOSError(errno.ENOENT)
            # find the file in the dropbox
            # if len(path) == 0 or path[0] != "/":
            #     path = "/" + path
            # print("PATH IS", path)
            # metadata = self.db.getmetadata(path)
            # if isinstance(metadata, dict):
            #     # TODO: solve the problem caused by getting started iwth dropbox paper.paper
            #     return metadata.get(name, bytes(""))

    def listxattr(self, path):
        logger.info(f"LISTXATTR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.listxattr(path)

    def mkdir(self, path, mode):
        logger.info(f"MKDIR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        
        dir_name = os.path.basename(path)
        new_file_metadata = {
            "name": dir_name, 
            "size": 0,
            "type": "folder"}
        self.metadata[path] = new_file_metadata
        print(self.metadata)
        if path[0] == "/":
            path = path[1:]
        self.db.createFolder(path, mode)

    def open(self, path, flags):
        logger.info(f"OPEN CALLED WITH ID {random.randint(0, 100)}, path: {path}")

        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        # metadata_from_db = self.db.saveMetadataToFile()

        try: 
            remote_metadata = self.db.fetchOneMetadata(path)
            remote_metadata = remote_metadata.get(path) if remote_metadata is not None else None
            if remote_metadata is None:
                raise FuseOSError(errno.ENOENT)
            if not os.path.exists(local_path):
                self.db.open_file(path, local_path) # trigger download
                self.metadata[path] = remote_metadata
                self.db.flushMetadataAsync(self.metadata)
                # self.metadata[path] = metadata_from_db[path]
            else:
                local_v = self.metadata[path]
                if local_v["uploaded"]:
                    # db_v = metadata_from_db.get(path)
                    # if db_v is None:
                    #     raise FuseOSError(errno.ENOENT)
                    lct = datetime.fromisoformat(local_v["mtime"])
                    rmt = datetime.fromisoformat(remote_metadata["mtime"])
                    if rmt > lct:
                        # self.metadata[path] = metadata_from_db[path]
                        # self.metadata[path] = remote_metadata
                        self.db.open_file(path, local_path)
                        self.metadata[path] = remote_metadata
                        self.db.flushMetadataAsync(self.metadata)
        except (FileNotFoundError, dropbox.files.DownloadError) as e:
            logger.error(f"Error opening file: {e}")
            raise FuseOSError(errno.ENOENT)
        # print(self.metadata)
        return os.open(local_path, flags)
    
    def read(self, path, size, offset, fh):
        # id = random.randint(0, 100)
        # logger.info(f"READ CALLED, path: {path}")
        # logger.debug(f"STARTING READ WITH ID {id}")
        
        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        with open(local_path, 'rb') as f:
            f.seek(offset)
            return f.read(size)

    def readdir(self, path, fh):
        logger.info(f"READDIR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        # remote_metadata = self.db.saveMetadataToFile()
        remote_metadata = self.db.fetchDirMetadata(path)

        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        if not os.path.exists(local_path):
            os.makedirs(local_path, exist_ok=True)
        
        direntries = ['.', '..']
        for local_key in list(self.metadata.keys()):
            if not self.metadata[local_key]["uploaded"]: # False if file hasn't been uploaded
                m_name = self.metadata[local_key]["name"]
                direntries.append(m_name)
        if remote_metadata is not None:
            for m_path in remote_metadata.keys():
                # if os.path.dirname(m_path.lstrip('/')) == path.lstrip('/'):
                m_name = remote_metadata[m_path]["name"]
                if m_name not in direntries:
                    direntries.append(m_name)
        return direntries

    def readlink(self, path):
        logger.info(f"READLINK CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        return os.readlink(path)

    def removexattr(self, path, name):
        logger.info(f"REMOVEXATTR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.removexattr(path, name)

    def rename(self, old, new):
        logger.info(f"RENAME CALLED WITH ID {random.randint(0, 100)}, path: {path}")

        self.db.move(old.lstrip('/'), new.lstrip('/'))
        local_path = os.path.join(self.rootdir, new.lstrip('/'))
        # print("loca: ", local_path)
        if old in self.metadata:
            m_type = self.metadata[old]["type"]
            self.metadata[new] = self.metadata.pop(old)
            self.metadata[new]["name"] = os.path.basename(local_path)
            
            if m_type == "folder":
                old_prefix = old + '/'
                new_prefix = new + '/'
                keys_to_update = [k for k in self.metadata.keys() if k.startswith(old_prefix)]
                for key in keys_to_update:
                    new_key = new_prefix + key[len(old_prefix):]
                    self.metadata[new_key] = self.metadata.pop(key)

    def rmdir(self, path):
        logger.info(f"RMDIR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        # with multiple level support, need to raise ENOTEMPTY if contains any files
        if path[0] == "/":
            path = path[1:]
        self.db.deleteFolder(path)

    def setxattr(self, path, name, value, options, position=0):
        logger.info(f"SETXATTR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.setxattr(path, name, value, options)

    def statfs(self, path):
        logger.info(f"STATFS CALLED WITH ID {random.randint(0, 100)}, path: {path}")

        total_space, used_space = self.db.getSpaceUsage()
        free_space = total_space - used_space
        block_size = 512
        total_blocks = total_space // block_size
        free_blocks = free_space // block_size
        return {
            'f_bsize': block_size,
            'f_blocks': total_blocks,
            'f_bfree': free_blocks,
            'f_bavail': free_blocks,
            'f_files': 0, 
            'f_ffree': 0,
        }

    def symlink(self, target, source):
        logger.info(f"SYMLINK CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        # os.close(os.open(target, os.O_CREAT))
        if target[0] == "/":
            target = target[1:]
        target = os.path.join(self.rootdir, target)
        if source[0] == "/":
            source = source[1:]
        source = os.path.join(self.rootdir, source)
        os.symlink(source, target)

    def truncate(self, path, length, fh=None):
        logger.info(f"TRUNCATE CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        # make sure extending the file fills in zero bytes
        new_path = path
        if new_path[0] == "/":
            new_path = new_path[1:]
        new_path = os.path.join(self.rootdir, new_path)
        os.truncate(new_path, length)
        new_size = os.path.getsize(new_path)
        logger.warning(f"GOING TO UPLOAD {path}")
        self.metadata[path]["uploaded"] = False
        self.metadata[path]["size"] = new_size
        self.metadata[path]["mtime"] = time.time()
        self.db.write(path, lambda path: self.update_metadata(path))
        logger.warning(f"TRUNCATE DONE ADD UPLOAD TASK")

    def unlink(self, path):
        logger.info(f"UNLINK CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if path[0] == "/":
            path = path[1:]
        self.db.deleteFile(path)

    def utimens(self, path, times=None):
        logger.info(f"UTIMENS CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if path[0] == "/":
            path = path[1:]
        os.utime(path, times)

    def write(self, path, data, offset, fh):
        id = random.randint(0, 100)
        # logger.info(f"WRITE CALLED WITH ID {id}")
        ret = os.pwrite(fh, data, offset)
        local_path = os.path.join(self.rootdir, path)
        new_size = offset + ret
        self.metadata[path]["uploaded"] = False
        self.metadata[path]["size"] = new_size
        self.metadata[path]["mtime"] = time.time()
        self.db.write(path, lambda path: self.update_metadata(path))
        #TODO
        #upload and change uploaded to True
        # self.db.upload(local_path,path, new_size)
        # logger.warning(f"WRITE DONE ADD UPLOAD TASK")
        return ret
    

    def release(self, path, fh):
        logger.info(f"RELEASE CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        os.close(fh)
        return 0

    def update_metadata(path):
        self.metadata[path]["uploaded"] = True

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("mountdir")
    parser.add_argument("rootdir")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    fuse = FUSE(
        FuseDropBox(args.rootdir), args.mountdir, foreground=True, allow_other=True
    )
