"""Bounded evidence classification. No endpoint guesses or causal certainty."""


def assess(sample):
    windows=[value.get('error_window',{}) for location in sample.get('app',{}).get('locations',[]) for value in location.get('files',{}).values()]
    patterns=[pattern for window in windows for pattern in window.get('patterns',[])]
    proxy=sample.get('socks',{}).get('socks5_no_auth')
    probes=sample.get('active_probes',{})
    observed_gap=any(value.get('proxy_https',{}).get('tls_verified') and not value.get('os_https',{}).get('tls_verified') for key,value in probes.items() if key!='warp')
    return {
        'actual_statistics_endpoint':'NOT_IDENTIFIED',
        'statistics_success_verified':False,
        'hypotheses':[
            {'id':'H1','hypothesis':'DNS/classification gap','status':'NEEDS_INVESTIGATION' if observed_gap else 'UNCONFIRMED','evidence':'FIXED_ENDPOINT_PATH_DIFFERENCE' if observed_gap else 'NONE'},
            {'id':'H2','hypothesis':'Stale client session/cache','status':'UNCONFIRMED','evidence':'NO_CLIENT_SESSION_INSPECTION'},
            {'id':'H3','hypothesis':'Local proxy unavailable','status':'OBSERVED' if proxy is False else 'NOT_OBSERVED' if proxy is True else 'UNCONFIRMED','evidence':'LOCAL_SOCKS_GREETING_ONLY'},
            {'id':'H4','hypothesis':'Transport error during post-game transition','status':'NEEDS_INVESTIGATION' if sample.get('phase')=='post_game' and patterns else 'UNCONFIRMED','evidence':'SANITIZED_LOG_WINDOW_NOT_REQUEST_ATTRIBUTION' if patterns else 'NONE'},
            {'id':'H5','hypothesis':'Health label differs from actual statistics result','status':'OBSERVED' if sample.get('statistics',{}).get('result')=='timeout_30s' and proxy is True else 'UNCONFIRMED','evidence':'USER_REPORT_AND_LOCAL_GREETING' if sample.get('statistics',{}).get('result')=='timeout_30s' and proxy is True else 'NONE'},
        ],
        'limitations':['HEAD is not the statistics API','No packet capture, tokens, account data or raw logs','No automatic routing changes','NOT_OBSERVED does not rule out intermittent failure'],
    }
