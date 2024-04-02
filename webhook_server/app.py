from flask import Flask, request, Response, stream_with_context
import os
from queue import Queue
import json

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
        if userid not in user_queues:
            user_queues[userid] = Queue()
        user_queues[userid].put('File change detected')
    return '', 200

def stream_events(userid):
    while True:
        if userid in user_queues and not user_queues[userid].empty():
            message = user_queues[userid].get()
            yield f"data: {message}\n\n"

@app.route('/events/<userid>')
def events(userid):
    return Response(stream_with_context(stream_events(userid)), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True, ssl_context=('certificates/vcm-38030.vm.duke.edu_root_last.pem', 'certificates/vcm-38030.vm.duke.edu.key'))