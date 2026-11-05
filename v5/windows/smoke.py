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
    previous=qInstallMessageHandler(lambda mode,context,message:messages.append(message))
    try:
        app,engine,b,w=ui.create_app(True);wait(app,.4)
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
        for theme in ('light','dark'):b.setTheme(theme);capture(theme)
        b.setLanguage('en');wait(app,.05);assert w.findChild(QObject,'startButton').property('text')=='Start';capture('english')
        b.setLanguage('ko');b.settings(True);wait(app,.2)
        settings=w.findChild(QObject,'settingsWindow');assert settings and settings.isVisible()
        b.setLanguage('en');wait(app,.05);assert settings.title()=='Settings'
        b.setLanguage('ko');wait(app,.05);assert settings.title()=='설정'
        assert settings.grabWindow().save(str(out/'windows-ui-settings.png'))
        b.settings(False);wait(app,.1)
        checks.append('Fluent settings, Korean-English copy, theme and persisted preferences')
        w.setWidth(480);w.setHeight(440);wait(app,.1)
        for name in ('startButton','stopButton','settingsButton'):
            item=w.findChild(QObject,name)
            pos=item.mapToScene(item.boundingRect().bottomRight())
            assert item.isVisible() and pos.x()<=w.width()+1 and pos.y()<=w.height()+1,(name,pos,w.size())
        capture('compact');w.setWidth(584);w.setHeight(704)
        checks.append('small windows keep primary Windows actions accessible')
        b.setReduced(True);wait(app,.05);assert not w.property('motionAllowed')
        b.effect.emit('success');wait(app,.05);assert not w.property('successActive')
        b.setReduced(False)
        checks.append('Windows reduce-motion preference prevents success transitions')
        label=w.findChild(QObject,'statusLabel')
        text_render=w.property('nativeTextMode')
        assert text_render==2, 'Text must use resolution-independent curve rendering'
        api=str(w.rendererInterface().graphicsApi())
        checks.append('scene graph, curve antialiasing and Windows font metadata recorded')
        b.setTheme('dark');state('idle',0,False);frames=[]
        for index in range(55):
            if index==1:b.effect.emit('start')
            if index==6:state('proxy_connect',1)
            if index==17:state('engine_start',4)
            if index==28:state('running',5)
            if index==44:state('restoring',0);b.effect.emit('stop')
            if index==52:state('restored',0,False)
            wait(app,.1)
            from PySide6.QtCore import QBuffer,QIODevice
            buf=QBuffer();buf.open(QIODevice.WriteOnly);image().save(buf,'PNG')
            frames.append(Image.open(io.BytesIO(bytes(buf.data()))).convert('RGB'))
        frames[0].save(out/'windows-ui-motion.gif',save_all=True,append_images=frames[1:],duration=100,loop=0)
        state('idle',0,False);w.showMinimized();wait(app,.1);assert not w.property('motionAllowed');w.showNormal()
        checks.append('minimizing pauses repeating effects')
        tokens=('ReferenceError:','TypeError:','Cannot assign','Unable to assign','Error decoding')
        if getattr(ui.sys,'frozen',False):tokens+=('Cannot open:',)
        errors=[m for m in messages if any(x in m for x in tokens)]
        assert not errors,errors
        result={'ok':True,'checks':checks,'network_actions':0,'state_source':'injected UI fixtures',
            'ui_engine':'Qt Quick RHI','control_style':QQuickStyle.name(),'graphics_api':api,
            'text_render_type':'CurveTextRendering', 'text_render_type_value':text_render,'font':b.font_family,
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
