# interface layer to the dropbox api
import dropbox
class DropboxInterface:
    def __init__(self, token):
        self.dbx = dropbox.Dropbox(token)

    def list_folder(self, path):
        res = self.dbx.files_list_folder(path)
        rv = {}
        for entry in res.entries:
            rv[entry.name] = entry
        return rv
    
    def upload(self, file, path):
        with open(file, 'rb') as f:
            self.dbx.files_upload(f.read(), path)

    def download(self, path, file):
        self.dbx.files_download_to_file(file, path)

    def mkdir(self, path):
        self.dbx.files_create_folder(path)
    
    def delete(self, path):
        self.dbx.files_delete(path)

    def getmetadata(self, path):
        rc = self.dbx.files_get_metadata(path)
        ret = {}
        ret["name"] = rc.name
        ret["preview_url"] = rc.preview_url

        return ret 
        
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: {} <token>".format(sys.argv[0]))
        sys.exit(1)
    rootPath = "/home/qf37/ece566/finalproj/SmartSync-Linux/rootdir"
    db = DropboxInterface(sys.argv[1])
    dic = db.list_folder("")
    for k, v in dic.items():
        print(k, v)

    