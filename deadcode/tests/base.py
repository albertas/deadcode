from unittest import TestCase
from unittest.mock import MagicMock, patch


class BaseTestCase(TestCase):
    def patch(self, path: str) -> MagicMock:
        patcher = patch(path)
        self.addCleanup(patcher.stop)
        return patcher.start()
