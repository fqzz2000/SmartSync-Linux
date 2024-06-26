# cmd of the dropbox daemon
from src.data.data import DropboxInterface
from src.fuselayer.fuselayer import FuseDropBox
from src.lib.fuse import FUSE
from src.model.model import DropBoxModel
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
import src.config.config as config
import signal

WORKING_DIR = os.path.expanduser("~/Desktop")
pid_file = os.path.join(config.TMP_DIR, "dropbox.pid")
auth_token = None
user_id = None
login_app = Flask(__name__)
login_app.secret_key = os.urandom(24)
logging.getLogger("werkzeug").setLevel(logging.CRITICAL)
queue = Queue()

auth_flow = dropbox.DropboxOAuth2Flow(
    config.APP_KEY,
    config.REDIRECT_URI,
    session,
    "dropbox-auth-csrf-token",
    use_pkce=True,
    token_access_type="offline",
)


@login_app.route("/start")
def start():
    authorize_url = auth_flow.start()
    return redirect(authorize_url)


@login_app.route("/oauth2/callback")
def callback():
    try:
        oauth_result = auth_flow.finish(request.args)
        queue.put(oauth_result.access_token)
        return "Success"
    except Exception as e:
        return f"Error: {e}"


# def signal_handler(sig, frame):
#     print("Caught signal", sig)
#     model.stop()
#     sys.exit(0)
# signal.signal(signal.SIGTERM, signal_handler)


def run_login_server():
    login_app.run(debug=False, port=5000, use_reloader=False)


def listen_for_events(url, data, model):
    print(f"Listening for events at {url}")
    max_retry = 3
    retry = 0
    while True:
        try:
            response = requests.post(url, json=data, stream=True)
            print(f"Response: {response.status_code}")
            if response.status_code != 200:
                print(f"Error: {response.text}")
                logger.error(f"Error: {response.text}")
                if retry < max_retry:
                    retry += 1
                    continue
                else:
                    print("Max retry reached. Exiting...")
                    logger.error("Max retry reached. Exiting...")
                    break
            for line in response.iter_lines():
                if line and line[0] != b":"[0]:
                    # log the line with logging
                    print(f"Event: {line}")
                    model.updateFullMetadata()
                    logger.warning(f"Event: {line}")

        except Exception as e:
            print(f"Error listening for events: {e}")


def start_daemon(args):
    # create directories and clearing previous logs
    if not os.path.exists(config.TMP_DIR):
        os.makedirs(config.TMP_DIR, exist_ok=True)
    if not os.path.exists(WORKING_DIR):
        os.makedirs(WORKING_DIR, exist_ok=True)
    if not os.path.exists(os.path.join(WORKING_DIR, ".cache")):
        os.makedirs(os.path.join(WORKING_DIR, ".cache"), exist_ok=True)
    if not os.path.exists(os.path.join(WORKING_DIR, "dropbox")):
        os.makedirs(os.path.join(WORKING_DIR, "dropbox"), exist_ok=True)
    rootdir = os.path.join(WORKING_DIR, ".cache")
    swapdir = os.path.join(WORKING_DIR, ".swap")
    if os.path.exists(os.path.join(config.TMP_DIR, "dropbox.log")):
        os.unlink(os.path.join(config.TMP_DIR, "dropbox.log"))
    if os.path.exists(os.path.join(config.TMP_DIR, "std_out.log")):
        os.unlink(os.path.join(config.TMP_DIR, "std_out.log"))
    if os.path.exists(os.path.join(config.TMP_DIR, "std_err.log")):
        os.unlink(os.path.join(config.TMP_DIR, "std_err.log"))
    if not args.t:
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
                break
        print("Auth token fetched successfully!")
        print("Terminating login flask server...")
        login_server_process.terminate()
        login_server_process.join()

        # setting up dropbox instance
        # write token to a file
        with open(os.path.join(config.TMP_DIR, "auth_token.txt"), "w") as file:
            file.write(auth_token)
        os.environ["MY_APP_AUTH_TOKEN"] = auth_token
    # print("Start setting up your dropbox...")
    else:
        print("Test mode enabled")
    # start daemon

    context = daemon.DaemonContext(
        pidfile=pidfile.TimeoutPIDLockFile(pid_file),
        stdout=open(os.path.join(config.TMP_DIR, "std_out.log"), "w+"),
        stderr=open(os.path.join(config.TMP_DIR, "std_err.log"), "w+"),
    )
    with context:
        auth_token = os.getenv("MY_APP_AUTH_TOKEN")
        data = {"token": auth_token}

        db = DropboxInterface(auth_token)
        model = DropBoxModel(db, rootdir, swapdir)
        # model.clearAll()
        # model.downloadAll()
        # model.saveMetadataToFile()

        # obtain all the metadata and display in the dropbox folder
        # as placeholder
        # atexit.register(model.clearAll)

        # setting up thread listening for updates
        global user_id
        tmp_userid = db.dbx.users_get_current_account().account_id
        if ":" in tmp_userid:
            user_id = tmp_userid.split(":")[1]
        else:
            user_id = tmp_userid
        if len(user_id) == 0:
            print("Error: user_id is empty")
            sys.exit(1)
        print("user_id: ", user_id)
        url = f"{config.SUBSCRIBE_URL}/{user_id}"
        subscribe_thread = threading.Thread(
            target=listen_for_events, args=(url, data, model)
        )
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


def stop_daemon(args):
    if os.path.exists(pid_file):
        with open(pid_file, "r") as file:
            pid = file.read().strip()
            pid = int(pid)
    mount_point = os.path.join(WORKING_DIR, "dropbox")

    try:
        subprocess.run(["umount", mount_point], check=True)
        # rootdir = os.path.join(WORKING_DIR, ".cache")
        shutil.rmtree(mount_point)
    except Exception as e:
        print(f"unmount failure：{e}")
    try:
        os.kill(pid, signal.SIGKILL)
    except Exception as e:
        print(f"kill process failure：{e}")
    try:
        if os.path.exists(pid_file):
            os.unlink(pid_file)
    except Exception as e:
        print(f"remove pid file failure：{e}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Dropbox CLI")
    subparsers = parser.add_subparsers(dest="command")

    parser_start = subparsers.add_parser("start", help="Start the dropbox daemon")
    parser_start.add_argument(
        "-t",
        action="store_true",
        help="Enable test mode for the daemon pass auth token from env variable MY_APP_AUTH_TOKEN",
    )
    parser_start.set_defaults(func=start_daemon)

    parser_stop = subparsers.add_parser("stop", help="Stop the dropbox daemon")
    parser_stop.set_defaults(func=stop_daemon)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    else:
        args.func(args)
