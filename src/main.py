# cmd of the dropbox daemon
from data.data import DropboxInterface
from fuselayer import FuseDropBox
from lib import FUSE
from model import DropBoxModel
import logging
import atexit
import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect
import datetime
import time
import os
import signal
import sys
import argparse
import subprocess
import shutil
import webbrowser
import daemon
from daemon import pidfile

APP_KEY = "p379vmpas0tf58c"
WORKING_DIR = os.path.expanduser("~/Desktop")
TMP_DIR = "/tmp/dropbox"
pid_file = os.path.join(TMP_DIR, "dropbox.pid")

# def signal_handler(sig, frame):
#     print("Caught signal", sig)
#     model.stop()
#     sys.exit(0)
# signal.signal(signal.SIGTERM, signal_handler)

def main():
    parser = argparse.ArgumentParser(description="Dropbox CLI")
    subparsers = parser.add_subparsers(dest='command')

    parser_start = subparsers.add_parser('start', help='Start the dropbox daemon')
    parser_start.set_defaults(func=start_daemon)

    parser_stop = subparsers.add_parser('stop', help='Stop the dropbox daemon')
    parser_stop.set_defaults(func=stop_daemon)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    else:
        args.func()

def start_daemon():
    if not os.path.exists(TMP_DIR):
        os.mkdir(TMP_DIR)
    if not os.path.exists(WORKING_DIR):
        os.mkdir(WORKING_DIR)
    if not os.path.exists(os.path.join(WORKING_DIR, ".cache")):
        os.mkdir(os.path.join(WORKING_DIR, ".cache"))
    if not os.path.exists(os.path.join(WORKING_DIR, "dropbox")):
        os.mkdir(os.path.join(WORKING_DIR, "dropbox"))

    auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, use_pkce=True, token_access_type='offline')

    authorize_url = auth_flow.start()
    webbrowser.open(authorize_url)
    print("1. Click \"Allow\" (you might have to log in first).")
    print("2. Copy the authorization code.")
    print("(Visit this url if your web browser fails to boot:" + authorize_url + ")")
    auth_code = input("Enter the authorization code here: ").strip()

    try:
        oauth_result = auth_flow.finish(auth_code)
    except Exception as e:
        print('Error: %s' % (e,))
        exit(1)
    token = oauth_result.access_token
    print("Start setting up your dropbox...")
    db = DropboxInterface(token)
    rootdir = os.path.join(WORKING_DIR, ".cache")
    if os.path.exists(os.path.join(TMP_DIR, "dropbox.log")):
        os.unlink(os.path.join(TMP_DIR, "dropbox.log")) 
    if os.path.exists(os.path.join(TMP_DIR, "std_out.log")):
        os.unlink(os.path.join(TMP_DIR, "std_out.log")) 
    if os.path.exists(os.path.join(TMP_DIR, "std_err.log")):
        os.unlink(os.path.join(TMP_DIR, "std_err.log")) 
    context = daemon.DaemonContext(
        pidfile=pidfile.TimeoutPIDLockFile(pid_file),
        stdout=open(os.path.join(TMP_DIR, 'std_out.log'), 'w+'),
        stderr=open(os.path.join(TMP_DIR, 'std_err.log'), 'w+'),
    )

    with context:
        model = DropBoxModel(db, rootdir)
        model.clearAll()
        model.downloadAll()
        atexit.register(model.clearAll)
        
        try:
            fuse = FUSE(
                FuseDropBox(rootdir, model),
                os.path.join(WORKING_DIR, "dropbox"),
                foreground=True,
                allow_other=True,
            )
        except Exception as e:
            with open(os.path.join(WORKING_DIR, "hi.txt"), "a") as file:
                file.write(f"Error: {e}")
            model.stop()
            sys.exit(1)
    
    
    
def stop_daemon():
    try:
        mount_point = os.path.join(WORKING_DIR, "dropbox")
        subprocess.run(['umount', mount_point], check=True)
        shutil.rmtree(mount_point)
        rootdir = os.path.join(WORKING_DIR, ".cache")
        shutil.rmtree(rootdir)
        if os.path.exists(pid_file):
            os.unlink(pid_file)
    except subprocess.CalledProcessError as e:
        print(f"unmount failure：{e}")
    except Exception as e:
        print(f"ERROR：{e}")
    

if __name__ == "__main__":
    main()
    
