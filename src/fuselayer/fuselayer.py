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


class FuseDropBox(LoggingMixIn, Operations):
    "Example memory filesystem. Supports only one level of files."

    def __init__(self, rootdir, dbmodel, interface):
        self.rootdir = rootdir
#        print("ROOTDIR IS", rootdir)
        self.db = dbmodel
        logger.remove()
        logger.add("/tmp/dropbox/dropbox.log", level="INFO")
        self.dbx = interface
        self.metadata = []
        self.metadata_file_path = '/tmp/dropbox/metadata.json'

    def chmod(self, path, mode):
        logger.info(f"CHMOD CALLED WITH ID {random.randint(0, 100)}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        return os.chmod(path, mode)

    def chown(self, path, uid, gid):
        logger.info(f"CHOWN CALLED WITH ID {random.randint(0, 100)}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.chown(path, uid, gid)

    def create(self, path, mode):
        logger.info(f"CREATE CALLED WITH ID {random.randint(0, 100)}")
        new_file_metadata = {
            "name": os.path.basename(path),
            "path_lower": path,
            "type": "file",
            "size": 0  
        }
        # print("create path: ", path)
        self.metadata.append(new_file_metadata)
        self.update_metadata_file()
        print(f"create, current metatdata {self.metadata}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        print("PATH IS", path)
        return os.open(path, os.O_CREAT | os.O_WRONLY, mode)

    def update_metadata_file(self):
        with open(self.metadata_file_path, 'w') as f:
            json.dump(self.metadata, f, indent=4)
        print(f"update metadata file, current metatdata {self.metadata}")
            
    def getattr(self, path, fh=None):
        logger.info(f"GETATTR CALLED WITH ID {random.randint(0, 100)}")
        
        # newpath = os.path.join(self.rootdir, path)
        '''
        Executes the lstat call directly on the local filesystem
            if path[0] == "/":
            path = path[1:]
            ret = os.lstat(newpath)
            # print(ret)
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
        '''
        
        now = time.time()
        default_attrs = {
            'st_atime': now,  
            'st_ctime': now,  
            'st_mtime': now,  
            'st_gid': os.getgid(),  
            'st_uid': os.getuid(),  
            'st_nlink': 2 if path == "/" else 1,  
        }
   
        if path == "/":
            attrs = {'st_mode': (S_IFDIR | 0o755), **default_attrs} 
            return attrs

        for item in self.metadata:
            if item["path_lower"] == path:
                if item["type"] == "folder":
                    attrs = {'st_mode': (S_IFDIR | 0o755), **default_attrs}
                else:  # type == "file"
                    attrs = {'st_mode': (S_IFREG | 0o644), 'st_size': item["size"], **default_attrs} 
                return attrs

        # If the path does not exist in the metadata
        raise FuseOSError(errno.ENOENT)
        

    def getxattr(self, path, name, position=0):
        logger.info(f"GETXATTR CALLED WITH ID {random.randint(0, 100)}")
        
        if path[0] == "/":
            path = path[1:]
        try:
            newpath = os.path.join(self.rootdir, path)
            ret = os.getxattr(newpath, name)
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
        logger.info(f"LISTXATTR CALLED WITH ID {random.randint(0, 100)}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.listxattr(path)

    def mkdir(self, path, mode):
        logger.info(f"MKDIR CALLED WITH ID {random.randint(0, 100)}")
        if path[0] == "/":
            path = path[1:]
        self.db.createFolder(path, mode)

    def open(self, path, flags):
        logger.info(f"OPEN CALLED WITH ID {random.randint(0, 100)}")
        # db_path = path
        # if path[0] == "/":
        #     path = path[1:]
        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        if not os.path.exists(local_path):
            
            self.dbx.download(path, local_path)
        
        return os.open(local_path, flags)

    def read(self, path, size, offset, fh):
        id = random.randint(0, 100)
        logger.info(f"READ CALLED WITH ID {id}")
        logger.debug(f"STARTING READ WITH ID {id}")
        
        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        with open(local_path, 'rb') as f:
            f.seek(offset)
            return f.read(size)

    def readdir(self, path, fh):
        logger.info(f"READDIR CALLED WITH ID {random.randint(0, 100)}")
        
        with open(self.metadata_file_path, 'r') as f:
            self.metadata = json.load(f)
        if path[0] == "/":
            path = path[1:]
        newpath = os.path.join(self.rootdir, path)
        direntries = ['.', '..'] + os.listdir(newpath)

        # newpath = os.path.join(self.rootdir, path)
        # return [".", ".."] + os.listdir(newpath)
        # if path == "/":
        #     path = ""
        # rv = self.db.listFolder(path)
        # return ['.', '..'] + list(rv.keys())
        
        for item in self.metadata:
            if item["type"] == "file":
                if os.path.dirname(item["path_lower"].lstrip('/')) == path.lstrip('/'):
                    if item["name"] not in direntries:
                        direntries.append(item["name"])
        return direntries


    def readlink(self, path):
        logger.info(f"READLINK CALLED WITH ID {random.randint(0, 100)}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        return os.readlink(path)

    def removexattr(self, path, name):
        logger.info(f"REMOVEXATTR CALLED WITH ID {random.randint(0, 100)}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.removexattr(path, name)

    def rename(self, old, new):
        logger.info(f"RENAME CALLED WITH ID {random.randint(0, 100)}")
        if old[0] == "/":
            old = old[1:]
        if new[0] == "/":
            new = new[1:]
        self.db.move(old, new)

    def rmdir(self, path):
        logger.info(f"RMDIR CALLED WITH ID {random.randint(0, 100)}")
        # with multiple level support, need to raise ENOTEMPTY if contains any files
        if path[0] == "/":
            path = path[1:]
        self.db.deleteFolder(path)

    def setxattr(self, path, name, value, options, position=0):
        logger.info(f"SETXATTR CALLED WITH ID {random.randint(0, 100)}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.setxattr(path, name, value, options)

    def statfs(self, path):
        logger.info(f"STATFS CALLED WITH ID {random.randint(0, 100)}")

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
        logger.info(f"SYMLINK CALLED WITH ID {random.randint(0, 100)}")
        # os.close(os.open(target, os.O_CREAT))
        if target[0] == "/":
            target = target[1:]
        target = os.path.join(self.rootdir, target)
        if source[0] == "/":
            source = source[1:]
        source = os.path.join(self.rootdir, source)
        os.symlink(source, target)

    def truncate(self, path, length, fh=None):
        logger.info(f"TRUNCATE CALLED WITH ID {random.randint(0, 100)}")
        # make sure extending the file fills in zero bytes
        new_path = path
        if new_path[0] == "/":
            new_path = new_path[1:]
        new_path = os.path.join(self.rootdir, new_path)
        os.truncate(new_path, length)
        logger.warning(f"GOING TO UPLOAD {path}")
        self.db.write(path)
        logger.warning(f"TRUNCATE DONE ADD UPLOAD TASK")

    def unlink(self, path):
        logger.info(f"UNLINK CALLED WITH ID {random.randint(0, 100)}")
        if path[0] == "/":
            path = path[1:]
        self.db.deleteFile(path)

    def utimens(self, path, times=None):
        logger.info(f"UTIMENS CALLED WITH ID {random.randint(0, 100)}")
        if path[0] == "/":
            path = path[1:]
        os.utime(path, times)

    def write(self, path, data, offset, fh):
        id = random.randint(0, 100)
        logger.info(f"WRITE CALLED WITH ID {id}")
        ret = os.pwrite(fh, data, offset)
        new_size = offset + ret
        self.update_metadata(path, new_size)
        print(f"write, current metatdata {self.metadata}")
        self.db.write(path)
        # logger.warning(f"WRITE DONE ADD UPLOAD TASK")
        return ret
        
    def update_metadata(self, path, new_size):
        for item in self.metadata:
            if item["path_lower"] == path:
                item["size"] = new_size
                break
        self.update_metadata_file()

    def release(self, path, fh):
        logger.info(f"RELEASE CALLED WITH ID {random.randint(0, 100)}")
        os.close(fh)
        return 0


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
