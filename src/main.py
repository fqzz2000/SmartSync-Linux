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
import signal

WORKING_DIR = "/home/qf37/ece566/finalproj/SmartSync-Linux/"

def signal_handler(sig, frame):
    print("Caught signal", sig)
    model.stop()
    sys.exit(0)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: {} <token>".format(sys.argv[0]))
        sys.exit(1)
    TOKEN = sys.argv[1]
    db = DropboxInterface(TOKEN)
    rootdir = os.path.join(WORKING_DIR, "cache")
    model = DropBoxModel(db, rootdir)
    model.clearAll()
    model.downloadAll()
    atexit.register(model.clearAll)
    if os.path.exists(os.path.join(WORKING_DIR, "dropbox.log")):
        os.unlink(os.path.join(WORKING_DIR, "dropbox.log"))

    # logging.basicConfig(filename='dropbox.log', level=logging.DEBUG)
    fuse = FUSE(
        FuseDropBox(rootdir, model),
        os.path.join(WORKING_DIR, "dropbox"),
        foreground=True,
        allow_other=True,
    )
