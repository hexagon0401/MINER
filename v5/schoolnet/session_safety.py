"""Inspect exact game/client basenames before any routing mutation. Never kill apps."""
from pathlib import Path
import platform
import subprocess

BLOCKED='MINER_SESSION_BLOCKED'


def inspect():
    system=platform.system()
    if system=='Darwin':
        result=subprocess.run(['/bin/ps','-A','-o','comm='],check=True,capture_output=True,text=True,timeout=4)
        names=[Path(line.strip()).name for line in result.stdout.splitlines()]
    elif system=='Windows':
        from windows.processes import names as process_names
        names=process_names()
    else:return {'supported':False,'game_open':False,'league_client_open':False}
    normalized={name.casefold().removesuffix('.exe') for name in names if isinstance(name,str)}
    games={'leagueoflegends','league of legends'}
    clients={'leagueclient','leagueclientux','leagueclientuxrender','leagueclientux helper','leagueclientux helper (renderer)','leagueclientux helper (gpu)'}
    return {'supported':True,'game_open':bool(normalized&games),'league_client_open':bool(normalized&clients)}


def require_clean_start():
    state=inspect()
    if state['game_open']:
        raise ValueError(BLOCKED+': 게임 실행 중에는 연결 경로를 바꾸지 않습니다. 게임 종료 후 시작하세요. / Finish the game before starting MINER; no settings changed.')
    if state['league_client_open']:
        raise ValueError(BLOCKED+': LoL 클라이언트를 완전히 종료하고 MINER 연결 완료 후 다시 실행하세요. 기존 연결·DNS 캐시를 유지한 채 전환하지 않습니다. / Quit the LoL client, connect MINER, then reopen it; no settings changed.')
    return state
