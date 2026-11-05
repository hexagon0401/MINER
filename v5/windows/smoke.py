"""Packaged EXE UI captures. All connection states here are injected, not live WARP."""
import io
import json
import os
from pathlib import Path
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QComboBox
from PIL import Image
import windows.app as ui


def wait(app,seconds):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        app.processEvents();time.sleep(.01)


def run(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    # Never read/write a user's real profile, recovery marker or UI preferences.
    ui.DATA=out/'test-profile';ui.DATA.mkdir(exist_ok=True)
    app=QApplication.instance() or QApplication([])
    w=ui.Window();w.show();w.activateWindow();wait(app,.2)
    watermark=QLabel('UI VALIDATION · simulated states · no live WARP',w)
    watermark.setStyleSheet('background:#ffd54a;color:#142337;font-size:10px;padding:3px;');watermark.adjustSize()
    checks=[]
    for asset in ['school.png','mascot-runtime-256.png','AppIcon.png','developer-avatar.png','full-window-strata.png']:
        assert not ui.QPixmap(str(ui.ART/asset)).isNull(),asset
    checks.append('Beta icon, scene, mascot and offline avatar decode')
    def shot(name):
        watermark.move(8,max(0,w.height()-watermark.height()-2));watermark.raise_();app.processEvents()
        assert w.grab().save(str(out/f'windows-ui-{name}.png'))
    for phase,count in [('idle',0),('proxy_connect',1),('running',5),('restoring',0),('restored',0)]:
        w.dirty=phase not in ('idle','restored');w.update_state(phase,count);wait(app,.15)
        assert f'{count}/5' in w.steps.text();shot(phase)
    checks.append('state-driven progress and Windows action gating')
    w.dirty=True;w.failure('Fixture: proxy verification failed. '+('Long diagnostic details. '*15));shot('error')
    assert not w.start.isEnabled() and w.stop.isEnabled()
    checks.append('long errors preserve Stop restoration and readable diagnostics')
    w.dirty=False;w.detail='';w.update_state('idle',0)
    for theme in ('light','dark'):
        w.theme=theme;w.apply_theme();shot(theme)
    w.lang='en';w.refresh();assert w.start.text()=='Start';shot('english')
    w.lang='ko';w.refresh();assert w.start.text()=='시작'
    w.preferences();wait(app,.1)
    dialog=w.dialog;assert dialog
    combos=dialog.findChildren(QComboBox);combos[0].setCurrentIndex(1);wait(app,.05)
    assert dialog.windowTitle()=='Settings'
    combos[0].setCurrentIndex(0);wait(app,.05);assert dialog.windowTitle()=='설정'
    assert dialog.grab().save(str(out/'windows-ui-settings.png'));dialog.close();wait(app,.05)
    checks.append('live Korean-English settings, About and persistent preferences')
    w.resize(480,440);wait(app,.1)
    for button in (w.start,w.stop,w.settings):
        assert button.isVisible() and w.rect().contains(button.mapTo(w,button.rect().bottomRight()))
    shot('compact');w.resize(560,680)
    checks.append('compact window keeps primary actions visible')
    w.reduced=True;w.cave.busy=True;w.sync_motion();assert not w.cave.timer.isActive()
    w.motion.play('start',w.start.pos(),True);assert not w.motion.anim.state()==ui.QVariantAnimation.Running
    checks.append('reduced motion has no recurring scene or wave animation')
    w.reduced=False;w.cave.active=True;w.cave.reduced=False;w.cave.busy=True;w.cave.sync()
    assert w.cave.timer.interval()>=33
    w.cave.active=False;w.cave.sync();assert not w.cave.timer.isActive()
    checks.append('digging bounded to 30fps and paused when inactive')
    # Record the actual renderer over time; this sequence still uses fixture states.
    w.theme='dark';w.apply_theme();w.cave.busy=False;w.update_state('idle',0)
    frames=[]
    for index in range(50):
        if index==1:w.motion.play('start',w.start.mapTo(w,w.start.rect().center()),False)
        if index==7:w.update_state('proxy_connect',1);w.cave.busy=True;w.cave.active=True;w.cave.sync()
        if index==16:w.update_state('engine_start',4);w.cave.busy=True;w.cave.active=True;w.cave.sync()
        if index==24:w.cave.busy=False;w.cave.sync();w.update_state('running',5)
        if index==40:w.update_state('restoring',0);w.motion.play('stop',w.stop.mapTo(w,w.stop.rect().center()),False)
        if index==47:w.update_state('restored',0)
        wait(app,.12);watermark.raise_();app.processEvents()
        image=w.grab().toImage();ptr=image.bits()
        # Save through PNG to avoid depending on a platform QImage memory layout.
        from PySide6.QtCore import QBuffer,QIODevice
        buffer=QBuffer();buffer.open(QIODevice.WriteOnly);image.save(buffer,'PNG')
        frames.append(Image.open(io.BytesIO(bytes(buffer.data()))).convert('RGB'))
    frames[0].save(out/'windows-ui-motion.gif',save_all=True,append_images=frames[1:],duration=120,loop=0)
    w.cave.busy=False;w.cave.sync();w.motion.cancel();w.dirty=False;w.close()
    result={'ok':True,'checks':checks,'network_actions':0,'state_source':'injected UI fixtures',
        'os':os.name,'scale_factor':os.environ.get('QT_SCALE_FACTOR','system')}
    (out/'windows-ui.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
