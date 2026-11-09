"""Actual Qt Quick EXE captures; network states are explicitly injected fixtures."""
import io
import json
import os
from pathlib import Path
import time

from PIL import Image
from PySide6.QtCore import QObject, qInstallMessageHandler
from PySide6.QtQuickControls2 import QQuickStyle
import windows.app as ui


def wait(app,seconds):
    until=time.monotonic()+seconds
    while time.monotonic()<until:app.processEvents();time.sleep(.01)


def run(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    ui.DATA=out/'test-profile';ui.DATA.mkdir(exist_ok=True)
    messages=[]
    def record(mode,context,message):
        messages.append(message)
        with (out/'qml-renderer.log').open('a',encoding='utf-8') as f:f.write(message+'\n')
    previous=qInstallMessageHandler(record)
    try:
        app,engine,b,w=ui.create_app(True);w.requestActivate();wait(app,.4)
        assert w.isVisible()
        assert w.findChild(QObject,'startButton') is not None
        checks=[]
        def image():
            shot=w.grabWindow()
            assert not shot.isNull(),'Qt Quick scene graph produced no image'
            return shot
        def capture(name):
            wait(app,.08);assert image().save(str(out/f'windows-ui-{name}.png'))
        def state(phase,count,dirty=True):
            b.dirty=dirty;b.fixture_busy=phase in ('proxy_connect','engine_start');b.update_state(phase,count);wait(app,.08)
            assert w.findChild(QObject,'progressLabel').property('text')==f'{count}/5'
        for phase,count in [('idle',0),('proxy_connect',1),('running',5),('restoring',0),('restored',0)]:
            state(phase,count,phase not in ('idle','restored'));capture(phase)
        checks.append('real Qt Quick scene renders all backend states without network actions')
        b.dirty=True;b.failure('Fixture: proxy verification failed. '+('Long diagnostic. '*15));capture('error')
        assert not w.findChild(QObject,'startButton').property('enabled')
        assert w.findChild(QObject,'stopButton').property('enabled')
        checks.append('errors gate restart and preserve explicit restoration')
        state('idle',0,False)
        assert b.state['theme']=='pearl' and b.state['controlLayout']=='rounded'
        logo=w.findChild(QObject,'pearlWordmark')
        center=logo.mapToScene(logo.boundingRect().center())
        assert abs(center.x()-w.width()/2)<2, 'Wordmark must be centered'
        stop_button=w.findChild(QObject,'stopButton');kill_button=w.findChild(QObject,'killButton')
        assert abs(stop_button.width()-kill_button.width())<2, 'STOP and KILL must have equal widths'
        start=w.findChild(QObject,'startButton')
        pos=start.mapToScene(start.boundingRect().topLeft());img=image();ratio=img.width()/w.width()
        pixel=img.pixelColor(int((pos.x()+16)*ratio),int((pos.y()+16)*ratio))
        assert pixel.green()>140 and pixel.red()<130, 'START gradient must actually render'
        for layout in ('rounded','flush'):
            b.setLayout(layout);capture(layout)
            assert w.property('flush')==(layout=='flush')
        b.setLayout('rounded');capture('pearl')
        checks.append('Pearl White A/B layouts, centered supplied logo, green button and equal action widths')
        b.setLanguage('en');wait(app,.05);assert w.findChild(QObject,'startButton').property('text')=='START';capture('english')
        b.setLanguage('ko');b.settings(True);wait(app,.2)
        settings=w.findChild(QObject,'settingsWindow');assert settings and settings.isVisible()
        b.setLanguage('en');wait(app,.05);assert settings.title()=='Settings'
        b.setLanguage('ko');wait(app,.05);assert settings.title()=='설정'
        assert settings.grabWindow().save(str(out/'windows-ui-settings.png'))
        b.settings(False);wait(app,.1)
        checks.append('Fluent settings, Korean-English copy, theme and persisted preferences')
        b.update_info={'available':True,'version':'99.0.0'};b.changed.emit();capture('update-available')
        assert b.state['updateAvailable'] and b.state['autoUpdates']
        b.update_info=None;b.update_busy=True
        assert b.state['canStart'],'Background version checks must not block connection controls'
        b.update_busy=False;b.changed.emit()
        checks.append('automatic update preference and available-version banner render without network actions')
        w.setWidth(480);w.setHeight(440);wait(app,.1)
        for name in ('startButton','stopButton','killButton','settingsButton'):
            item=w.findChild(QObject,name)
            pos=item.mapToScene(item.boundingRect().bottomRight())
            assert item.isVisible() and pos.x()<=w.width()+1 and pos.y()<=w.height()+1,(name,pos,w.size())
        capture('compact');w.setWidth(560);w.setHeight(680)
        checks.append('small windows keep primary Windows actions accessible')
        b.setReduced(True);wait(app,.05);assert not w.property('motionAllowed')
        b.effect.emit('success');wait(app,.05);assert not w.property('successActive')
        b.setReduced(False)
        assert not w.property('motionAllowed'), 'Supplied Pearl White hero must remain static'
        checks.append('static supplied mascot and no digging or progress timers')
        # Exercise the UI's late-Kill race without any worker or CLI executing.
        import threading
        from unittest.mock import patch
        class FakeSignal:
            def connect(self,*a):pass
        class FakeWorker:
            def __init__(self,restore=False):
                self.stop_event=threading.Event();self.emergency_event=threading.Event()
                self.progress=FakeSignal();self.failed=FakeSignal();self.finished=FakeSignal();self.running=False
            def start(self):self.running=True
            def isRunning(self):return self.running
        with patch.object(ui,'Worker',FakeWorker):
            b.testing=False;b.dirty=True;b.phase='restoring';b.worker=FakeWorker();b.worker.running=True
            original=b.worker;b.kill()
            assert original.stop_event.is_set() and original.emergency_event.is_set()
            original.running=False;b.update_state('restored',0)
            assert b.dirty and b.phase=='disconnecting' and b.pending_kill
            b.finished();assert b.worker is not original and b.worker.emergency_event.is_set()
            b.update_state('disconnected',0);b.worker.running=False;b.finished()
            assert not b.dirty and not b.pending_kill and b.state['canStart']
            b.testing=True;b.worker=None
        checks.append('late Kill during Stop queues one explicit disconnect; no false WARP-off claim')
        b.changed.emit();state('disconnected',0,False);capture('disconnected')
        label=w.findChild(QObject,'statusLabel')
        text_render=w.property('nativeTextMode')
        assert text_render==0, 'Body text must use distance-field antialiasing'
        api=str(w.rendererInterface().graphicsApi())
        checks.append('scene graph, text antialiasing and language-specific Windows fonts recorded')
        b.setLayout('rounded');state('idle',0,False);frames=[]
        # Static concept: a short state walkthrough, not a new mining animation.
        storyboard=[('idle',0),('proxy_connect',1),('engine_start',4),('running',5),('restoring',0),('restored',0),('disconnecting',0),('disconnected',0)]
        capture_walkthrough=not (out.name.startswith('scale-') or out.name=='installed')
        for phase,count in (storyboard if capture_walkthrough else storyboard[:1]):
            state(phase,count,phase not in ('idle','restored','disconnected'));wait(app,.08)
            from PySide6.QtCore import QBuffer,QIODevice
            buf=QBuffer();buf.open(QIODevice.WriteOnly);image().save(buf,'PNG')
            frames.append(Image.open(io.BytesIO(bytes(buf.data()))).convert('RGB'))
        frames[0].save(out/'windows-ui-motion.gif',save_all=True,append_images=frames[1:],duration=700,loop=0)
        state('idle',0,False);w.showMinimized();wait(app,.1);assert not w.property('motionAllowed');w.showNormal()
        checks.append('minimizing preserves the static, timer-free Pearl White scene')
        tokens=('ReferenceError:','TypeError:','Cannot assign','Unable to assign','Error decoding')
        if getattr(ui.sys,'frozen',False):tokens+=('Cannot open:',)
        errors=[m for m in messages if any(x in m for x in tokens)]
        assert not errors,errors
        result={'ok':True,'checks':checks,'network_actions':0,'state_source':'injected UI fixtures',
            'theme':'Pearl White','default_controls':'A rounded floating','fallback_controls':'B flush integrated',
            'kill_switch':'Stop owned engine then disconnect WARP; regular internet retained',
            'animation_preference_overridden_for_capture':False,
            'software_adapter_preferred':os.environ.get('QSG_RHI_PREFER_SOFTWARE_RENDERER')=='1',
            'capture_render_loop':os.environ.get('QSG_RENDER_LOOP','default'),
            'foreground_override_for_capture':False,
            'floating_shadows_active':b.state['effectsSupported'],
            'ui_engine':'Qt Quick RHI','control_style':QQuickStyle.name(),'graphics_api':api,
            'text_render_type':'QtTextRendering (high-quality distance fields)', 'text_render_type_value':text_render,'font':b.state['fontFamily'],
            'scale_factor':os.environ.get('QT_SCALE_FACTOR','system')}
        (out/'windows-ui.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        (out/'qml-renderer.log').write_text('\n'.join(messages),encoding='utf-8')
        b.dirty=False;w.close()
        import shiboken6
        shiboken6.delete(w);shiboken6.delete(engine);app.processEvents()
        return result
    finally:
        (out/'qml-renderer.log').write_text('\n'.join(messages),encoding='utf-8')
        qInstallMessageHandler(previous)
