"""Native Qt Windows UI using the existing Beta 1 artwork and network engine."""
import ctypes
import json
import os
from pathlib import Path
import sys
import threading
import webbrowser

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget
from windows.controller import session

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
ART = ROOT / 'art'
if not ART.exists():
    ART = ROOT / 'macos/design/assets'
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'MINER' / 'Beta1'
WORDS = {
'ko': {'start':'시작', 'stop':'중지', 'settings':'설정', 'idle':'탈옥 준비', 'cli_check':'WARP CLI 확인', 'proxy_connect':'프록시 연결', 'tls_verify':'보안 연결 검증', 'warp_ready':'WARP 연결 확인', 'engine_check':'라우팅 설정 검사', 'engine_start':'네트워크 엔진 시작', 'running':'연결 완료 · 클라이언트 WARP / 게임 직접 연결', 'restoring':'WARP Traffic and DNS 복귀 중', 'restored':'중지 완료 · WARP 복귀 확인', 'error':'연결 오류 · 중지를 눌러 WARP 복귀', 'about':'개발자 소개', 'hint':'WARP Local Proxy · 127.0.0.1:40000', 'close':'닫기'},
'en': {'start':'Start', 'stop':'Stop', 'settings':'Settings', 'idle':'Ready to dig', 'cli_check':'Checking WARP CLI', 'proxy_connect':'Connecting proxy', 'tls_verify':'Verifying secure connection', 'warp_ready':'WARP verified', 'engine_check':'Checking routing', 'engine_start':'Starting network engine', 'running':'Connected · client WARP / game direct', 'restoring':'Restoring WARP Traffic and DNS', 'restored':'Stopped · WARP restored', 'error':'Connection error · press Stop to restore WARP', 'about':'About', 'hint':'WARP Local Proxy · 127.0.0.1:40000', 'close':'Close'}}


