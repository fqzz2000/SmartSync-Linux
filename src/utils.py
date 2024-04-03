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
    """
    Represents a file path utility class.

    Args:
        rootdir (str): The root directory path.
        tmpdir (str): The temporary directory path.

    Attributes:
        rootdir (str): The root directory path.
        tmpdir (str): The temporary directory path.
    """

    def __init__(self, rootdir, tmpdir) -> None:
        if rootdir[-1] == '/':
            rootdir = rootdir[:-1]
        if tmpdir[-1] == '/':
            tmpdir = tmpdir[:-1]
        self.rootdir = rootdir
        self.tmpdir = tmpdir

    def getTmpPath(self, path):
        """
        Get the temporary path for a given file path.

        Args:
            path (str): The file path.

        Returns:
            str: The temporary path for the file.
        """
        return self.tmpdir + self.getRemotePath(path)

    def getLocalPath(self, path):
        """
        Get the local path for a given file path.

        Args:
            path (str): The file path.

        Returns:
            str: The local path for the file.
        """
        return self.rootdir + self.getRemotePath(path)
    
    def getRemotePath(self, path):
        """
        Get the remote path for a given file path.

        Args:
            path (str): The file path.

        Returns:
            str: The remote path for the file.
        """
        if len(path) == 0:
            return '/'
        elif path[0] == '/':
            return path
        else:
            return '/' + path
