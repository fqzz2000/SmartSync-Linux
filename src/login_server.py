from flask import Flask, request, redirect, session
import dropbox
import requests
import os

login_app = Flask(__name__)
login_app.secret_key = os.urandom(24)

APP_KEY = 'p379vmpas0tf58c'
REDIRECT_URI = 'http://localhost:5000/oauth2/callback'

auth_flow = dropbox.DropboxOAuth2Flow(APP_KEY, REDIRECT_URI, session, 'dropbox-auth-csrf-token', use_pkce=True, token_access_type='offline')

@login_app.route('/start')
def start():
    authorize_url = auth_flow.start()
    print(authorize_url)
    return redirect(authorize_url)

@login_app.route('/oauth2/callback')
def callback():
    try:
        oauth_result = auth_flow.finish(request.args)
        print(oauth_result.access_token)
        url = 'http://localhost:5001/'
        data = {'token': oauth_result.access_token}
        requests.post(url, json=data)
        return 'Success'
    except dropbox.oauth.DropboxOAuth2FlowError as e:
        return 'Error: %s' % (e,)

@login_app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    shutdown_func()
    return 'Server shutting down...'

if __name__ == '__main__':
    login_app.run(debug=True, port=5000)
