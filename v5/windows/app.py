"""Windows Qt Quick / Fluent frontend, isolated from the networking controller."""
import ctypes
import json
import os
from pathlib import Path
import sys
import threading
import webbrowser

from PySide6.QtCore import QObject, Property, QThread, Signal, Slot, QUrl, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QFont, QFontDatabase, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
from PySide6.QtQuickControls2 import QQuickStyle
from windows.controller import session
from windows.platform_ui import WORDS, windows_appearance
from windows.version import LABEL

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
ART=ROOT/'art'
if not ART.exists(): ART=ROOT/'macos/design/assets'
DATA=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'MINER'/'Beta1'


class Worker(QThread):
    progress=Signal(str,int);failed=Signal(str)
    def __init__(self,restore=False):
        super().__init__();self.stop_event=threading.Event();self.emergency_event=threading.Event();self.restore=restore
    def run(self):
        try:session(DATA,ROOT/'engine/sing-box.exe',self.stop_event,lambda p,c:self.progress.emit(p,c),self.restore,self.emergency_event)
        except Exception as exc:self.failed.emit(str(exc))


class UpdateWorker(QObject):
    completed=Signal(object); failed=Signal(str); finished=Signal()
    def __init__(self,info=None):
        super().__init__();self.info=info;self.cancelled=threading.Event()
    def start(self):threading.Thread(target=self.run,daemon=True,name="MINER update").start()
    def run(self):
        try:
            from schoolnet import updates
            result=updates.download(self.info,DATA/'Updates') if self.info else updates.check('windows','x64')
            if not self.cancelled.is_set():self.completed.emit(result)
        except Exception as exc:
            if not self.cancelled.is_set():self.failed.emit(str(exc))
        finally:
            if not self.cancelled.is_set():self.finished.emit()


