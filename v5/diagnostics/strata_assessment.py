"""Bounded evidence classification. No endpoint guesses or causal certainty."""

def session_state(sample):
    network=sample.get('network',{});warp=sample.get('warp',{});socks=sample.get('socks',{})
    count=network.get('processes',{}).get('engine')
    command=network.get('process_command',network.get('windows_command',{}))
    known=command.get('ok') is True and not network.get('parse_error',False) and type(count) is int
    engine='PRESENT' if known and count>0 else 'NOT_OBSERVED' if known else 'UNKNOWN'
    proxy='SOCKS_HANDSHAKE_OK' if socks.get('socks5_no_auth') is True else 'NOT_LISTENING' if socks.get('listening') is False else 'SOCKS_HANDSHAKE_FAILED' if socks.get('socks5_no_auth') is False else 'UNKNOWN'
    default=network.get('default',{});synthetic=network.get('synthetic',{})
    separate=bool(default.get('interface') and synthetic.get('interface') and default['interface']!=synthetic['interface'] and synthetic.get('interface_class')=='tunnel')
    dns=any(value.get('kind')=='miner_dns' for value in network.get('dns',[]))
    observed=engine=='PRESENT' and warp.get('mode')=='WarpProxy' and proxy=='SOCKS_HANDSHAKE_OK' and separate and dns
    inactive=engine=='NOT_OBSERVED' and (warp.get('mode') not in (None,'unknown','WarpProxy') or proxy=='NOT_LISTENING')
    copies=[item for item in network.get('running_miner_apps',[]) if item.get('recognized') is True]
    installed=sample.get('app',{}).get('version')
    metadata=sample.get('app',{}).get('installed_app',{'version':installed})
    different=any(item.get('identity_available') is True and item.get('matches_system_install') is False for item in copies)
    mismatch=any(any(metadata.get(key) not in (None,'unavailable','unknown') and item.get(key) not in (None,'unavailable','unknown',metadata.get(key)) for key in ('version','build','backend_version')) for item in copies)
    return {'state':'SELECTIVE_COMPONENTS_OBSERVED' if observed else 'SELECTIVE_NOT_OBSERVED' if inactive else 'NOT_VERIFIED',
            'engine_observation':engine,'proxy_observation':proxy,'synthetic_route_separate':separate,'miner_dns_observed':dns,
            'installed_version_proves_running_version':False,'different_running_copy_observed':different,'running_version_difference_observed':mismatch,
            'game_or_statistics_success_verified':False}


def assess(sample):
    windows=[value.get('error_window',{}) for location in sample.get('app',{}).get('locations',[]) for value in location.get('files',{}).values()]
    patterns=[pattern for window in windows if window.get('scope')=='since_previous_sample' for pattern in window.get('patterns',[])]
    proxy=sample.get('socks',{}).get('socks5_no_auth')
    probes=sample.get('active_probes',{})
    observed_gap=any(value.get('proxy_https',{}).get('tls_verified') and not value.get('os_https',{}).get('tls_verified') for key,value in probes.items() if key!='warp')
    session=session_state(sample)
    expected=sample.get('warp',{}).get('mode')=='WarpProxy' or session['engine_observation']=='PRESENT'
    unavailable=sample.get('socks',{}).get('listening') is False or proxy is False
    not_selected=sample.get('warp',{}).get('mode') not in (None,'unknown','WarpProxy') and session['engine_observation']=='NOT_OBSERVED'
    return {
        'actual_statistics_endpoint':'NOT_IDENTIFIED',
        'statistics_success_verified':False,
        'session':session,
        'hypotheses':[
            {'id':'H1','hypothesis':'DNS/classification gap','status':'NEEDS_INVESTIGATION' if observed_gap else 'UNCONFIRMED','evidence':'FIXED_ENDPOINT_PATH_DIFFERENCE' if observed_gap else 'NONE'},
            {'id':'H2','hypothesis':'Stale client session/cache','status':'UNCONFIRMED','evidence':'NO_CLIENT_SESSION_INSPECTION'},
            {'id':'H3','hypothesis':'Local proxy unavailable when required','status':'NOT_APPLICABLE' if not_selected else 'OBSERVED' if expected and unavailable else 'NOT_OBSERVED' if proxy is True else 'UNCONFIRMED','evidence':'LOCAL_PROXY_NOT_SELECTED' if not_selected else 'LOCAL_SOCKS_GREETING_ONLY'},
            {'id':'H4','hypothesis':'Transport error during post-game transition','status':'NEEDS_INVESTIGATION' if sample.get('phase')=='post_game' and patterns else 'UNCONFIRMED','evidence':'SANITIZED_LOG_WINDOW_NOT_REQUEST_ATTRIBUTION' if patterns else 'NONE'},
            {'id':'H5','hypothesis':'Proxy reachable while reported statistics timed out','status':'OBSERVED' if sample.get('statistics',{}).get('result')=='timeout_30s' and proxy is True else 'UNCONFIRMED','evidence':'USER_REPORT_AND_LOCAL_GREETING' if sample.get('statistics',{}).get('result')=='timeout_30s' and proxy is True else 'NONE'},
        ],
        'limitations':['HEAD is not the statistics API','No packet capture, tokens, account data or raw logs','No automatic routing changes','NOT_OBSERVED does not rule out intermittent failure'],
    }
