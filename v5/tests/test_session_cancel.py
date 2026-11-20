import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from schoolnet import macos_service as service

class SessionTests(unittest.TestCase):
    def test_expired_connection_cannot_start_after_a_delayed_authorization(self):
        session=str(int(time.time())-301)+'-'+'a'*32
        self.assertTrue(service.start_cancelled(501,session))
        with self.assertRaises(ValueError):service.start_cancelled(501,'invalid')

    @unittest.skipIf(os.name=='nt','Unix ownership marker')
    def test_only_the_requesting_user_can_cancel_the_session(self):
        session=str(int(time.time()))+'-'+'b'*32
        path=Path('/tmp')/f'.miner-cancel-{os.getuid()}-{session}'
        try:
            self.assertFalse(service.start_cancelled(os.getuid() or 501,session))
            path.write_text('cancel')
            if os.getuid()>0:self.assertTrue(service.start_cancelled(os.getuid(),session))
            with patch.object(Path,'lstat',return_value=type('Entry',(),{'st_mode':0o100600,'st_uid':9999})()):
                self.assertFalse(service.start_cancelled(501,session))
        finally:path.unlink(missing_ok=True)
