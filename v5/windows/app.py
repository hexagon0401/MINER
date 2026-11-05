"""Windows Qt Quick / Fluent frontend, isolated from the networking controller."""
import ctypes
import json
import os
from pathlib import Path
import sys
import threading
import webbrowser

from PySide6.QtCore import QObject, Property, QThread, Signal, Slot, QUrl, Qt
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
        super().__init__();self.stop_event=threading.Event();self.restore=restore
    def run(self):
        try:session(DATA,ROOT/'engine/sing-box.exe',self.stop_event,lambda p,c:self.progress.emit(p,c),self.restore)
        except Exception as exc:self.failed.emit(str(exc))


class Bridge(QObject):
    changed=Signal();effect=Signal(str);closeRequested=Signal()
    def __init__(self,testing=False):
        super().__init__();self.testing=testing;self.worker=None;self.closing=False;self.detail='';self.count=0
        self.settings_open=False;self.fixture_busy=False
        DATA.mkdir(parents=True,exist_ok=True)
        try:
            cfg=json.loads((DATA/'settings.json').read_text(encoding='utf-8'))
            if not isinstance(cfg,dict):cfg={}
        except (OSError,ValueError):cfg={}
        language=cfg.get('language');theme=cfg.get('theme')
        self.language=language if isinstance(language,str) and language in WORDS else 'ko'
        self.theme=theme if theme in ('system','light','dark') else 'system'
        self.reduced=cfg.get('reduce_motion') is True
        self.appearance=windows_appearance();self.dirty=(DATA/'session.json').exists()
        self.phase='interrupted' if self.dirty else 'idle'
        available=QFontDatabase.families()
        self.font_family=next((x for x in ('Segoe UI Variable Text','Segoe UI','Noto Sans') if x in available),QGuiApplication.font().family())
        QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _:self.changed.emit())

    @Property('QVariantMap',notify=changed)
    def state(self):
        active=bool(self.worker and self.worker.isRunning())
        system_dark=QGuiApplication.styleHints().colorScheme()==Qt.ColorScheme.Dark
        return {'text':WORDS[self.language],'language':self.language,'theme':self.theme,
            'dark':self.theme=='dark' or (self.theme=='system' and system_dark),
            'reduced':self.reduced or self.appearance['reduced'],'systemReduced':self.appearance['reduced'],
            'contrast':self.appearance['contrast'],'phase':self.phase,'completed':self.count,
            'detail':self.detail,'canStart':not self.dirty and not active,
            'canStop':self.dirty and self.phase!='restoring',
            'busy':(active or self.fixture_busy) and self.phase not in ('running','restoring','error','restored'),
            'settingsOpen':self.settings_open,'fontFamily':self.font_family,'version':LABEL,
            'art':QUrl.fromLocalFile(str(ART.resolve())+os.sep).toString(),
            'validation':self.testing}

    def save(self):
        from schoolnet.runtime import write_json
        try:write_json(DATA/'settings.json',{'language':self.language,'theme':self.theme,'reduce_motion':self.reduced})
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
        if self.worker and self.worker.stop_event.is_set() and phase!='restored':phase='restoring';count=0
        previous=self.phase;self.detail='';self.phase=phase;self.count=count
        if phase=='restored':self.dirty=False
        self.changed.emit()
        if phase=='running' and previous!='running':self.effect.emit('success')
    def failure(self,message):
        self.detail=message;self.phase='error';self.closing=False;self.changed.emit();self.effect.emit('cancel')
    def finished(self):
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
        if self.dirty or (self.worker and self.worker.isRunning()):
            self.closing=True
            if self.phase!='restoring':self.end()
            return False
        return True
    @Slot(str)
    def setLanguage(self,value):
        if value in WORDS:self.language=value;self.save()
    def apply_appearance(self):
        hints=QGuiApplication.styleHints()
        scheme={'system':Qt.ColorScheme.Unknown,'dark':Qt.ColorScheme.Dark,'light':Qt.ColorScheme.Light}[self.theme]
        hints.setColorScheme(scheme)
        if sys.platform=='win32' and hasattr(self,'window'):
            try:
                dark=ctypes.c_int(int(self.state['dark']))
                fn=ctypes.windll.dwmapi.DwmSetWindowAttribute
                fn.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint]
                fn(int(self.window.winId()),20,ctypes.byref(dark),ctypes.sizeof(dark))
            except (AttributeError,OSError):pass

    @Slot(str)
    def setTheme(self,value):
        if value in ('system','light','dark'):self.theme=value;self.apply_appearance();self.save()
    @Slot(bool)
    def setReduced(self,value):self.reduced=value;self.save()
    @Slot(bool)
    def settings(self,value):self.settings_open=value;self.changed.emit()
    @Slot()
    def github(self):webbrowser.open('https://github.com/hexagon0401')
    @Slot()
    def logs(self):
        if sys.platform=='win32':os.startfile(str(DATA))


def create_app(testing=False):
    # D3D11 is Qt Quick's Windows scene graph backend; WARP is the driver fallback,
    # unrelated to the separately installed Cloudflare WARP network client.
    if sys.platform=='win32':
        os.environ.setdefault('QSG_RHI_BACKEND','d3d11')
        QQuickStyle.setStyle('FluentWinUI3')
    else:QQuickStyle.setStyle('Basic') # portable source checks, not a Windows style claim
    QQuickWindow.setTextRenderType(QQuickWindow.TextRenderType.CurveTextRendering)
    app=QGuiApplication.instance() or QGuiApplication(sys.argv)
    font=app.font();font.setFamilies(['Segoe UI Variable Text','Segoe UI','Malgun Gothic'])
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias|QFont.StyleStrategy.PreferQuality)
    font.setPixelSize(14);app.setFont(font);app.setWindowIcon(QIcon(str(ART/'AppIcon.png')))
    bridge=Bridge(testing);bridge.apply_appearance();engine=QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend',bridge)
    qml=ROOT/'qml/Main.qml' if (ROOT/'qml/Main.qml').exists() else ROOT/'windows/qml/Main.qml'
    engine.load(QUrl.fromLocalFile(str(qml.resolve())))
    if not engine.rootObjects():raise RuntimeError('Windows Qt Quick scene failed to load')
    window=engine.rootObjects()[0]
    bridge.window=window;bridge.apply_appearance()
    return app,engine,bridge,window


def main():
    if '--self-test' in sys.argv:
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
    import shiboken6
    shiboken6.delete(window);shiboken6.delete(engine)
    kernel.CloseHandle(mutex);return code


if __name__=='__main__':sys.exit(main())
