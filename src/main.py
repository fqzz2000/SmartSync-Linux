# cmd of the dropbox daemon
from data import DropboxInterface
from fuselayer import FuseDropBox
from lib import FUSE
from model import DropBoxModel
import logging
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: {} <token>".format(sys.argv[0]))
        sys.exit(1)
    TOKEN = sys.argv[1]
    db = DropboxInterface(TOKEN)
    rootdir = "/home/tq22/ece566/SmartSync-Linux/cache"
    model = DropBoxModel(db)
    model.downloadAll(rootdir)
    logging.basicConfig(level=logging.DEBUG)
    # fuse = FUSE(FuseDropBox(rootdir, model), "/home/tq22/ece566/SmartSync-Linux/dropbox", foreground=True, allow_other=True)

    