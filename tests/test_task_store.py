import unittest

from task_store import TaskStore


class TaskStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = TaskStore()

    def test_create_and_list(self):
        created = self.store.create_task("Write Jenkinsfile")
        self.assertEqual(created["id"], 1)
        self.assertFalse(created["completed"])
        self.assertEqual(self.store.list_tasks(), [created])

    def test_update(self):
        task = self.store.create_task("Old title")
        updated = self.store.update_task(task["id"], title="New title", completed=True)
        self.assertEqual(updated["title"], "New title")
        self.assertTrue(updated["completed"])

    def test_delete(self):
        task = self.store.create_task("Delete me")
        deleted = self.store.delete_task(task["id"])
        self.assertEqual(deleted["id"], task["id"])
        self.assertEqual(self.store.list_tasks(), [])

    def test_rejects_blank_title(self):
        with self.assertRaises(ValueError):
            self.store.create_task("   ")

    def test_missing_task_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.store.get_task(99)


if __name__ == "__main__":
    unittest.main()
