"""
settings.py - JSON config handling and launchd plist generation (v2)

Fixes vs v1:
- 원자적 쓰기: tempfile → os.replace() 방식으로 저장 중 충돌 시 config.json 손상 방지
- launchctl: os.system → subprocess.run으로 오류 감지 가능
- enable/disable_autostart 반환값 추가
"""

import json
import os
import logging
import subprocess
import tempfile
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, asdict, field

CONFIG_DIR  = os.path.expanduser("~/Library/Application Support/SchoolNetOptimizer")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

PLIST_DIR  = os.path.expanduser("~/Library/LaunchAgents")
PLIST_PATH = os.path.join(PLIST_DIR, "com.schoolnet.optimizer.plist")

LOG_DIR  = os.path.expanduser("~/Library/Logs/SchoolNetOptimizer")
LOG_PATH = os.path.join(LOG_DIR, "app.log")


@dataclass
class Settings:
    primary_provider:    str  = "quad9"
    obfuscation_enabled: bool = False
    auto_start:          bool = False
    language:            str  = "ko"
    first_launch:        bool = True
    last_ssid:           str  = ""
    last_recon:          dict = field(default_factory=dict)

    VALID_PROVIDERS = {"quad9", "cloudflare", "adguard"}
    VALID_LANGUAGES = {"ko", "en"}

    @classmethod
    def load(cls) -> "Settings":
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception as e:
                logging.error(f"Settings load failed ({CONFIG_PATH}): {e}. Using defaults.")
        return cls()

    def save(self):
        """원자적 쓰기: 임시 파일에 쓴 후 rename → 충돌 시 기존 파일 보존."""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=CONFIG_DIR, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(asdict(self), f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, CONFIG_PATH)  # 원자적 교체
            except Exception:
                os.unlink(tmp_path)
                raise
        except Exception as e:
            logging.error(f"Settings save failed: {e}")

    def validate(self):
        """잘못된 값을 기본값으로 교정."""
        if self.primary_provider not in self.VALID_PROVIDERS:
            self.primary_provider = "quad9"
        if self.language not in self.VALID_LANGUAGES:
            self.language = "ko"

    def enable_autostart(self) -> bool:
        import sys
        app_path = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])

        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.schoolnet.optimizer</string>
    <key>Program</key>
    <string>{app_path}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
        os.makedirs(PLIST_DIR, exist_ok=True)
        try:
            with open(PLIST_PATH, "w", encoding="utf-8") as f:
                f.write(plist)
            result = subprocess.run(
                ["launchctl", "load", PLIST_PATH],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                logging.warning(f"launchctl load warning: {result.stderr}")
            return True
        except Exception as e:
            logging.error(f"enable_autostart failed: {e}")
            return False

    def disable_autostart(self) -> bool:
        if not os.path.exists(PLIST_PATH):
            return True
        try:
            subprocess.run(
                ["launchctl", "unload", PLIST_PATH],
                capture_output=True, text=True
            )
            os.remove(PLIST_PATH)
            return True
        except Exception as e:
            logging.error(f"disable_autostart failed: {e}")
            return False


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
