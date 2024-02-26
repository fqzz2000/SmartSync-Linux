# cmd of the dropbox daemon
from data import DropboxInterface
from fuselayer import FuseDropBox
from lib import FUSE
from model import DropBoxModel
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: {} <token>".format(sys.argv[0]))
        sys.exit(1)
    TOKEN = sys.argv[1]
    db = DropboxInterface(TOKEN)
    model = DropBoxModel(db)
    rootdir = "/home/qf37/ece566/finalproj/SmartSync-Linux/rootdir"
    fuse = FUSE(FuseDropBox(rootdir, model), "/home/qf37/ece566/finalproj/SmartSync-Linux/mntdir", foreground=True, allow_other=True)
    