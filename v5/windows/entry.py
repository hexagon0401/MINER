"""Log startup/import failures before the graphical runtime exists."""
import ctypes
import os
from pathlib import Path
import sys
import traceback


def run():
    try:
        if '--dns-guard' in sys.argv:
            from schoolnet.dns_guard import run as guard
            index=sys.argv.index('--dns-guard')
            return guard(int(sys.argv[index+1]),int(sys.argv[index+2]),sys.argv[index+3])
        from windows.app import main
        return main()
    except BaseException:
        text=traceback.format_exc()
        test='--self-test' in sys.argv
        root=(Path(sys.argv[sys.argv.index('--self-test')+1]) if test else
              Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'MINER'/'Beta1')
        root.mkdir(parents=True,exist_ok=True)
        (root/'startup-error.log').write_text(text,encoding='utf-8')
        if not test and '--dns-guard' not in sys.argv and sys.platform=='win32':
            ctypes.windll.user32.MessageBoxW(None,'MINER could not start. / MINER를 시작할 수 없습니다.\n'+str(root/'startup-error.log'),'MINER',0x10)
        return 1


if __name__=='__main__':sys.exit(run())