class Cave(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(230)
        self.school = QPixmap(str(ART / 'school.png'))
        self.miner = QPixmap(str(ART / 'mascot-runtime-256.png'))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(self.width()/560, self.height()/250)
        p.fillRect(0, 0, 560, 250, QColor('#202d3d'))
        p.drawPixmap(215, 5, 130, 75, self.school)
        path = QPainterPath()
        path.moveTo(270, 76); path.cubicTo(280, 115, 235, 120, 270, 150)
        path.cubicTo(370, 132, 455, 125, 458, 190)
        path.cubicTo(463, 230, 410, 237, 330, 233)
        path.cubicTo(240, 240, 151, 239, 155, 198)
        path.cubicTo(157, 162, 190, 138, 244, 151)
        path.cubicTo(222, 119, 264, 102, 251, 76)
        path.closeSubpath()
        p.fillPath(path, QColor('#080d15'))
        p.drawPixmap(330, 137, 100, 100, self.miner)
        p.end()


class Worker(QThread):
    progress = Signal(str, int)
    failed = Signal(str)
    def __init__(self, restore=False):
        super().__init__()
        self.stop_event = threading.Event()
        self.restore = restore
    def run(self):
        try:
            session(DATA, ROOT/'engine/sing-box.exe', self.stop_event,
                    lambda phase, count: self.progress.emit(phase, count), self.restore)
        except Exception as exc:
            self.failed.emit(str(exc))


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('MINER')
        self.setWindowIcon(QIcon(str(ART/'AppIcon.png')))
        self.resize(560, 650)
        self.setMinimumSize(520, 620)
        DATA.mkdir(parents=True, exist_ok=True)
        try:
            self.lang = json.loads((DATA/'settings.json').read_text())['language']
        except (OSError, ValueError, KeyError):
            self.lang = 'ko'
        if self.lang not in WORDS: self.lang = 'ko'
        self.worker = None
        self.dirty = False
        self.closing = False
        self.detail = ''
        self.phase = 'idle'
        self.count = 0
        self.setStyleSheet('QWidget {background:#111a26;color:#edf2f7;font:14px "Segoe UI";} QPushButton {padding:12px;border-radius:12px;background:#29394d;} QPushButton:disabled {color:#748092;} QLabel {background:transparent;} QComboBox {padding:8px;}')
        layout = QVBoxLayout(self); layout.setContentsMargins(26,24,26,24); layout.setSpacing(15)
        title = QLabel('MINER'); title.setStyleSheet('font-size:28px;font-weight:800;'); layout.addWidget(title)
        layout.addWidget(QLabel('Dig your way out.'))
        layout.addWidget(Cave(), 1)
        self.status = QLabel(); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.steps = QLabel(); layout.addWidget(self.steps)
        self.start = QPushButton(); self.start.setStyleSheet('background:#00e52b;color:#06170b;font-weight:bold;'); self.start.clicked.connect(self.begin); layout.addWidget(self.start)
        self.stop = QPushButton(); self.stop.clicked.connect(self.end); layout.addWidget(self.stop)
        self.hint = QLabel(); layout.addWidget(self.hint)
        self.settings = QPushButton(); self.settings.clicked.connect(self.preferences); layout.addWidget(self.settings)
        QShortcut(QKeySequence('Ctrl+,'), self, activated=self.preferences)
        self.refresh()

    def refresh(self):
        w=WORDS[self.lang]
        self.status.setText(w.get(self.phase,self.phase)+(('\n'+self.detail) if self.detail else ''))
        self.steps.setText('  '.join('●' if n<self.count else '○' for n in range(5))+f'    {self.count}/5')
        self.start.setText(w['start']); self.stop.setText(w['stop']); self.settings.setText(w['settings']); self.hint.setText(w['hint'])
        self.start.setEnabled(not self.dirty and not (self.worker and self.worker.isRunning()))
        self.stop.setEnabled(self.dirty)

    def begin(self):
        if self.dirty or (self.worker and self.worker.isRunning()): return
        self.dirty = True
        self.launch(False)

    def launch(self, restore):
        self.worker = Worker(restore)
        self.worker.progress.connect(self.update_state)
        self.worker.failed.connect(self.failure)
        self.worker.finished.connect(self.finished)
        self.worker.start(); self.refresh()

    def update_state(self, phase, count):
        self.detail=""
        self.phase=phase; self.count=count
        if phase=='restored': self.dirty=False
        self.refresh()

    def failure(self, message):
        self.detail=message
        self.phase='error'; self.closing=False; self.refresh()

    def finished(self):
        self.refresh()
        if self.closing and not self.dirty: self.close()

    def end(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop_event.set()
            self.phase='restoring'; self.refresh()
        elif self.dirty: self.launch(True)

    def closeEvent(self, event):
        if self.dirty or (self.worker and self.worker.isRunning()):
            event.ignore(); self.closing=True; self.end()
        else: event.accept()

    def preferences(self):
        d=QDialog(self); d.setWindowTitle(WORDS[self.lang]['settings']); d.resize(360,330)
        l=QVBoxLayout(d); l.addWidget(QLabel('언어 / Language'))
        c=QComboBox(); c.addItems(['한국어','English']); c.setCurrentIndex(0 if self.lang=='ko' else 1)
        def change(n):
            self.lang=['ko','en'][n]
            (DATA/'settings.json').write_text(json.dumps({'language':self.lang}),encoding='utf-8')
            self.refresh()
        c.currentIndexChanged.connect(change); l.addWidget(c)
        l.addWidget(QLabel(WORDS[self.lang]['about']))
        avatar=QLabel(); pix=QPixmap(str(ART/'developer-avatar.png'))
        if not pix.isNull(): avatar.setPixmap(pix.scaled(64,64,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        l.addWidget(avatar)
        l.addWidget(QLabel('Punkthats*it · @hexagon0401\nMINER BETA 1 · Windows x64'))
        b=QPushButton('GitHub · hexagon0401'); b.clicked.connect(lambda:webbrowser.open('https://github.com/hexagon0401')); l.addWidget(b)
        b=QPushButton(WORDS[self.lang]['close']); b.clicked.connect(d.accept); l.addWidget(b); d.exec()


def main():
    # Hidden shared console permits graceful CTRL_BREAK to the engine's process group.
    if "--self-test" in sys.argv:
        from windows.smoke import run
        run(sys.argv[sys.argv.index("--self-test")+1])
        return 0
    kernel=ctypes.windll.kernel32
    kernel.CreateMutexW.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    kernel.GetConsoleWindow.restype=ctypes.c_void_p
    ctypes.windll.user32.ShowWindow.argtypes=[ctypes.c_void_p,ctypes.c_int]
    mutex=kernel.CreateMutexW(None,False,'Local\\MINER.Beta1.Windows')
    if not mutex: raise ctypes.WinError()
    if kernel.GetLastError()==183:
        kernel.CloseHandle(mutex)
        return 1
    kernel.AllocConsole()
    ctypes.windll.user32.ShowWindow(kernel.GetConsoleWindow(),0)
    app=QApplication(sys.argv)
    w=Window(); w.show()
    code=app.exec()
    kernel.CloseHandle(mutex)
    return code


if __name__=='__main__':
    sys.exit(main())
