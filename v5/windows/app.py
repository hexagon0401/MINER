"""MINER Windows: native window controls, measured backend stages and bounded motion."""
import ctypes
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
import webbrowser

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QVariantAnimation, QEasingCurve, QEvent, QPointF
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap, QKeySequence, QShortcut, QPen, QPalette
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea, QTextEdit)
from windows.controller import session
from windows.version import LABEL

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
ART = ROOT / 'art'
if not ART.exists(): ART = ROOT / 'macos/design/assets'
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'MINER' / 'Beta1'
WORDS = {
'ko': {'start':'시작', 'stop':'중지', 'settings':'설정', 'idle':'탈옥 준비', 'cli_check':'WARP CLI 확인', 'proxy_connect':'프록시 연결', 'tls_verify':'보안 연결 검증', 'warp_ready':'WARP 연결 확인', 'engine_check':'라우팅 설정 검사', 'engine_start':'네트워크 엔진 시작', 'running':'연결 완료', 'restoring':'WARP Traffic and DNS 복귀 중…', 'restored':'중지 완료 · WARP 복귀 확인', 'error':'연결을 완료하지 못했습니다', 'interrupted':'이전 연결이 정상 종료되지 않았습니다', 'about':'개발자 소개', 'hint':'클라이언트 WARP · 게임 직접 연결', 'close':'닫기', 'language':'언어', 'theme':'화면 테마', 'system':'시스템 설정', 'dark':'어둡게', 'light':'밝게', 'reduce':'동작 줄이기', 'details':'오류 상세', 'retry':'WARP 복귀 재시도', 'help':'개인용 WARP를 먼저 설치하고 등록해 주세요.', 'recovery':'중지를 눌러 엔진 정리와 WARP 복귀를 확인해 주세요.', 'opening':'연결 경로를 점검하고 있습니다.', 'log':'로그 폴더 열기'},
'en': {'start':'Start', 'stop':'Stop', 'settings':'Settings', 'idle':'Ready to dig', 'cli_check':'Checking WARP CLI', 'proxy_connect':'Connecting proxy', 'tls_verify':'Verifying secure connection', 'warp_ready':'WARP verified', 'engine_check':'Checking routing', 'engine_start':'Starting network engine', 'running':'Connected', 'restoring':'Restoring WARP Traffic and DNS…', 'restored':'Stopped · WARP restored', 'error':'Could not complete the connection', 'interrupted':'The previous session did not finish', 'about':'About the developer', 'hint':'Client via WARP · game direct', 'close':'Close', 'language':'Language', 'theme':'Appearance', 'system':'Use system settings', 'dark':'Dark', 'light':'Light', 'reduce':'Reduce motion', 'details':'Error details', 'retry':'Retry WARP restoration', 'help':'Install and register personal Cloudflare WARP first.', 'recovery':'Press Stop to confirm engine cleanup and WARP restoration.', 'opening':'Checking your connection path.', 'log':'Open logs folder'}}


def windows_appearance():
    """Read Windows accessibility preferences; unsupported calls keep safe defaults."""
    result = {'reduced':False, 'contrast':False}
    if sys.platform != 'win32': return result
    try:
        enabled = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
            result['reduced'] = not bool(enabled.value)
        class Contrast(ctypes.Structure):
            _fields_=[('size',ctypes.c_uint),('flags',ctypes.c_uint),('scheme',ctypes.c_wchar_p)]
        hc=Contrast(); hc.size=ctypes.sizeof(hc)
        if ctypes.windll.user32.SystemParametersInfoW(0x42,hc.size,ctypes.byref(hc),0):
            result['contrast']=bool(hc.flags & 1)
    except (AttributeError, OSError): pass
    return result


