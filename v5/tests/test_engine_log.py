import io
import json
from pathlib import Path
import tempfile
import unittest
from schoolnet.engine_log import EngineLog


class EngineLogTests(unittest.TestCase):
    def test_rotation_and_memory_are_bounded_without_raw_urls_or_addresses(self):
        line=b'ERROR outbound/socks[warp]: connection refused SECRET at https://login.riotgames.com/?token=PASSWORD from 192.168.1.123\n'
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'runtime.log';log=EngineLog(io.BytesIO(line*200),path,limit=4096);log.finish()
            for p in (path,path.with_name(path.name+'.previous')):
                self.assertTrue(p.exists());self.assertLessEqual(p.stat().st_size,4096)
                text=p.read_text()
                for secret in ('SECRET','PASSWORD','192.168.1.123','https://'):self.assertNotIn(secret,text)
                self.assertEqual(json.loads(text.splitlines()[0])['event'],'engine_error_categories')
