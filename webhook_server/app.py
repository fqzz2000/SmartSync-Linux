from flask import Flask, request, Response, stream_with_context
import os
from queue import Queue
import json
import time
from datetime import datetime
import logging
import dropbox

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
        if len(userid) > 0 and userid not in user_queues:
            user_queues[userid] = Queue()
        user_queues[userid].put('File change detected')
    return '', 200

def stream_events(userid):
    while True:
        if userid in user_queues and not user_queues[userid].empty():
            message = user_queues[userid].get()
            time_format = "%Y-%m-%d %H:%M:%S"
            app.logger.debug(f"[{datetime.now().strftime(time_format)}]: notifying user {userid}")
            yield f"data: {message}\n\n"
        yield ":heartbeat\n\n"
        time.sleep(1)

@app.route('/events/<userid>', methods=['POST'])
def events(userid):
    token = request.get_json().get('token', None)
    db = dropbox.Dropbox(token)
    try:
        db.users_get_current_account()
    except:
        return 'Invalid token', 401
    return Response(stream_with_context(stream_events(userid)), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True, ssl_context=('certificates/vcm-39026.vm.duke.edu_root_last.pem', 'certificates/vcm-39026.vm.duke.edu.key'))