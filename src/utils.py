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

class FilePath(): 
    def __init__(self, rootdir, tmpdir) -> None:
        if rootdir[-1] == '/':
            rootdir = rootdir[:-1]
        if tmpdir[-1] == '/':
            tmpdir = tmpdir[:-1]
        self.rootdir = rootdir
        self.tmpdir = tmpdir

    def getTmpPath(self, path):
        return self.tmpdir + self.getRemotePath(path)

    def getLocalPath(self, path):
        return self.rootdir + self.getRemotePath(path)
    
    def getRemotePath(self, path):
        if len(path) == 0:
            return '/'
        elif path[0] == '/':
            return path
        else:
            return '/' + path
