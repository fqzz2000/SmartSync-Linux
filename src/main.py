# cmd of the dropbox daemon
from data import DropboxInterface
from fuselayer import FuseDropBox
from lib import FUSE
from model import DropBoxModel
import logging
import atexit
import dropbox
import datetime
import time
import os

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: {} <token>".format(sys.argv[0]))
        sys.exit(1)
    TOKEN = sys.argv[1]
    db = DropboxInterface(TOKEN)
    rootdir = "/mnt/d/Duke/ECE566/finalproj/SmartSync-Linux/cache"
    model = DropBoxModel(db, rootdir)
    model.clearAll()
    model.downloadAll()
    atexit.register(model.clearAll)
    os.remove("dropbox.log")

    # logging.basicConfig(filename='dropbox.log', level=logging.DEBUG)
    fuse = FUSE(
        FuseDropBox(rootdir, model),
        "/mnt/d/Duke/ECE566/finalproj/SmartSync-Linux/dropbox",
        foreground=True,
        allow_other=True,
    )
