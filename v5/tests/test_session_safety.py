import subprocess
import contextlib
import io
import json
import unittest
from unittest.mock import patch
from schoolnet import session_safety as s

class SessionSafetyTests(unittest.TestCase):
    def test_live_client_can_start_without_killing_it(self):
        result=subprocess.CompletedProcess([],0,'/Applications/League of Legends.app/Contents/LoL/LeagueClient\n')
        with patch.object(s.platform,'system',return_value='Darwin'),patch.object(s.subprocess,'run',return_value=result) as command:
            state=s.require_clean_start()
        self.assertTrue(state['league_client_open']);self.assertFalse(state['game_open'])
        self.assertEqual(command.call_count,1);self.assertEqual(command.call_args.args[0],['/bin/ps','-ww','-A','-o','comm='])

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
            self.assertTrue(s.require_clean_start()['league_client_open'])
            shell.assert_not_called()

    def test_game_and_open_client_still_block_on_both_platforms(self):
        for system in ['Darwin','Windows']:
            with self.subTest(system=system),patch.object(s.platform,'system',return_value=system),patch.object(s.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'/long game path/LeagueClient\n/long game path/LeagueofLegends\n')),patch('windows.processes.names',return_value=['LeagueClientUx.exe','League of Legends.exe']),self.assertRaisesRegex(ValueError,'Finish the game'):
                s.require_clean_start()

    def test_cli_preflight_accepts_open_lobby_and_reports_it(self):
        import main
        output=io.StringIO()
        with patch.object(s,'inspect',return_value={'supported':True,'game_open':False,'league_client_open':True}),contextlib.redirect_stdout(output):
            self.assertEqual(main.main(['session-preflight']),0)
        self.assertTrue(json.loads(output.getvalue())['league_client_open'])

    def test_cli_preflight_blocks_active_match_before_any_warp_change(self):
        import main
        with patch.object(s,'inspect',return_value={'supported':True,'game_open':True,'league_client_open':True}),patch('schoolnet.warp.activate') as activate,contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(main.main(['session-preflight']),1)
        self.assertIn(s.BLOCKED,errors.getvalue());activate.assert_not_called()
    def test_native_windows_inspection_failure_does_not_guess_clean(self):
        with patch.object(s.platform,'system',return_value='Windows'),patch('windows.processes.names',side_effect=OSError('snapshot unavailable')),self.assertRaises(OSError):s.require_clean_start()
