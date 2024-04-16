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