class Bridge(QObject):
    changed=Signal();effect=Signal(str);closeRequested=Signal()
    def __init__(self,testing=False):
        super().__init__();self.testing=testing;self.worker=None;self.closing=False;self.detail='';self.count=0
        self.settings_open=False;self.fixture_busy=False;self.pending_kill=False;self.effects_supported=False
        self.update_worker=None;self.update_busy=False;self.installing_update=False;self.update_message='';self.update_info=None;self.pending_installer=None
        DATA.mkdir(parents=True,exist_ok=True)
        try:
            cfg=json.loads((DATA/'settings.json').read_text(encoding='utf-8'))
            if not isinstance(cfg,dict):cfg={}
        except (OSError,ValueError):cfg={}
        language=cfg.get('language');theme=cfg.get('theme')
        self.language=language if isinstance(language,str) and language in WORDS else 'ko'
        self.theme='pearl'
        layout=cfg.get('control_layout')
        self.control_layout=layout if layout in ('rounded','flush') else 'rounded'
        self.reduced=cfg.get('reduce_motion') is True
        self.auto_updates=cfg.get('auto_updates',True) is not False
        self.appearance=windows_appearance();self.dirty=(DATA/'session.json').exists()
        self.phase='interrupted' if self.dirty else 'idle'
        available=QFontDatabase.families()
        self.font_family=next((x for x in ('Segoe UI Variable Text','Segoe UI','Noto Sans') if x in available),QGuiApplication.font().family())
        self.korean_font=next((x for x in ('Malgun Gothic','맑은 고딕','Noto Sans CJK KR') if x in available),self.font_family)
        QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _:self.changed.emit())

    @Property('QVariantMap',notify=changed)
    def state(self):
        active=bool(self.worker and self.worker.isRunning())
        system_dark=QGuiApplication.styleHints().colorScheme()==Qt.ColorScheme.Dark
        return {'text':WORDS[self.language],'language':self.language,'theme':self.theme,
            'dark':False,'controlLayout':self.control_layout,'effectsSupported':self.effects_supported,
            'reduced':self.reduced or self.appearance['reduced'],'systemReduced':self.appearance['reduced'],
            'contrast':self.appearance['contrast'],'phase':self.phase,'completed':self.count,
            'detail':self.detail,'canStart':not self.dirty and not active and not self.installing_update,
            'canStop':self.dirty and self.phase not in ('restoring','disconnecting'),
            'canKill':self.phase not in ('disconnecting','disconnected'),
            'busy':(active or self.fixture_busy) and self.phase not in ('running','restoring','disconnecting','error','restored','disconnected'),
            'settingsOpen':self.settings_open,'latinFontFamily':self.font_family,'fontFamily':self.korean_font if self.language=='ko' else self.font_family,'version':LABEL,
            'art':QUrl.fromLocalFile(str(ART.resolve())+os.sep).toString(),
            'pearlArt':QUrl.fromLocalFile(str((ART/'pearl' if (ART/'pearl').exists() else ROOT/'windows/pearl').resolve())+os.sep).toString(),
            'validation':self.testing,'updateBusy':self.update_busy,'updateMessage':self.update_message,
            'updateAvailable':bool(self.update_info and self.update_info.get('available')),
            'autoUpdates':self.auto_updates,'updateVersion':self.update_info.get('version','') if self.update_info else ''}

    def save(self):
        from schoolnet.runtime import write_json
        try:write_json(DATA/'settings.json',{'language':self.language,'theme':self.theme,'reduce_motion':self.reduced,'control_layout':self.control_layout,'auto_updates':self.auto_updates})
        except (OSError,ValueError) as exc:self.detail=str(exc)
        self.changed.emit()

    @Slot()
    def begin(self):
        if not self.state['canStart'] or self.testing:return
        self.dirty=True;self.detail='';self.phase='cli_check';self.count=0;self.effect.emit('start');self.launch(False)
    def launch(self,restore):
        if self.worker and self.worker.isRunning():return
        self.worker=Worker(restore);self.worker.progress.connect(self.update_state)
        self.worker.failed.connect(self.failure);self.worker.finished.connect(self.finished)
        self.worker.start();self.changed.emit()
    def update_state(self,phase,count):
        if self.worker and self.worker.stop_event.is_set() and phase not in ('restored','disconnected'):
            phase='disconnecting' if self.worker.emergency_event.is_set() else 'restoring';count=0
        previous=self.phase;self.detail='';self.phase=phase;self.count=count
        if phase=='disconnected':self.dirty=False;self.pending_kill=False
        elif phase=='restored':
            if self.pending_kill:self.phase='disconnecting'
            else:self.dirty=False
        self.changed.emit()
        if phase=='running' and previous!='running':self.effect.emit('success')
    def failure(self,message):
        self.detail=message;self.phase='error';self.pending_kill=False;self.closing=False;self.changed.emit();self.effect.emit('cancel')
    def finished(self):
        if self.worker and self.worker.isRunning():return
        if self.pending_kill:
            self.launch_kill();return
        self.changed.emit()
        if self.closing and not self.dirty:self.closeRequested.emit()
    @Slot()
    def end(self):
        if not self.dirty or self.testing:return
        self.phase='restoring';self.effect.emit('stop')
        if self.worker and self.worker.isRunning():self.worker.stop_event.set();self.changed.emit()
        else:self.launch(True)
    @Slot(result=bool)
    def requestClose(self):
        if self.testing:return True
        if self.installing_update:return False
        if self.dirty or (self.worker and self.worker.isRunning()):
            self.closing=True
            if self.phase not in ('restoring','disconnecting'):self.end()
            return False
        return True
    @Slot(str)
    def setLanguage(self,value):
        if value in WORDS:
            self.language=value
            font=QGuiApplication.font();font.setFamily(self.state['fontFamily']);QGuiApplication.setFont(font)
            self.save()
    def apply_appearance(self):
        hints=QGuiApplication.styleHints()
        scheme=Qt.ColorScheme.Unknown if self.appearance['contrast'] else Qt.ColorScheme.Light
        hints.setColorScheme(scheme)
        if sys.platform=='win32' and hasattr(self,'window'):
            try:
                dark=ctypes.c_int(int(self.state['dark']))
                fn=ctypes.windll.dwmapi.DwmSetWindowAttribute
                fn.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint]
                fn(int(self.window.winId()),20,ctypes.byref(dark),ctypes.sizeof(dark))
                for attribute,value in ((33,2),(35,0x00FFF8F6),(34,0x00E9D8D0)):
                    v=ctypes.c_int(-1 if self.appearance["contrast"] and attribute in (34,35) else value);fn(int(self.window.winId()),attribute,ctypes.byref(v),ctypes.sizeof(v))
            except (AttributeError,OSError):pass

    @Slot(str)
    def setTheme(self,value):
        if value=='pearl':self.theme=value;self.apply_appearance();self.save()
    @Slot(str)
    def setLayout(self,value):
        if value in ('rounded','flush'):self.control_layout=value;self.save()

    @Slot()
    def kill(self):
        if not self.state['canKill'] or self.testing:return
        self.dirty=True;self.pending_kill=True;self.phase='disconnecting';self.changed.emit()
        if self.worker and self.worker.isRunning():
            self.worker.emergency_event.set();self.worker.stop_event.set()
        else:self.launch_kill()

    def launch_kill(self):
        self.worker=Worker(True);self.worker.emergency_event.set()
        self.worker.progress.connect(self.update_state);self.worker.failed.connect(self.failure);self.worker.finished.connect(self.finished)
        self.worker.start();self.changed.emit()

    @Slot(bool)
    def setReduced(self,value):self.reduced=value;self.save()
    @Slot(bool)
    def settings(self,value):self.settings_open=value;self.changed.emit()
    @Slot()
    def github(self):webbrowser.open('https://github.com/hexagon0401')
    @Slot()
    def logs(self):
        if sys.platform=='win32':os.startfile(str(DATA))

    @Slot()
    def checkUpdate(self):
        if self.testing or self.update_busy:return
        self.update_message=WORDS[self.language]['update_checking'];self.run_update()

    @Slot(bool)
    def setAutoUpdates(self,value):self.auto_updates=value;self.save()

    def automaticUpdate(self):
        if self.auto_updates and not self.update_busy and not self.testing:self.checkUpdate()

    @Slot()
    def installUpdate(self):
        if self.testing or self.update_busy or not self.update_info or not self.update_info.get('available'):return
        if self.dirty or (self.worker and self.worker.isRunning()):
            self.update_message=WORDS[self.language]['update_stop'];self.changed.emit();return
        self.installing_update=True
        self.update_message=WORDS[self.language]['update_downloading'];self.run_update(self.update_info)

    def run_update(self,info=None):
        self.update_busy=True;self.update_worker=UpdateWorker(info)
        self.update_worker.completed.connect(self.update_result)
        self.update_worker.failed.connect(self.update_error)
        self.update_worker.finished.connect(self.update_finished)
        self.update_worker.start();self.changed.emit()

    def update_result(self,result):
        if result.get('verified'):
            self.pending_installer=result['path'];return
        self.update_info=result
        self.update_message=(WORDS[self.language]['update_available']+' '+result['version']) if result.get('available') else WORDS[self.language]['update_current']

    def update_error(self,message):self.update_message=message;self.pending_installer=None

    def update_finished(self):
        self.update_busy=False;self.installing_update=False
        if self.pending_installer:
            try:
                from windows.updates import launch
                launch(self.pending_installer);self.pending_installer=None;self.closeRequested.emit()
            except Exception as exc:self.update_message=str(exc);self.pending_installer=None
        self.changed.emit()


