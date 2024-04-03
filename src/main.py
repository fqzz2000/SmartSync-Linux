# cmd of the dropbox daemon
from data.data import DropboxInterface
from fuselayer import FuseDropBox
from lib import FUSE
from model import DropBoxModel
import atexit
import os
import sys
import argparse
import subprocess
import shutil
import daemon
from daemon import pidfile
import webbrowser
import threading
import requests
from loguru import logger
from multiprocessing import Process, Queue
from flask import Flask, request, redirect, session
import dropbox
import logging
import config

WORKING_DIR = os.path.expanduser("~/Desktop")
pid_file = os.path.join(config.TMP_DIR, "dropbox.pid")
auth_token = None
user_id = None
login_app = Flask(__name__)
login_app.secret_key = os.urandom(24)
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
queue = Queue()

auth_flow = dropbox.DropboxOAuth2Flow(config.APP_KEY, config.REDIRECT_URI, session, 'dropbox-auth-csrf-token', use_pkce=True, token_access_type='offline')

@login_app.route('/start')
def start():
    authorize_url = auth_flow.start()
    return redirect(authorize_url)

@login_app.route('/oauth2/callback')
def callback():
    try:
        oauth_result = auth_flow.finish(request.args)
        queue.put(oauth_result.access_token)
        return 'Success'
    except Exception as e:
        return f"Error: {e}"
    
# def signal_handler(sig, frame):
#     print("Caught signal", sig)
#     model.stop()
#     sys.exit(0)
# signal.signal(signal.SIGTERM, signal_handler)

def run_login_server():
    login_app.run(debug=False, port=5000, use_reloader=False)

def listen_for_events(url):
    while True:
        try:
            response = requests.get(url, stream=True)
            for line in response.iter_lines():
                if line and line[0] != b':'[0]:
                    # log the line with logging
                    logger.warning(f'Event: {line}')

        except Exception as e:
            print(f"Error listening for events: {e}")
    
def start_daemon():
    # create directories and clearing previous logs
    if not os.path.exists(config.TMP_DIR):
        os.mkdir(config.TMP_DIR)
    if not os.path.exists(WORKING_DIR):
        os.mkdir(WORKING_DIR)
    if not os.path.exists(os.path.join(WORKING_DIR, ".cache")):
        os.mkdir(os.path.join(WORKING_DIR, ".cache"))
    if not os.path.exists(os.path.join(WORKING_DIR, "dropbox")):
        os.mkdir(os.path.join(WORKING_DIR, "dropbox"))
    rootdir = os.path.join(WORKING_DIR, ".cache")
    swapdir = os.path.join(WORKING_DIR, ".swap")
    if os.path.exists(os.path.join(config.TMP_DIR, "dropbox.log")):
        os.unlink(os.path.join(config.TMP_DIR, "dropbox.log")) 
    if os.path.exists(os.path.join(config.TMP_DIR, "std_out.log")):
        os.unlink(os.path.join(config.TMP_DIR, "std_out.log")) 
    if os.path.exists(os.path.join(config.TMP_DIR, "std_err.log")):
        os.unlink(os.path.join(config.TMP_DIR, "std_err.log")) 

    # fetching auth token
    login_server_process = Process(target=run_login_server)
    login_server_process.start()
    authorize_url = "http://localhost:5000/start"
    # print(f"{os.getpid()}: browser launching...")
    webbrowser.open(authorize_url)
    global auth_token
    while True:
        if not queue.empty():
            auth_token = queue.get()
            break;
    print("Auth token fetched successfully!")
    print("Terminating login flask server...")
    login_server_process.terminate()
    login_server_process.join()
    
    # setting up dropbox instance
    os.environ['MY_APP_AUTH_TOKEN'] = auth_token
    # print("Start setting up your dropbox...")
    
    # start daemon

    context = daemon.DaemonContext(
        pidfile=pidfile.TimeoutPIDLockFile(pid_file),
        stdout=open(os.path.join(config.TMP_DIR, 'std_out.log'), 'w+'),
        stderr=open(os.path.join(config.TMP_DIR, 'std_err.log'), 'w+'),
    )
    with context:
        auth_token = os.getenv('MY_APP_AUTH_TOKEN')
        db = DropboxInterface(auth_token)


        model = DropBoxModel(db, rootdir, swapdir)

        model.clearAll()
        model.downloadAll()
        atexit.register(model.clearAll)

        # setting up thread listening for updates
        global user_id
        user_id = db.dbx.users_get_current_account().account_id
        url = f"{config.SUBSCRIBE_URL}/{user_id}"
        subscribe_thread = threading.Thread(target=listen_for_events, args=(url,))
        subscribe_thread.daemon = True
        subscribe_thread.start()
        
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

    
