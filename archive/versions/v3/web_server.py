"""
web_server.py - Lightweight HTTP Server for Dashboard API
"""

import json
import logging
import inspect
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os

# Global log queue for web UI
WEB_LOGS = []

def add_web_log(msg: str):
    WEB_LOGS.append(msg)
    if len(WEB_LOGS) > 100:
        WEB_LOGS.pop(0)

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress default logging

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        import gui  # To interact with global state inside the method to avoid circular deps
        app_instance = getattr(gui, "GLOBAL_APP", None)

        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            
            import sys
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
            html_path = os.path.join(base_dir, 'dashboard.html')
            
            with open(html_path, 'r', encoding='utf-8') as f:
                self.wfile.write(f.read().encode('utf-8'))
            return


        if self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            
            state = {
                "running": getattr(app_instance, "is_active", False) if app_instance else False,
                "optimizing": getattr(app_instance, "is_optimizing", False) if app_instance else False,
                "latency": getattr(app_instance, "current_latency", 0) if app_instance else 0,
                "bypass_verified": getattr(app_instance, "bypass_verified", None) if app_instance else None,
                "settings": getattr(app_instance.config, "__dict__", {}) if app_instance else {},
            }
            if app_instance and getattr(app_instance, "recon_result", None):
                import dataclasses
                state['recon'] = dataclasses.asdict(app_instance.recon_result)
            else:
                state['recon'] = None

            self.wfile.write(json.dumps(state).encode('utf-8'))
            return

        if self.path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            
            global WEB_LOGS
            to_send = list(WEB_LOGS)
            WEB_LOGS.clear()
            
            self.wfile.write(json.dumps({"logs": to_send}).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        import gui
        app_instance = getattr(gui, "GLOBAL_APP", None)

        if self.path == '/api/settings':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            if app_instance:
                app_instance.config.primary_provider = data.get('primary_provider', 'quad9')
                app_instance.config.obfuscation_enabled = data.get('obfuscation_enabled', False)
                app_instance.config.auto_start = data.get('auto_start', False)
                app_instance.config.save()
                
                if app_instance.config.auto_start:
                    app_instance.config.enable_autostart()
                else:
                    app_instance.config.disable_autostart()
                
                # Trigger action from GUI thread to re-optimize safely
                import threading
                threading.Thread(target=app_instance._do_optimize, daemon=True).start()
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            return
            
        if self.path == '/api/restore':
            if app_instance:
                import threading
                threading.Thread(target=app_instance._do_restore, daemon=True).start()
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            return

def start_server():
    server = HTTPServer(('127.0.0.1', 5354), DashboardHandler)
    server.serve_forever()

def run_web_server_daemon():
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
