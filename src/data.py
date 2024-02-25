# interface layer to the dropbox api
import dropbox
class DropboxInterface:
    def __init__(self, token):
        self.dbx = dropbox.Dropbox(token)

    