import os
import gi
gi.require_version('Nemo', '3.0')
from gi.repository import Nemo, GObject
import json
import pyinotify


class CloudStatusExtension(GObject.GObject, Nemo.InfoProvider):
    def __init__(self):
        self.local_paths = []
        self.json_file_path = '/home/tenki/Desktop/metadata.json'
        self.target_dir_path = os.path.expanduser('~/Desktop/dropbox')
        self.load_local_paths()
#        self.setup_inotify_watcher()
    
    def load_local_paths(self):
        try:
            with open(self.json_file_path, 'r') as f:
                self.local_paths = list(json.load(f).keys())
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

    def setup_inotify_watcher(self):
        wm = pyinotify.WatchManager()
        handler = OnWriteHandler(self)
        notifier = pyinotify.Notifier(wm, handler)
        wm.add_watch(self.json_file_path, pyinotify.IN_MODIFY)
        notifier.loop()

class OnWriteHandler(pyinotify.ProcessEvent):
    def __init__(self, extension):
        self.extension = extension

    def process_IN_MODIFY(self, event):
        self.extension.load_local_paths()
