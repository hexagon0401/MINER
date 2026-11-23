import subprocess
import unittest
from unittest.mock import patch
from schoolnet import session_safety as s

class SessionSafetyTests(unittest.TestCase):
    def test_live_client_is_blocked_before_any_mode_change_without_killing_it(self):
        result=subprocess.CompletedProcess([],0,'/Applications/League of Legends.app/Contents/LoL/LeagueClient\n')
        with patch.object(s.platform,'system',return_value='Darwin'),patch.object(s.subprocess,'run',return_value=result) as command,self.assertRaisesRegex(ValueError,s.BLOCKED):s.require_clean_start()
        self.assertEqual(command.call_count,1);self.assertEqual(command.call_args.args[0],['/bin/ps','-A','-o','comm='])

    def test_background_riot_launcher_alone_does_not_block_start(self):
        result=subprocess.CompletedProcess([],0,'/Applications/RiotClientServices\n/Applications/MINER.app/Contents/MacOS/MINER\n')
        with patch.object(s.platform,'system',return_value='Darwin'),patch.object(s.subprocess,'run',return_value=result):
            self.assertFalse(s.require_clean_start()['league_client_open'])

    def test_game_is_identified_exactly_not_by_substring(self):
        result=subprocess.CompletedProcess([],0,'/Applications/Game/LeagueofLegends\n')
        with patch.object(s.platform,'system',return_value='Darwin'),patch.object(s.subprocess,'run',return_value=result),self.assertRaisesRegex(ValueError,'Finish the game'):s.require_clean_start()

    def test_inspection_failure_does_not_guess_a_clean_session(self):
        with patch.object(s.platform,'system',return_value='Darwin'),patch.object(s.subprocess,'run',side_effect=subprocess.TimeoutExpired('ps',4)),self.assertRaises(subprocess.TimeoutExpired):s.require_clean_start()

    def test_windows_unicode_process_list_uses_exact_client_names(self):
        with patch.object(s.platform,'system',return_value='Windows'),patch('windows.processes.names',return_value=['한글 앱.exe','LeagueClientUx.exe','RiotClientServices.exe']),patch.object(s.subprocess,'run') as shell:
            self.assertTrue(s.inspect()['league_client_open'])
            shell.assert_not_called()
    def test_native_windows_inspection_failure_does_not_guess_clean(self):
        with patch.object(s.platform,'system',return_value='Windows'),patch('windows.processes.names',side_effect=OSError('snapshot unavailable')),self.assertRaises(OSError):s.require_clean_start()
