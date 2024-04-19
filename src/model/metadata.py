import uuid


class MetadataContainer:
    def __init__(self) -> None:
        self.path_to_id = {}
        self.id_metadata = {}
        pass

    def update_id(self, path, new_id):
        # update id of the given path
        if self.path_to_id.get(path, None) is None:
            raise KeyError(path)
        old_id = self.path_to_id[path]
        self.path_to_id[path] = new_id
        self.id_metadata[new_id] = self.id_metadata.pop(old_id)

    def update_path(self, old_path, new_path):
        # update path of the given id
        # if self.id_metadata.get(id, None) is None:
        #     raise KeyError(id)
        if self.path_to_id.get(old_path, None) is None:
            return
        id = self.path_to_id[old_path]
        self.path_to_id[new_path] = id
        self.id_metadata[id]["path"] = new_path
        del self.path_to_id[old_path]

    def __getitem__(self, path):
        if self.path_to_id.get(path, None) is None:
            raise KeyError(path)
        return self.id_metadata[self.path_to_id[path]]

    def __setitem__(self, path, value):
        if not isinstance(value, dict):
            raise TypeError(value)
        tmp_id = uuid.uuid4()
        if self.path_to_id.get(path, None) is None:
            self.path_to_id[path] = tmp_id
        else:
            tmp_id = self.path_to_id[path]
        self.id_metadata[tmp_id] = value

    def __delitem__(self, path):
        id = self.path_to_id[path]
        del self.path_to_id[path]
        del self.id_metadata[id]

    def __contains__(self, path):
        return path in self.path_to_id

    def __len__(self):
        return len(self.path_to_id)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.path_to_id}, {self.id_metadata})"

    def __str__(self) -> str:
        return f"{self.path_to_id}, {self.id_metadata}"

    def items(self):
        return [(path, self.id_metadata[id]) for path, id in self.path_to_id.items()]

    def pop(self, path):
        if self.path_to_id.get(path, None) is None:
            return None
        id = self.path_to_id[path]
        del self.path_to_id[path]
        return self.id_metadata.pop(id)

    def get(self, path, default=None):
        if self.path_to_id.get(path, None) is None:
            return default
        return self.id_metadata[self.path_to_id[path]]

    def keys(self):
        return self.path_to_id.keys()
