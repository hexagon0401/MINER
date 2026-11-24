"""Exercise packaged preflight with inert client/game processes, never real LoL."""
import json
from pathlib import Path
import subprocess
import time


def run(cli, output):
    output = Path(output) / 'live-client-preflight'
    output.mkdir(parents=True)
    source = output / 'idle.c'
    source.write_text('#include <stdio.h>\n#include <unistd.h>\n'
                      'int main(int argc,char **argv){if(argc!=2)return 2;'
                      'FILE *f=fopen(argv[1],"w");if(!f)return 3;'
                      'fputs("ready",f);fclose(f);for(;;)pause();}\n')
    children = []

    def start(name):
        folder = output / ('Long path with spaces ' * 6) / name
        folder.mkdir(parents=True)
        executable = folder / name
        subprocess.run(['xcrun', 'clang', str(source), '-o', str(executable)], check=True, timeout=30)
        subprocess.run(['codesign', '--force', '--sign', '-', str(executable)], check=True, timeout=10)
        ready = folder / 'ready'
        child = subprocess.Popen([str(executable), str(ready)])
        children.append(child)
        deadline = time.monotonic() + 5
        while not ready.exists():
            if child.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError('Inert process fixture did not start')
            time.sleep(.05)

    try:
        start('LeagueClient')
        client = subprocess.run([str(cli), 'session-preflight'], capture_output=True, text=True, timeout=10)
        assert client.returncode == 0, client.stderr
        state = json.loads(client.stdout)
        assert state['supported'] and state['league_client_open'] and not state['game_open']
        assert children[0].poll() is None, 'Client fixture was terminated'
        start('LeagueofLegends')
        game = subprocess.run([str(cli), 'session-preflight'], capture_output=True, text=True, timeout=10)
        assert game.returncode == 0, game.stderr
        game_state = json.loads(game.stdout)
        assert game_state['game_open'] and game_state['transition_notice'] == 'GAME_RECONNECT_MAY_BE_REQUIRED'
        assert all(child.poll() is None for child in children), 'Preflight terminated another process'
        report = {'ok': True, 'packaged_cli': True, 'inert_process_fixtures': True,
                  'live_client_allowed': True, 'active_game_allowed': True,
                  'reconnect_notice_reported': True,
                  'long_paths_with_spaces': True, 'client_not_terminated': True,
                  'routing_or_warp_commands_requested': False, 'real_lol_tested': False}
        (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
        return report
    finally:
        # Only processes created by this fixture are stopped.
        for child in children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
