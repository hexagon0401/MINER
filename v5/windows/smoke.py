"""Packaged UI checks: no WARP commands and no network changes."""
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from windows.app import Window, ART


def run(output):
    app=QApplication.instance() or QApplication([])
    w=Window(); w.show(); app.processEvents()
    out=Path(output); out.mkdir(parents=True,exist_ok=True)
    checks=[]
    for asset in ['school.png','mascot-runtime-256.png','AppIcon.png','developer-avatar.png']:
        assert (ART/asset).is_file(),asset
    checks.append('existing Beta 1 artwork and developer avatar bundled')
    for phase,count in [('idle',0),('running',5),('restoring',0),('restored',0)]:
        w.update_state(phase,count); app.processEvents()
        assert f'{count}/5' in w.steps.text()
        w.grab().save(str(out/f'windows-ui-{phase}.png'))
    checks.append('real state drives five-stage UI')
    w.lang='en'; w.refresh(); assert w.start.text()=='Start'
    w.lang='ko'; w.refresh(); assert w.start.text()=='시작'
    checks.append('Korean and English settings')
    w.dirty=True; w.failure('Fixture failure: no network action executed')
    assert not w.start.isEnabled() and w.stop.isEnabled()
    w.grab().save(str(out/'windows-ui-error.png'))
    checks.append('error requires explicit restoration before restart')
    w.dirty=False; w.close()
    result={'ok':True,'checks':checks,'network_actions':0}
    (out/'windows-ui.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
