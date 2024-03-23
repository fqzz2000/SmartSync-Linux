#!/bin/python3
# the fuse interaction layer
from lib import FUSE, LoggingMixIn, Operations, FuseOSError
import logging
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
import errno
from time import time
from collections import defaultdict
import os

class FuseDropBox(LoggingMixIn, Operations):
    'Example memory filesystem. Supports only one level of files.'

    def __init__(self, rootdir, dbmodel):
        self.rootdir = rootdir
        print("ROOTDIR IS", rootdir)
        self.db = dbmodel

    def chmod(self, path, mode):
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        return os.chmod(path, mode)

    def chown(self, path, uid, gid):
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.chown(path, uid, gid)

    def create(self, path, mode):
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        print ("PATH IS", path)
        return os.open(path, os.O_CREAT|os.O_WRONLY)

    def getattr(self, path, fh=None):
        if path[0] == "/":
            path = path[1:]

        newpath = os.path.join(self.rootdir, path)
        # print(newpath)
        try:
            ret = os.lstat(newpath)
            # print(ret)
            return {
                'st_atime': ret.st_atime,
                'st_ctime': ret.st_ctime,
                'st_gid': ret.st_gid,
                'st_mode': ret.st_mode,
                'st_mtime': ret.st_mtime,
                'st_nlink': ret.st_nlink,
                'st_size': ret.st_size,
                'st_uid': ret.st_uid
            }
        except FileNotFoundError:
            #print(e)
            raise FuseOSError(errno.ENOENT)
        # except FileNotFoundError:
        #     # find the file in the dropbox
        #     # get base name
        #     if len(path) == 0 or path[0] != "/":
        #         path = "/" + path
        #     print("PATH IS", path)
        #     metadata = self.db.getmetadata(path)
        #     if isinstance(metadata, dict):
        #         return {
        #             'st_atime': time(),
        #             'st_ctime': time(),
        #             'st_gid': os.getgid(),
        #             'st_mode': S_IFREG | 0o644,
        #             'st_mtime': time(),
        #             'st_nlink': 1,
        #             'st_size': 0,
        #             'st_uid': os.getuid()
        #         }
            

    def getxattr(self, path, name, position=0):
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
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.listxattr(path)

    def mkdir(self, path, mode):
        if path[0] == "/":
            path = path[1:]
        new_path = os.path.join(self.rootdir, path)
        os.mkdir(new_path, mode)
        self.db.createFolder("/" + path)

    def open(self, path, flags):
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        return os.open(path, flags)


    def read(self, path, size, offset, fh):
        data = os.pread(fh, size, offset)
        return data

    def readdir(self, path, fh):
        if path[0] == "/":
            path = path[1:]
        newpath = os.path.join(self.rootdir, path)
        return ['.','..'] + os.listdir(newpath)
        # if path == "/":
        #     path = ""
        # rv = self.db.listFolder(path)
        # return ['.', '..'] + list(rv.keys())

    def readlink(self, path):
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        return os.readlink(path)

    def removexattr(self, path, name):
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.removexattr(path, name)

    def rename(self, old, new):
        if old[0] == "/":
            old = old[1:]
        if new[0] == "/":
            new = new[1:]
        old_path = os.path.join(self.rootdir, old)
        new_path = os.path.join(self.rootdir, new)
        os.rename(old_path, new_path)
        self.db.move("/" + old, "/" + new)  


    def rmdir(self, path):
        # with multiple level support, need to raise ENOTEMPTY if contains any files
        if path[0] == "/":
            path = path[1:]
        new_path = os.path.join(self.rootdir, path)
        os.rmdir(new_path)
        self.db.deleteFile("/" + path)

    def setxattr(self, path, name, value, options, position=0):
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.setxattr(path, name, value, options)

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        
        # os.close(os.open(target, os.O_CREAT))
        if target[0] == "/":
            target = target[1:]
        target = os.path.join(self.rootdir, target)
        if source[0] == "/":
            source = source[1:]
        source = os.path.join(self.rootdir, source)
        os.symlink(source, target)

    def truncate(self, path, length, fh=None):
        # make sure extending the file fills in zero bytes
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.truncate(path, length)

    def unlink(self, path):
        if path[0] == "/":
            path = path[1:]
        new_path = os.path.join(self.rootdir, path)
        os.unlink(new_path)
        self.db.deleteFile("/" + path)

    def utimens(self, path, times=None):
        if path[0] == "/":
            path = path[1:]
        os.utime(path, times)

    def write(self, path, data, offset, fh):
        return os.pwrite(fh, data, offset)
    
    def release(self, path, fh):
        os.close(fh)
        self.db.write(path)
        return 0
    

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('mountdir')
    parser.add_argument('rootdir')
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    fuse = FUSE(FuseDropBox(args.rootdir), args.mountdir, foreground=True, allow_other=True)