class Cave(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(130)
        self.setMaximumHeight(300)
        self.school=QPixmap(str(ART/'school.png')); self.miner=QPixmap(str(ART/'mascot-runtime-256.png'))
        self.strata=QPixmap(str(ART/'full-window-strata.png'))
        self.busy=False; self.active=True; self.reduced=False; self.phase='idle'; self.stage=0
        self.timer=QTimer(self); self.timer.setInterval(34); self.timer.timeout.connect(self.update)
        self.started=time.monotonic()

    def sync(self):
        animate=self.busy and self.active and self.isVisible() and not self.reduced
        if animate and not self.timer.isActive(): self.started=time.monotonic(); self.timer.start()
        if not animate: self.timer.stop()
        self.update()

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        scale=min(self.width()/560,self.height()/260)
        p.translate((self.width()-560*scale)/2,(self.height()-260*scale)/2); p.scale(scale,scale)
        path=QPainterPath(); path.addRoundedRect(0,0,560,260,20,20); p.setClipPath(path)
        p.fillRect(0,0,560,260,QColor('#202d3d'))
        if not self.strata.isNull(): p.drawPixmap(0,-110,560,610,self.strata)
        p.drawPixmap(215,10,130,75,self.school)
        path=QPainterPath(); path.moveTo(269,78)
        path.cubicTo(279,113,237,122,268,151); path.cubicTo(365,135,451,125,458,190)
        path.cubicTo(465,230,411,239,330,234); path.cubicTo(240,241,151,239,155,198)
        path.cubicTo(158,161,190,138,244,151); path.cubicTo(222,119,263,104,251,78); path.closeSubpath()
        p.fillPath(path,QColor('#080d15')); p.setPen(QPen(QColor('#71604a'),1.5))
        floor=QPainterPath(); floor.moveTo(177,225); floor.cubicTo(258,241,356,226,436,225);p.drawPath(floor)
        t=(time.monotonic()-self.started)/.57 if self.timer.isActive() else 0
        x=340+self.stage*7 if self.busy else 370
        if self.phase=='running':
            beam=QPainterPath(); beam.moveTo(x-12,137);beam.lineTo(x-65,232);beam.lineTo(x+60,232);beam.lineTo(x+12,137)
            p.fillPath(beam,QColor(210,240,210,28))
        p.save();p.translate(x,184)
        p.rotate(math.sin(t*math.tau)*4 if t else (-5 if self.phase=='running' else 0))
        p.drawPixmap(-50,-50,100,100,self.miner);p.restore()
        if self.timer.isActive():
            p.setPen(Qt.NoPen)
            for i in range(5):
                u=(t+i*.16)%1;p.setBrush(QColor(208,164,111,int(180*(1-u))))
                p.drawRect(int(x+39+u*(12+i*3)),int(185+u*(20+i*5)),3+i%3,3+i%3)
        p.end()


class Motion(QWidget):
    """Transient effects never intercept actions or advance backend progress."""
    def __init__(self,parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.value=1.;self.kind='start';self.origin=None;self.anim=QVariantAnimation(self)
        self.anim.valueChanged.connect(self.changed)
        self.hide()

    def changed(self,value): self.value=float(value);self.update()
    def play(self,kind,origin=None,reduced=False):
        self.anim.stop();self.kind=kind;self.origin=origin
        if reduced: self.hide();return
        self.setGeometry(self.parentWidget().rect());self.show();self.raise_()
        self.anim.setDuration(1400 if kind=='success' else 520 if kind=='start' else 480)
        self.anim.setStartValue(0.);self.anim.setEndValue(1.)
        self.anim.setEasingCurve(QEasingCurve.OutCubic);self.anim.start()
    def cancel(self): self.anim.stop();self.value=1.;self.hide()
    def paintEvent(self,event):
        if self.value>=1.: return
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);v=self.value
        if self.kind=='success':
            alpha=min(1,v*8,(1-v)*5)
            p.fillRect(self.rect(),QColor(0,0,0,int(26*alpha)))
            c=self.rect().center();r=30*(.8+.2*min(1,v*4))
            p.setPen(Qt.NoPen);p.setBrush(QColor(14,230,55,int(255*alpha)));p.drawEllipse(QPointF(c),r,r)
            p.setPen(QPen(QColor(8,35,18,int(255*alpha)),4,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
            check=QPainterPath();check.moveTo(c.x()-12,c.y());check.lineTo(c.x()-3,c.y()+9);check.lineTo(c.x()+13,c.y()-11);p.drawPath(check)
        elif self.origin:
            p.setPen(Qt.NoPen);color=QColor('#0efb2e' if self.kind=='start' else '#ff5a61')
            color.setAlpha(int(78*(1-v)));p.setBrush(color)
            radius=math.hypot(self.width(),self.height())*v
            p.drawEllipse(QPointF(self.origin),radius,radius)
        p.end()


class Worker(QThread):
    progress=Signal(str,int); failed=Signal(str)
    def __init__(self,restore=False):
        super().__init__();self.stop_event=threading.Event();self.restore=restore
    def run(self):
        try:session(DATA,ROOT/'engine/sing-box.exe',self.stop_event,lambda phase,count:self.progress.emit(phase,count),self.restore)
        except Exception as exc:self.failed.emit(str(exc))


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('MINER');self.setWindowIcon(QIcon(str(ART/'AppIcon.png')))
        self.setMinimumSize(480,440)
        area=QApplication.primaryScreen().availableGeometry()
        self.resize(min(560,area.width()),min(680,area.height()))
        DATA.mkdir(parents=True,exist_ok=True)
        try:
            cfg=json.loads((DATA/'settings.json').read_text(encoding='utf-8'))
            if not isinstance(cfg,dict):cfg={}
        except (OSError,ValueError):cfg={}
        self.lang=cfg.get('language','ko') if cfg.get('language','ko') in WORDS else 'ko'
        self.theme=cfg.get('theme','system') if cfg.get('theme','system') in ('system','dark','light') else 'system'
        self.reduced=bool(cfg.get('reduce_motion',False))
        self.worker=None;self.dirty=(DATA/'session.json').exists();self.closing=False
        self.detail='';self.phase='interrupted' if self.dirty else 'idle';self.count=0;self.dialog=None
        self.appearance=windows_appearance()
        self.reduced=self.reduced or self.appearance['reduced']
        layout=QVBoxLayout(self);layout.setContentsMargins(24,20,24,18);layout.setSpacing(10)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.NoFrame)
        body=QWidget();main=QVBoxLayout(body);main.setContentsMargins(0,0,0,0);main.setSpacing(12)
        header=QHBoxLayout(); title=QLabel('MINER');title.setObjectName('wordmark');header.addWidget(title);header.addStretch()
        self.chip=QLabel();header.addWidget(self.chip);main.addLayout(header)
        main.addWidget(QLabel('Dig your way out.'))
        self.cave=Cave();main.addWidget(self.cave,1)
        self.status=QLabel();self.status.setWordWrap(True);self.status.setObjectName('status');main.addWidget(self.status)
        self.description=QLabel();self.description.setWordWrap(True);main.addWidget(self.description)
        self.steps=QLabel();main.addWidget(self.steps)
        self.error_details=QTextEdit();self.error_details.setReadOnly(True);self.error_details.setMaximumHeight(100);self.error_details.hide();main.addWidget(self.error_details)
        scroll.setWidget(body);layout.addWidget(scroll,1)
        self.start=QPushButton();self.start.setObjectName('start');self.start.setMinimumHeight(46);self.start.clicked.connect(self.begin);layout.addWidget(self.start)
        self.stop=QPushButton();self.stop.setMinimumHeight(36);self.stop.clicked.connect(self.end);layout.addWidget(self.stop)
        footer=QHBoxLayout();self.hint=QLabel();self.hint.setWordWrap(True);footer.addWidget(self.hint,1)
        self.settings=QPushButton();self.settings.clicked.connect(self.preferences);footer.addWidget(self.settings);layout.addLayout(footer)
        self.motion=Motion(self)
        QShortcut(QKeySequence('Ctrl+,'),self,activated=self.preferences)
        self.setTabOrder(self.start,self.stop);self.setTabOrder(self.stop,self.settings)
        self.apply_theme();self.refresh()
        QApplication.instance().applicationStateChanged.connect(self.sync_motion)

    def save(self):
        from schoolnet.runtime import write_json
        write_json(DATA/'settings.json',{'language':self.lang,'theme':self.theme,'reduce_motion':self.reduced})

    def apply_theme(self):
        if self.appearance['contrast']:
            self.setStyleSheet('QPushButton {padding:8px;} QPushButton:focus {border:3px solid palette(highlight);} #wordmark {font-size:28px;font-weight:800;}')
            return
        dark=self.theme=='dark' or (self.theme=='system' and QApplication.palette().color(QPalette.Window).lightness()<128)
        self.dark=dark
        bg,fg,panel,muted=('#111a26','#edf2f7','#29394d','#aab9cb') if dark else ('#f3f6fa','#142337','#e2e9f1','#465b73')
        self.setStyleSheet(f'QWidget {{background:{bg};color:{fg};}} QLabel {{background:transparent;}} QScrollArea {{border:0;}} QPushButton,QComboBox {{padding:8px;border:1px solid {muted};border-radius:9px;background:{panel};}} QPushButton:disabled {{color:{muted};border-color:{panel};}} QPushButton:focus,QComboBox:focus {{border:2px solid #008b32;}} #start {{background:#0ee432;color:#05220e;font-weight:700;}} #start:disabled {{background:{panel};color:{muted};}} #wordmark {{font-size:28px;font-weight:800;}} #status {{font-size:17px;font-weight:600;}} QTextEdit {{background:{panel};}}')

    def refresh(self):
        w=WORDS[self.lang];self.status.setText(w.get(self.phase,self.phase))
        self.description.setText(w['recovery'] if self.phase in ('error','interrupted') else w['hint'] if self.phase=='running' else w['opening'] if self.dirty else w['help'])
        self.chip.setText('● '+w.get(self.phase,self.phase) if self.phase in ('idle','running','error') else f'{self.count}/5')
        self.steps.setText('  '.join('━' if n<self.count else '─' for n in range(5))+f'    {self.count}/5')
        self.start.setText(w['start']);self.stop.setText(w['retry'] if self.phase in ('error','interrupted') else w['stop']);self.settings.setText(w['settings']);self.hint.setText('WARP Local Proxy · 127.0.0.1:40000')
        self.start.setAccessibleName(w['start']);self.stop.setAccessibleName(self.stop.text());self.settings.setAccessibleName(w['settings'])
        active=bool(self.worker and self.worker.isRunning())
        self.start.setEnabled(not self.dirty and not active)
        self.stop.setEnabled(self.dirty and self.phase!='restoring')
        self.error_details.setVisible(bool(self.detail));self.error_details.setPlainText(w['details']+'\n'+self.detail)
        self.cave.phase=self.phase;self.cave.stage=self.count
        self.cave.busy=active and self.phase not in ('running','restoring','error','restored')
        self.sync_motion()

    def sync_motion(self,*args):
        self.cave.active=self.isActiveWindow() and not self.isMinimized()
        self.cave.reduced=self.reduced;self.cave.sync()
        if not self.cave.active:self.motion.cancel()

    def changeEvent(self,event):
        super().changeEvent(event)
        if hasattr(self,'cave') and event.type() in (QEvent.ActivationChange,QEvent.WindowStateChange):self.sync_motion()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'motion'):self.motion.setGeometry(self.rect())

    def begin(self):
        if self.dirty or (self.worker and self.worker.isRunning()):return
        self.dirty=True;self.detail='';self.phase='cli_check';self.count=0
        self.motion.play('start',self.start.mapTo(self,self.start.rect().center()),self.reduced)
        self.launch(False)

    def launch(self,restore):
        if self.worker and self.worker.isRunning():return
        self.worker=Worker(restore);self.worker.progress.connect(self.update_state);self.worker.failed.connect(self.failure);self.worker.finished.connect(self.finished)
        self.worker.start();self.refresh()

    def update_state(self,phase,count):
        if self.worker and self.worker.stop_event.is_set() and phase!='restored':
            phase='restoring';count=0
        previous=self.phase;self.detail='';self.phase=phase;self.count=count
        if phase=='restored':self.dirty=False;self.motion.cancel()
        self.refresh()
        if phase=='running' and previous!='running':self.motion.play('success',reduced=self.reduced)

    def failure(self,message):
        self.motion.cancel();self.detail=message;self.phase='error';self.closing=False;self.refresh()

    def finished(self):
        self.refresh()
        if self.closing and not self.dirty:self.close()

    def end(self):
        if not self.dirty:return
        self.phase='restoring';self.motion.play('stop',self.stop.mapTo(self,self.stop.rect().center()),self.reduced)
        if self.worker and self.worker.isRunning():self.worker.stop_event.set();self.refresh()
        else:self.launch(True)

    def closeEvent(self,event):
        if self.dirty or (self.worker and self.worker.isRunning()):
            event.ignore();self.closing=True
            if self.phase!='restoring':self.end()
        else:self.motion.cancel();self.cave.timer.stop();event.accept()

    def preferences(self):
        if self.dialog:self.dialog.raise_();self.dialog.activateWindow();return
        d=QDialog(self);self.dialog=d;d.setMinimumWidth(360);l=QVBoxLayout(d)
        language_label=QLabel();l.addWidget(language_label)
        language=QComboBox();language.addItems(['한국어','English']);language.setCurrentIndex(0 if self.lang=='ko' else 1);l.addWidget(language)
        theme_label=QLabel();l.addWidget(theme_label);theme=QComboBox();l.addWidget(theme)
        reduce=QCheckBox();reduce.setChecked(self.reduced);l.addWidget(reduce)
        about=QLabel();l.addWidget(about)
        avatar=QLabel();pix=QPixmap(str(ART/'developer-avatar.png'))
        if not pix.isNull():avatar.setPixmap(pix.scaled(64,64,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        l.addWidget(avatar);l.addWidget(QLabel('Punkthats*it · @hexagon0401\n'+LABEL))
        github=QPushButton('GitHub · hexagon0401');github.clicked.connect(lambda:webbrowser.open('https://github.com/hexagon0401'));l.addWidget(github)
        logs=QPushButton();logs.clicked.connect(lambda:os.startfile(str(DATA)));l.addWidget(logs)
        close=QPushButton();close.clicked.connect(d.accept);l.addWidget(close)
        def labels():
            w=WORDS[self.lang];d.setWindowTitle(w['settings']);language_label.setText(w['language']);theme_label.setText(w['theme']);reduce.setText(w['reduce']);about.setText(w['about']);logs.setText(w['log']);close.setText(w['close'])
            theme.blockSignals(True);theme.clear();theme.addItems([w['system'],w['dark'],w['light']]);theme.setCurrentIndex(['system','dark','light'].index(self.theme));theme.blockSignals(False)
        def change_language(n):self.lang=['ko','en'][n];self.save();self.refresh();labels()
        def change_theme(n):self.theme=['system','dark','light'][n];self.save();self.apply_theme()
        def change_motion(v):self.reduced=v or self.appearance['reduced'];self.save();self.motion.cancel();self.refresh()
        language.currentIndexChanged.connect(change_language);theme.currentIndexChanged.connect(change_theme);reduce.toggled.connect(change_motion);labels()
        d.finished.connect(lambda _:setattr(self,'dialog',None));d.setAttribute(Qt.WA_DeleteOnClose);d.show()


def main():
    if '--self-test' in sys.argv:
        from windows.smoke import run
        output=Path(sys.argv[sys.argv.index('--self-test')+1])
        try:
            run(output);return 0
        except BaseException:
            import traceback
            output.mkdir(parents=True,exist_ok=True)
            (output/'self-test-error.log').write_text(traceback.format_exc(),encoding='utf-8')
            return 1
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
    app=QApplication(sys.argv);w=Window();w.show()
    code=app.exec();kernel.CloseHandle(mutex);return code


if __name__=='__main__':sys.exit(main())
