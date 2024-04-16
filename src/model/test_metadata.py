import unittest
from metadata import MetadataContainer


class TestMetadataContainer(unittest.TestCase):

    def setUp(self):
        self.container = MetadataContainer()

    def test_update_id(self):
        # Test updating id of an existing path
        path = "/path/to/file.txt"
        old_id = "old_id"
        new_id = "new_id"
        metadata = {"name": "file.txt", "size": 100}
        self.container.path_to_id[path] = old_id
        self.container.id_metadata[old_id] = metadata

        self.container.update_id(path, new_id)

        self.assertEqual(self.container.path_to_id[path], new_id)
        self.assertEqual(self.container.id_metadata[new_id], metadata)

    def test_update_id_nonexistent_path(self):
        # Test updating id of a nonexistent path
        path = "/path/to/nonexistent.txt"
        new_id = "new_id"

        with self.assertRaises(KeyError):
            self.container.update_id(path, new_id)

    def test_getitem(self):
        # Test getting metadata of an existing path
        path = "/path/to/file.txt"
        metadata = {"name": "file.txt", "size": 100}
        self.container.path_to_id[path] = "id"
        self.container.id_metadata["id"] = metadata

        result = self.container[path]

        self.assertEqual(result, metadata)

    def test_getitem_nonexistent_path(self):
        # Test getting metadata of a nonexistent path
        path = "/path/to/nonexistent.txt"

        with self.assertRaises(KeyError):
            self.container[path]

    def test_setitem(self):
        # Test setting metadata for a new path
        path = "/path/to/new_file.txt"
        metadata = {"name": "new_file.txt", "size": 200}

        self.container[path] = metadata

        self.assertEqual(
            self.container.path_to_id[path], list(self.container.id_metadata.keys())[0]
        )
        self.assertEqual(
            self.container.id_metadata[self.container.path_to_id[path]], metadata
        )

    def test_setitem_existing_path(self):
        # Test setting metadata for an existing path
        path = "/path/to/file.txt"
        old_id = "old_id"
        new_id = "new_id"
        old_metadata = {"name": "file.txt", "size": 100}
        new_metadata = {"name": "file.txt", "size": 150}
        self.container.path_to_id[path] = old_id
        self.container.id_metadata[old_id] = old_metadata

        self.container[path] = new_metadata

        self.assertEqual(self.container.path_to_id[path], old_id)
        self.assertEqual(self.container.id_metadata[old_id], new_metadata)

    def test_setitem_invalid_value(self):
        # Test setting metadata with an invalid value
        path = "/path/to/file.txt"
        invalid_metadata = "invalid_metadata"

        with self.assertRaises(TypeError):
            self.container[path] = invalid_metadata

    def test_delitem(self):
        # Test deleting metadata of an existing path
        path = "/path/to/file.txt"
        id = "id"
        metadata = {"name": "file.txt", "size": 100}
        self.container.path_to_id[path] = id
        self.container.id_metadata[id] = metadata

        del self.container[path]

        self.assertNotIn(path, self.container.path_to_id)
        self.assertNotIn(id, self.container.id_metadata)

    def test_delitem_nonexistent_path(self):
        # Test deleting metadata of a nonexistent path
        path = "/path/to/nonexistent.txt"

        with self.assertRaises(KeyError):
            del self.container[path]

    def test_items(self):
        # Test retrieving items from the container
        path1 = "/path/to/file1.txt"
        path2 = "/path/to/file2.txt"
        metadata1 = {"name": "file1.txt", "size": 100}
        metadata2 = {"name": "file2.txt", "size": 200}
        self.container.path_to_id[path1] = "id1"
        self.container.path_to_id[path2] = "id2"
        self.container.id_metadata["id1"] = metadata1
        self.container.id_metadata["id2"] = metadata2

        result = self.container.items()

        self.assertEqual(result, [(path1, metadata1), (path2, metadata2)])

    def test_pop(self):
        # Test popping metadata of an existing path
        path = "/path/to/file.txt"
        id = "id"
        metadata = {"name": "file.txt", "size": 100}
        self.container.path_to_id[path] = id
        self.container.id_metadata[id] = metadata

        result = self.container.pop(path)

        self.assertNotIn(path, self.container.path_to_id)
        self.assertNotIn(id, self.container.id_metadata)
        self.assertEqual(result, metadata)

    def test_pop_nonexistent_path(self):
        # Test popping metadata of a nonexistent path
        path = "/path/to/nonexistent.txt"

        result = self.container.pop(path)

        self.assertIsNone(result)

    def test_get(self):
        # Test getting metadata of an existing path with default value
        path = "/path/to/file.txt"
        metadata = {"name": "file.txt", "size": 100}
        self.container.path_to_id[path] = "id"
        self.container.id_metadata["id"] = metadata

        result = self.container.get(path, default=None)

        self.assertEqual(result, metadata)

    def test_get_nonexistent_path(self):
        # Test getting metadata of a nonexistent path with default value
        path = "/path/to/nonexistent.txt"
        default = {"name": "default.txt", "size": 0}

        result = self.container.get(path, default=default)

        self.assertEqual(result, default)

    def test_keys(self):
        # Test retrieving keys from the container
        path1 = "/path/to/file1.txt"
        path2 = "/path/to/file2.txt"
        metadata1 = {"name": "file1.txt", "size": 100}
        metadata2 = {"name": "file2.txt", "size": 200}
        self.container.path_to_id[path1] = "id1"
        self.container.path_to_id[path2] = "id2"
        self.container.id_metadata["id1"] = metadata1
        self.container.id_metadata["id2"] = metadata2

        result = self.container.keys()

        self.assertEqual(result, {path1, path2})


if __name__ == "__main__":
    unittest.main()
