from flask import Flask, request, Response, stream_with_context
import os
from queue import Queue
import json
import time
from datetime import datetime
import logging
import dropbox
import uuid
import threading

lock = threading.Lock()

logging.basicConfig(filename='webhook_server.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
app = Flask(__name__)
app.secret_key = os.urandom(24)

user_queues = {}

@app.route('/webhook', methods=['GET'])
def verify():
    return request.args.get('challenge')

@app.route('/webhook', methods=['POST'])
def webhook():
    # Verify the message is from Dropbox (how to store the APP_SECRET?)
    # signature = request.headers.get('X-Dropbox-Signature')
    # if not hmac.compare_digest(signature, hmac.new(APP_SECRET, request.data, sha256).hexdigest()):
    #     abort(403)
    
    for userid in json.loads(request.data)['list_folder']['accounts']:
        if ':' not in userid:
            continue
        userid = userid.split(':')[1]
        if len(userid) > 0:
            if userid not in user_queues:
                return '', 200
            with lock:
                for connection_id in user_queues[userid]:
                    user_queues[userid][connection_id].put('File change detected')
    return '', 200

def stream_events(userid, connection_id):
    try:
        while True:
            if userid in user_queues and connection_id in user_queues[userid] and not user_queues[userid][connection_id].empty():
                message = user_queues[userid][connection_id].get()
                time_format = "%Y-%m-%d %H:%M:%S"
                app.logger.debug(f"[{datetime.now().strftime(time_format)}]: notifying user {userid}")
                yield f"data: {message}\n\n"
            yield ":heartbeat\n\n"
            time.sleep(1)
    finally:
        delete_user_connection(userid, connection_id)

def delete_user_connection(userid, connection_id):
    with lock:
        if userid in user_queues and connection_id in user_queues[userid]:
            del user_queues[userid][connection_id]
            if not user_queues[userid]:
                del user_queues[userid]

@app.route('/events/<userid>', methods=['POST'])
def events(userid):
    connection_id = str(uuid.uuid4())
    token = request.get_json().get('token', None)
    db = dropbox.Dropbox(token)
    try:
        actual_userid = db.users_get_current_account().account_id
        if ':' in actual_userid:
            actual_userid = actual_userid.split(':')[1]
        if actual_userid != userid:
            return 'Unauthorized', 401
    except:
        return 'Invalid token', 401
    with lock:
        if len(userid) > 0 and userid not in user_queues:
            user_queues[userid] = {}
        if connection_id not in user_queues[userid]:
            user_queues[userid][connection_id] = Queue()

    response = Response(stream_with_context(stream_events(userid, connection_id)), content_type='text/event-stream')
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True, ssl_context=('certificates/vcm-39026.vm.duke.edu_root_last.pem', 'certificates/vcm-39026.vm.duke.edu.key'))