import os
import gi
gi.require_version('Nemo', '3.0')
from gi.repository import Nemo, GObject
import pickle
import sys
sys.path.append('/home/tq22/SmartSync-Linux')
import importlib
src = importlib.import_module('src')

class CloudStatusExtension(GObject.GObject, Nemo.InfoProvider):
    def __init__(self):
        self.local_paths = []
        self.metadata_file_path = os.path.expanduser('~/Desktop/.config/metadata.pkl')
        self.target_dir_path = os.path.expanduser('~/Desktop/dropbox')
        self.load_local_paths()
    
    def load_local_paths(self):
        try:
            with open(self.metadata_file_path, 'rb') as f:
                tmp_paths = list(pickle.load(f).keys())
                self.local_paths = [s.lstrip('/') for s in tmp_paths]
                print(f"load_local_path_finish: {self.local_paths}")
        except Exception as e:
            self.local_paths = []
        
    def update_file_info(self, file):
        if file.get_uri_scheme() != 'file':
            return
        file_path = file.get_location().get_path()
        if file_path.startswith(self.target_dir_path):
            relative_path = os.path.relpath(file_path, self.target_dir_path)
            self.load_local_paths()
            print(f"currently updating: {relative_path}")
            if relative_path != '.':
                if relative_path in self.local_paths:
                    file.add_emblem('emblem-default')
                else:
                    file.add_emblem('emblem-web')
                print(f"emblem add finished")
