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

    def __init__(self):
        self.files = {}
        self.data = defaultdict(bytes)
        self.fd = 0
        now = time()
        self.files['/'] = dict(
            st_mode=(S_IFDIR | 0o755),
            st_ctime=now,
            st_mtime=now,
            st_atime=now,
            st_nlink=2)

    def chmod(self, path, mode):
        self.files[path]['st_mode'] &= 0o770000
        self.files[path]['st_mode'] |= mode
        return 0

    def chown(self, path, uid, gid):
        self.files[path]['st_uid'] = uid
        self.files[path]['st_gid'] = gid

    def create(self, path, mode):
        self.files[path] = dict(
            st_mode=(S_IFREG | mode),
            st_nlink=1,
            st_size=0,
            st_ctime=time(),
            st_mtime=time(),
            st_atime=time())
        self.data[path] = b''
        
        self.fd += 1
        return os.open(path, os.O_CREAT|os.O_WRONLY)

    def getattr(self, path, fh=None):
        # print(os.lstat(path))
        # if path not in self.files:
        #     raise FuseOSError(ENOENT)
        # now = time()
        # if path == "/":
        #     return dict(
        #     st_mode=(S_IFDIR | 0o755),
        #     st_ctime=now,
        #     st_mtime=now,
        #     st_atime=now,
        #     st_nlink=2)
        
        # return self.files[path]
        ret = os.lstat(path)
        # make ret to a dict
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

    def getxattr(self, path, name, position=0):
        attrs = self.files[path].get('attrs', {})

        try:
            return attrs[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def listxattr(self, path):
        attrs = self.files[path].get('attrs', {})
        return attrs.keys()

    def mkdir(self, path, mode):
        self.files[path] = dict(
            st_mode=(S_IFDIR | mode),
            st_nlink=2,
            st_size=0,
            st_ctime=time(),
            st_mtime=time(),
            st_atime=time())

        self.files['/']['st_nlink'] += 1

    def open(self, path, flags):
        self.fd += 1
        
        return os.open(path, flags)

    def read(self, path, size, offset, fh):
        data = os.pread(fh, size, offset)
        # return self.data[path][offset:offset + size]
        return data

    def readdir(self, path, fh):
        # return ['.', '..'] + [x[1:] for x in self.files if x != '/']
        return ['.','..'] + os.listdir(path)

    def readlink(self, path):
        return self.data[path]

    def removexattr(self, path, name):
        attrs = self.files[path].get('attrs', {})

        try:
            del attrs[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        self.data[new] = self.data.pop(old)
        self.files[new] = self.files.pop(old)

    def rmdir(self, path):
        # with multiple level support, need to raise ENOTEMPTY if contains any files
        self.files.pop(path)
        self.files['/']['st_nlink'] -= 1

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options
        attrs = self.files[path].setdefault('attrs', {})
        attrs[name] = value

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        self.files[target] = dict(
            st_mode=(S_IFLNK | 0o777),
            st_nlink=1,
            st_size=len(source))

        self.data[target] = source

    def truncate(self, path, length, fh=None):
        # make sure extending the file fills in zero bytes
        self.data[path] = self.data[path][:length].ljust(
            length, '\x00'.encode('ascii'))
        self.files[path]['st_size'] = length

    def unlink(self, path):
        self.data.pop(path)
        self.files.pop(path)

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        self.files[path]['st_atime'] = atime
        self.files[path]['st_mtime'] = mtime

    def write(self, path, data, offset, fh):
        self.data[path] = (
            # make sure the data gets inserted at the right offset
            self.data[path][:offset].ljust(offset, '\x00'.encode('ascii'))
            + data
            # and only overwrites the bytes that data is replacing
            + self.data[path][offset + len(data):])
        os.pwrite(fh, data, offset)
        self.files[path]['st_size'] = len(self.data[path])
        return len(data)
    def release(self, path, fh):
        # os.close(fh)
        return 0
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('mount')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    fuse = FUSE(FuseDropBox(), args.mount, foreground=True, allow_other=True)