def create_app(testing=False):
    # D3D11 is Qt Quick's Windows scene graph backend; WARP is the driver fallback,
    # unrelated to the separately installed Cloudflare WARP network client.
    if sys.platform=='win32':
        os.environ.setdefault('QSG_RHI_BACKEND','d3d11')
        QQuickStyle.setStyle('FluentWinUI3')
    else:QQuickStyle.setStyle('Basic') # portable source checks, not a Windows style claim
    QQuickWindow.setTextRenderType(QQuickWindow.TextRenderType.QtTextRendering)
    app=QGuiApplication.instance() or QGuiApplication(sys.argv)
    font=app.font();font.setFamilies(['Segoe UI Variable Text','Segoe UI','Malgun Gothic'])
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias|QFont.StyleStrategy.PreferQuality)
    font.setPixelSize(14);app.setFont(font);app.setWindowIcon(QIcon(str(ART/'AppIcon.png')))
    bridge=Bridge(testing);font.setFamily(bridge.state['fontFamily']);app.setFont(font)
    bridge.apply_appearance();engine=QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend',bridge)
    qml=ROOT/'qml/Main.qml' if (ROOT/'qml/Main.qml').exists() else ROOT/'windows/qml/Main.qml'
    engine.load(QUrl.fromLocalFile(str(qml.resolve())))
    if not engine.rootObjects():raise RuntimeError('Windows Qt Quick scene failed to load')
    window=engine.rootObjects()[0]
    bridge.window=window
    bridge.effects_supported=window.rendererInterface().graphicsApi() not in (QSGRendererInterface.GraphicsApi.Software,QSGRendererInterface.GraphicsApi.Unknown)
    bridge.changed.emit();bridge.apply_appearance()
    if not testing:
        QTimer.singleShot(4000,bridge.automaticUpdate)
        bridge.update_timer=QTimer(bridge);bridge.update_timer.setInterval(21600000)
        bridge.update_timer.timeout.connect(bridge.automaticUpdate);bridge.update_timer.start()
    return app,engine,bridge,window


def main():
    if '--self-test' in sys.argv:
        # Keep Python's diagnostic callback and Qt's render loop on one thread
        # during synchronous captures. Production retains Qt's default render loop.
        os.environ['QSG_RENDER_LOOP']='basic'
        output=Path(sys.argv[sys.argv.index('--self-test')+1])
        try:
            from windows.smoke import run
            run(output);return 0
        except BaseException:
            import traceback
            output.mkdir(parents=True,exist_ok=True)
            (output/'self-test-error.log').write_text(traceback.format_exc(),encoding='utf-8');return 1
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p];kernel.CreateMutexW.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p];kernel.GetConsoleWindow.restype=ctypes.c_void_p
    ctypes.windll.user32.ShowWindow.argtypes=[ctypes.c_void_p,ctypes.c_int]
    mutex=kernel.CreateMutexW(None,False,'Global\\MINER.Beta1.Windows')
    if not mutex:raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error()==183:
        ctypes.windll.user32.MessageBoxW(None,'MINER is already running. / MINER가 이미 실행 중입니다.','MINER',0x40)
        kernel.CloseHandle(mutex);return 1
    kernel.AllocConsole();ctypes.windll.user32.ShowWindow(kernel.GetConsoleWindow(),0)
    app,engine,bridge,window=create_app()
    code=app.exec()
    if bridge.update_worker:bridge.update_worker.cancelled.set()
    import shiboken6
    shiboken6.delete(window);shiboken6.delete(engine)
    kernel.CloseHandle(mutex);return code


if __name__=='__main__':sys.exit(main())
