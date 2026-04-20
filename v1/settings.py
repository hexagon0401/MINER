"""
settings.py - JSON config handling and launchd plist generation.
"""

import json
import os
import logging
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, asdict, field

CONFIG_DIR = os.path.expanduser("~/Library/Application Support/SchoolNetOptimizer")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

PLIST_DIR = os.path.expanduser("~/Library/LaunchAgents")
PLIST_PATH = os.path.join(PLIST_DIR, "com.schoolnet.optimizer.plist")

LOG_DIR = os.path.expanduser("~/Library/Logs/SchoolNetOptimizer")
LOG_PATH = os.path.join(LOG_DIR, "app.log")

@dataclass
class Settings:
    primary_provider: str = "quad9"
    obfuscation_enabled: bool = False
    auto_start: bool = False
    language: str = "ko"
    first_launch: bool = True
    last_ssid: str = ""
    last_recon: dict = field(default_factory=dict)

    @classmethod
    def load(cls) -> "Settings":
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception as e:
                logging.error(f"Failed to load settings from {CONFIG_PATH}: {e}")
        return cls()

    def save(self):
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

    def enable_autostart(self):
        import sys
        if getattr(sys, 'frozen', False):
            # PyInstaller creates a frozen executable.
            app_path = sys.executable
        else:
            app_path = os.path.abspath(sys.argv[0]) # if running as python script

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
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
        if not os.path.exists(PLIST_DIR):
            os.makedirs(PLIST_DIR, exist_ok=True)
        try:
            with open(PLIST_PATH, "w", encoding="utf-8") as f:
                f.write(plist_content)
            os.system(f"launchctl load {PLIST_PATH}")
        except Exception as e:
            logging.error(f"Failed to enable autostart: {e}")

    def disable_autostart(self):
        if os.path.exists(PLIST_PATH):
            os.system(f"launchctl unload {PLIST_PATH}")
            try:
                os.remove(PLIST_PATH)
            except Exception as e:
                logging.error(f"Failed to disable autostart: {e}")

def setup_logging():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
    handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
