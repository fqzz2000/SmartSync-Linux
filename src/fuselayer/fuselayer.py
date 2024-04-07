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

    def __init__(self, rootdir, dbmodel):
        self.rootdir = rootdir
#        print("ROOTDIR IS", rootdir)
        self.db = dbmodel
        logger.remove()
        logger.add("/tmp/dropbox/dropbox.log", level="INFO")
        self.metadata = {}
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
        
        file_name = os.path.basename(path)
        new_file_metadata = [file_name, 0, "file"]
        self.metadata[path] = new_file_metadata
        # print(f"create, current metatdata {self.metadata}")
        if path[0] == "/":
            path = path[1:]
        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        return os.open(local_path, os.O_CREAT | os.O_WRONLY, mode)

            
    def getattr(self, path, fh=None):
        logger.info(f"GETATTR CALLED WITH ID {random.randint(0, 100)}")
     
        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        now = time.time()
        default_attrs = {
            'st_atime': now,  
            'st_ctime': now,  
            'st_mtime': now,  
            'st_gid': os.getgid(),  
            'st_uid': os.getuid(),  
            'st_blksize': 4096, #assume size
        }
   
        if path == "/":
            attrs = {'st_mode': (S_IFDIR | 0o755), **default_attrs} 
            return attrs

        if os.path.exists(local_path):
            try:
                ret = os.stat(local_path)
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
            except OSError as e:
                raise FuseOSError(e.errno)
            
        if path in self.metadata:
            m_data = self.metadata[path]
            attrs = {
                **default_attrs,
                'st_mode': (S_IFDIR | 0o755) if m_data[2] == "folder" else (S_IFREG | 0o644),
                'st_nlink': 2 if m_data[2] == "folder" else 1,
                'st_size': m_data[1] if m_data[1] is not None else 0,
                
            }
            st_size = m_data[1] if m_data[1] is not None else 0
            attrs['st_blocks'] = (st_size + 511) // 512
            return attrs
        
        # If the path does not exist in the metadata
        raise FuseOSError(errno.ENOENT)
        

    def getxattr(self, path, name, position=0):
        logger.info(f"GETXATTR CALLED WITH ID {random.randint(0, 100)}")
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

        local_path = os.path.join(self.rootdir, path.lstrip('/'))
        # print("path: ", path)
        if path in self.metadata:
            if not os.path.exists(local_path):
                item = self.metadata[path]
                if item[2] == "file":
                    self.db.open_file(path, local_path)

        elif os.path.exists(local_path): 
            pass
        else:
            raise FileNotFoundError(f"Path {path} does not exist in both local and metadata.")
        
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
        
        self.update_metadata()

        local_path = os.path.join(self.rootdir, path.lstrip('/'))

        if not os.path.exists(local_path):
            os.makedirs(local_path, exist_ok=True)
        
        direntries = ['.', '..']
        for m_path in self.metadata.keys():
            if os.path.dirname(m_path.lstrip('/')) == path.lstrip('/'):
                    # print("path: ", path)
                    m_name = self.metadata[m_path][0]
                    if m_name not in direntries:
                        direntries.append(m_name)
        
        # print(direntries)
        return direntries
    
    def update_metadata(self):
        with open(self.metadata_file_path, 'r') as f:
            tmp_metadata = json.load(f)

        if(len(self.metadata) < len(tmp_metadata)):
            self.metadata = tmp_metadata
        else:
            with open(self.metadata_file_path, 'w') as f:
                json.dump(self.metadata, f, indent=4)

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

        self.db.move(old.lstrip('/'), new.lstrip('/'))
        local_path = os.path.join(self.rootdir, new.lstrip('/'))
        print("loca: ", local_path)
        if old in self.metadata:
            m_type = self.metadata[old][2]
            self.metadata[new] = self.metadata.pop(old)
            self.metadata[new][0] = os.path.basename(local_path)
            if m_type == "folder":
                old_prefix = old + '/'
                new_prefix = new + '/'
                keys_to_update = [k for k in self.metadata.keys() if k.startswith(old_prefix)]
                for key in keys_to_update:
                    new_key = new_prefix + key[len(old_prefix):]
                    self.metadata[new_key] = self.metadata.pop(key)

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
        # logger.info(f"WRITE CALLED WITH ID {id}")
        ret = os.pwrite(fh, data, offset)
        new_size = offset + ret
        self.metadata[path][1] = new_size
        self.db.write(path)
        # logger.warning(f"WRITE DONE ADD UPLOAD TASK")
        return ret
    

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
