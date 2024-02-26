# commandline interface for the program
from data import DropboxInterface
from lib import FUSE
class DropBoxModel():
    def __init__(self, interface) -> None:
        self.dbx = interface

    def __del__(self):
        pass 


    def read(self, path:str) -> int:
        '''
        download the file from dropbox
        '''
        try:
            self.dbx.download(path)
            return 0
        except Exception as e:
            print(e)
            return -1
        
    def write(self, path:int) -> int:
        '''
        upload the file to dropbox
        '''
        try:
            self.dbx.upload(path)
            return 0
        except Exception as e:
            print(e)
            return -1
        
    def listFolder(self, path:str) -> dict:
        '''
        list the folder in the dropbox
        '''
        try:
            return self.dbx.list_folder(path)
        except Exception as e:
            print(e)
            return None
    def getmetadata(self, path:str) -> dict:
        '''
        get the metadata of the file
        '''
        try:
            return self.dbx.getmetadata(path)
        except Exception as e:
            print(e)
            return None




if __name__ == "__main__":
    print("Hello World")