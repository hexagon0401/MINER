"""Observe a session before a user-requested transition. Never kill game/apps."""
from pathlib import Path
import platform
import subprocess

BLOCKED='MINER_SESSION_BLOCKED'


def inspect():
    system=platform.system()
    if system=='Darwin':
        result=subprocess.run(['/bin/ps','-ww','-A','-o','comm='],check=True,capture_output=True,text=True,timeout=4)
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
    # Retain the shared entry point used by both desktops. The user permits
    # transitions during a match, accepting that the game may need to reconnect.
    # Existing sockets are not migrated and no reconnect success is implied.
    state=inspect()
    return {**state,'transition_notice':'GAME_RECONNECT_MAY_BE_REQUIRED' if state['game_open'] else None}
