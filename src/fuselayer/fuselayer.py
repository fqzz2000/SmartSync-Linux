#!/bin/python3
# the fuse interaction layer
import random
from src.lib import FUSE, LoggingMixIn, Operations, FuseOSError
import logging
import errno
import errno
import os
from loguru import logger


class FuseDropBox(LoggingMixIn, Operations):
    "Example memory filesystem. Supports only one level of files."

    def __init__(self, rootdir, dbmodel):
        self.rootdir = rootdir
        #        print("ROOTDIR IS", rootdir)
        self.db = dbmodel
        logger.remove()
        logger.add("/tmp/dropbox/dropbox.log", level="INFO")

    def chmod(self, path, mode):
        # logger.info(f"CHMOD CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        logger.info(f"CHMOD CALLED, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        return os.chmod(path, mode)

    def chown(self, path, uid, gid):
        # logger.info(f"CHOWN CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        logger.info(f"CHOWN CALLED, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.chown(path, uid, gid)

    def create(self, path, mode):
        # logger.info(f"CREATE CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        logger.info(f"CREATE CALLED, path: {path}")
        ret = self.db.createFile(path, mode)
        if ret == -1:
            raise FuseOSError(errno.ENOENT)
        return ret

    def getattr(self, path, fh=None):
        logger.info(f"GETATTR CALLED, path: {path}")
        # logger.info(f"GETATTR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        return self.db.getattr(path)

    def getxattr(self, path, name, position=0):
        # logger.info(f"GETXATTR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        logger.info(f"GETXATTR CALLED, path: {path}")
        ret = b"default"
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
        # logger.info(f"LISTXATTR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        logger.info(f"LISTXATTR CALLED, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.listxattr(path)

    def mkdir(self, path, mode):
        logger.info(f"MKDIR CALLED, path: {path}")
        # logger.info(f"MKDIR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if self.db.createFolder(path.lstrip("/"), mode) == -1:
            raise FuseOSError(errno.ENOENT)

    def open(self, path, flags):
        logger.info(f"OPEN CALLED, path: {path}")
        # logger.info(f"OPEN CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        local_path = os.path.join(self.rootdir, path.lstrip("/"))

        return self.db.open_file(path, local_path, flags)

    def read(self, path, size, offset, fh):
        # id = random.randint(0, 100)
        # logger.info(f"READ CALLED, path: {path}")
        # logger.debug(f"STARTING READ WITH ID {id}")

        local_path = os.path.join(self.rootdir, path.lstrip("/"))
        with open(local_path, "rb") as f:
            f.seek(offset)
            return f.read(size)

    def readdir(self, path, fh):
        logger.info(f"READDIR CALLED, path: {path}")
        # logger.info(f"READDIR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        # remote_metadata = self.db.saveMetadataToFile()
        return self.db.readdir(path)

    def readlink(self, path):
        logger.info(f"READLINK CALLED, path: {path}")
        # logger.info(f"READLINK CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        return os.readlink(path)

    def removexattr(self, path, name):
        logger.info(f"REMOVEXATTR CALLED, path: {path}")
        # logger.info(f"REMOVEXATTR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.removexattr(path, name)

    def rename(self, old, new):
        # logger.info(f"RENAME CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        logger.info(f"RENAME CALLED, path: {old} to {new}")

        if self.db.move(old.lstrip("/"), new.lstrip("/")) == -1:
            raise FuseOSError(errno.ENOENT)

    def rmdir(self, path):
        # logger.info(f"RMDIR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        logger.info(f"RMDIR CALLED, path: {path}")
        # with multiple level support, need to raise ENOTEMPTY if contains any files
        if self.db.deleteFolder(path.lstrip("/")) == -1:
            raise FuseOSError(errno.ENOENT)

    def setxattr(self, path, name, value, options, position=0):
        # logger.info(f"SETXATTR CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        logger.info(f"SETXATTR CALLED, path: {path}")
        if path[0] == "/":
            path = path[1:]
        path = os.path.join(self.rootdir, path)
        os.setxattr(path, name, value, options)

    def statfs(self, path):
        logger.info(f"STATFS CALLED, path: {path}")
        # logger.info(f"STATFS CALLED WITH ID {random.randint(0, 100)}, path: {path}")

        total_space, used_space = self.db.getSpaceUsage()
        free_space = total_space - used_space
        block_size = 512
        total_blocks = total_space // block_size
        free_blocks = free_space // block_size
        return {
            "f_bsize": block_size,
            "f_blocks": total_blocks,
            "f_bfree": free_blocks,
            "f_bavail": free_blocks,
            "f_files": 0,
            "f_ffree": 0,
        }

    def symlink(self, target, source):
        # logger.info(f"SYMLINK CALLED WITH ID {random.randint(0, 100)}, path: {path}")'
        logger.info(f"SYMLINK CALLED, path: {target}")
        # os.close(os.open(target, os.O_CREAT))
        if target[0] == "/":
            target = target[1:]
        target = os.path.join(self.rootdir, target)
        if source[0] == "/":
            source = source[1:]
        source = os.path.join(self.rootdir, source)
        os.symlink(source, target)

    def truncate(self, path, length, fh=None):
        logger.info(f"TRUNCATE CALLED, path: {path}")
        # logger.info(f"TRUNCATE CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        # make sure extending the file fills in zero bytes
        new_path = os.path.join(self.rootdir, path.lstrip("/"))
        os.truncate(new_path, length)
        # logger.warning(f"GOING TO UPLOAD {path}")
        self.db.write(path, os.path.getsize(new_path))
        # logger.warning(f"TRUNCATE DONE ADD UPLOAD TASK")

    def unlink(self, path):
        logger.info(f"UNLINK CALLED, path: {path}")
        # logger.info(f"UNLINK CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if self.db.deleteFile(path.lstrip("/")) == -1:
            raise FuseOSError(errno.ENOENT)
        

    def utimens(self, path, times=None):
        logger.info(f"UTIMENS CALLED, path: {path}")
        # logger.info(f"UTIMENS CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        if path[0] == "/":
            path = path[1:]
        os.utime(path, times)

    def write(self, path, data, offset, fh):
        # id = random.randint(0, 100)
        # logger.info(f"WRITE CALLED WITH ID {id}")
        ret = os.pwrite(fh, data, offset)
        # local_path = os.path.join(self.rootdir, path)
        # new_size = offset + ret
        self.db.write(path, offset + ret)
        # TODO
        # upload and change uploaded to True
        # self.db.upload(local_path,path, new_size)
        # logger.warning(f"WRITE DONE ADD UPLOAD TASK")
        return ret

    def release(self, path, fh):
        # logger.info(f"RELEASE CALLED WITH ID {random.randint(0, 100)}, path: {path}")
        logger.info(f"RELEASE CALLED, path: {path}")
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
