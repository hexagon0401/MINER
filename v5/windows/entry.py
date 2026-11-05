"""Log startup/import failures before the graphical runtime exists."""
import ctypes
import os
from pathlib import Path
import sys
import traceback


def run():
    try:
        from windows.app import main
        return main()
    except BaseException:
        text=traceback.format_exc()
        test='--self-test' in sys.argv
        root=(Path(sys.argv[sys.argv.index('--self-test')+1]) if test else
              Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'MINER'/'Beta1')
        root.mkdir(parents=True,exist_ok=True)
        (root/'startup-error.log').write_text(text,encoding='utf-8')
        if not test and sys.platform=='win32':
            ctypes.windll.user32.MessageBoxW(None,'MINER could not start. / MINER를 시작할 수 없습니다.\n'+str(root/'startup-error.log'),'MINER',0x10)
        return 1


if __name__=='__main__':sys.exit(run())
