# cmd of the dropbox daemon
from data import DropboxInterface
from fuselayer import FuseDropBox
from lib import FUSE
from model import DropBoxModel
import logging
import atexit
import dropbox
from dropbox import DropboxOAuth2Flow
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
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json

APP_KEY = "p379vmpas0tf58c"
REDIRECT_URI = "http://localhost:9090"
WORKING_DIR = os.path.expanduser("~/Desktop")
TMP_DIR = "/tmp/dropbox"
pid_file = os.path.join(TMP_DIR, "dropbox.pid")
auth_token = None

# def signal_handler(sig, frame):
#     print("Caught signal", sig)
#     model.stop()
#     sys.exit(0)
# signal.signal(signal.SIGTERM, signal_handler)

class OAuthRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        if 'token' in data:
            global auth_token 
            auth_token = data['token']
            self.send_response(200)
            self.end_headers()
            event.set()
        else:
            self.send_response(400)
            self.end_headers()

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
    global event
    event = threading.Event()
    if not os.path.exists(TMP_DIR):
        os.mkdir(TMP_DIR)
    if not os.path.exists(WORKING_DIR):
        os.mkdir(WORKING_DIR)
    if not os.path.exists(os.path.join(WORKING_DIR, ".cache")):
        os.mkdir(os.path.join(WORKING_DIR, ".cache"))
    if not os.path.exists(os.path.join(WORKING_DIR, "dropbox")):
        os.mkdir(os.path.join(WORKING_DIR, "dropbox"))

    #auth_flow = DropboxOAuth2Flow(APP_KEY, redirect_uri=REDIRECT_URI, session=session, csrf_token_session_key='dropbox-auth-csrf-token', use_pkce=True, token_access_type='offline')
    #requests.get(f"http://localhost:5000/start")
    # authorize_url = response.text
    # print(authorize_url)
    authorize_url = "http://localhost:5000/start"
    webbrowser.open(authorize_url)
    server_address = ('127.0.0.1', 5001)
    httpd = HTTPServer(server_address, OAuthRequestHandler)
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    event.wait()
    httpd.shutdown()
    #exit the program
    print(auth_token)
    print("Dropbox is ready to use.")
    exit(0)
    # print("1. Click \"Allow\" (you might have to log in first).")
    # print("2. Copy the authorization code.")
    # print("(Visit this url if your web browser fails to boot:" + authorize_url + ")")
    # auth_code = input("Enter the authorization code here: ").strip()

    #token = oauth_result.access_token
    print("Start setting up your dropbox...")
    db = DropboxInterface(auth_token)
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
    
