"""
locales.py - String table for Korean and English localization (v2)

Changes vs v1:
- quit_label 추가 (v1에서 Quit 버튼이 하드코딩되어 i18n 미적용이던 버그)
"""

STRINGS = {
    "ko": {
        "analyze_button":     "🔍 네트워크 분석",
        "optimize_button":    "⚡ 네트워크 최적화",
        "restore_button":     "✅ 원래 설정 복원",
        "quit_label":         "종료",
        "status_inactive":    "📊 상태: 비활성",
        "status_active":      "✅ 활성",
        "status_passive":     "⚠️ 상태: DoH 차단됨",
        "mode_standard":      "표준형",
        "mode_obfuscated":    "난독화",
        "mode_passive":       "패시브",
        "warning_mac":        "⚠️ MAC 주소는 여전히 학교 Wi-Fi에 노출됩니다",
        "warning_dpi":        "⚠️ 학교 DPI가 DoH를 차단 시 연결이 끊길 수 있습니다",
        "warning_restore":    "⚠️ 종료 전 반드시 '원래 설정 복원'을 클릭하세요",
        "recon_complete":     "네트워크 분석 완료",
        "recon_hijack_detected": "DNS 하이재킹 감지됨. 난독화 모드를 권장합니다.",
        "recon_doh_blocked":  "이 네트워크에서는 DoH를 사용할 수 없습니다 (포트 443 차단됨)",
        "settings_title":     "설정",
        "about_title":        "정보",
        "notification_optimized": "네트워크 최적화 완료\n⚠️ MAC 주소는 학교 Wi-Fi에 노출됩니다",
        "notification_restored":  "원래 설정으로 복원되었습니다",
        "error_pfctl":        "방화벽(pfctl) 설정 오류. DNS 전용 모드로 계속합니다.",
        "error_no_wifi":      "Wi-Fi 인터페이스를 찾을 수 없습니다.",
        "first_launch_title": "안전 경고",
        "first_launch_body":  (
            "본 앱은 학교 네트워크의 제한을 우회하기 위한 도구입니다.\n\n"
            "1. MAC 주소는 노출됩니다.\n"
            "2. DPI 검열로 인해 연결이 불안정할 수 있습니다.\n"
            "3. 종료 전 반드시 원래 설정으로 복원하세요.\n"
            "4. 종료(Quit) 버튼을 누르면 자동으로 복원됩니다."
        ),
    },
    "en": {
        "analyze_button":     "🔍 Analyze Network",
        "optimize_button":    "⚡ Optimize Network",
        "restore_button":     "✅ Restore Original",
        "quit_label":         "Quit",
        "status_inactive":    "📊 Status: Inactive",
        "status_active":      "✅ Active",
        "status_passive":     "⚠️ Status: DoH Blocked",
        "mode_standard":      "Standard",
        "mode_obfuscated":    "Obfuscated",
        "mode_passive":       "Passive",
        "warning_mac":        "⚠️ MAC address remains visible to the school Wi-Fi",
        "warning_dpi":        "⚠️ Connection may drop if school DPI blocks DoH",
        "warning_restore":    "⚠️ Always click 'Restore Original' before quitting",
        "recon_complete":     "Network Analysis Complete",
        "recon_hijack_detected": "DNS hijacking detected. Obfuscated mode recommended.",
        "recon_doh_blocked":  "DoH is unavailable on this network (Port 443 blocked)",
        "settings_title":     "Settings",
        "about_title":        "About",
        "notification_optimized": "Network Optimized\n⚠️ MAC address is visible to the school Wi-Fi",
        "notification_restored":  "Restored to original settings",
        "error_pfctl":        "pfctl error. Continuing in DNS-only mode.",
        "error_no_wifi":      "Wi-Fi interface not found.",
        "first_launch_title": "Safety Warning",
        "first_launch_body":  (
            "This app bypasses school network restrictions.\n\n"
            "1. Your MAC address remains visible.\n"
            "2. Connections may be unstable due to DPI.\n"
            "3. Always restore original settings before closing.\n"
            "4. Clicking Quit will restore settings automatically."
        ),
    },
}

_current_lang = "ko"


def set_language(lang: str):
    global _current_lang
    if lang in STRINGS:
        _current_lang = lang


def t(key: str) -> str:
    return STRINGS.get(_current_lang, STRINGS["ko"]).get(key, key)
