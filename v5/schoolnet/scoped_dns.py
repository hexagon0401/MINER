"""Owned macOS supplemental resolvers, journaled by network_dns.Lease."""
import os
from pathlib import Path
import re
import secrets
from .config import RIOT_DOMAINS,DNS_V4

MODE='mac_suffix_v1'
ROOT=Path('/etc/resolver')


def validate(snapshot):
    mode=snapshot.get('dns_mode')
    if mode is None:return
    if mode!=MODE or snapshot.get('system')!='Darwin':raise ValueError('Unknown DNS recovery mode')
    token=snapshot.get('resolver_token');domains=snapshot.get('resolver_domains')
    if not isinstance(token,str) or not re.fullmatch('[a-f0-9]{32}',token):raise ValueError('Invalid resolver ownership token')
    if not isinstance(domains,list) or not domains or len(domains)!=len(set(domains)) or any(d not in RIOT_DOMAINS for d in domains):raise ValueError('Invalid resolver domain plan')


def plan(root=ROOT):
    root=Path(root)
    if root.is_symlink() or root.exists() and not root.is_dir():raise ValueError('Resolver directory is not a regular directory')
    if os.name!='nt' and root.exists() and root.stat().st_mode&0o005!=0o005:raise ValueError('Existing resolver directory permissions preserved; DNS daemon cannot read it')
    domains=sorted(set(RIOT_DOMAINS))
    if any((root/d).exists() or (root/d).is_symlink() for d in domains):
        raise ValueError('Existing Riot domain resolver preserved; stop/recover the prior session or review its configuration')
    return {'dns_mode':MODE,'resolver_token':secrets.token_hex(16),'resolver_domains':domains}


def content(snapshot,domain):
    return ('# MINER STRATA scoped DNS '+snapshot['resolver_token']+'\n'
            'domain '+domain+'\nnameserver '+DNS_V4+'\nsearch_order 10000\ntimeout 2\n').encode('ascii')


def sync_directory(root):
    if os.name=='nt':return  # Portable ownership tests; live backend is macOS-only.
    fd=os.open(root,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def install(snapshot,root=ROOT):
    validate(snapshot);root=Path(root)
    if root.is_symlink():raise ValueError('Resolver directory link preserved')
    try:
        root.mkdir(mode=0o755)
        root.chmod(0o755)  # launchd helper uses umask 077; mDNSResponder must read.
    except FileExistsError:
        if not root.is_dir():raise ValueError('Resolver directory is not a directory')
    for domain in snapshot['resolver_domains']:
        path=root/domain
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o644)
        with os.fdopen(fd,'wb') as output:
            if hasattr(os,'fchmod'):os.fchmod(output.fileno(),0o644)
            else:path.chmod(0o644)
            output.write(content(snapshot,domain));output.flush();os.fsync(output.fileno())
        sync_directory(root)


def owned(path,expected):
    return not path.is_symlink() and path.is_file() and path.stat().st_size<=1024 and path.read_bytes()==expected


def active(snapshot,root=ROOT):
    validate(snapshot);root=Path(root)
    if root.is_symlink():return False
    return all(owned(root/domain,content(snapshot,domain)) for domain in snapshot['resolver_domains'])


def remove(snapshot,root=ROOT):
    validate(snapshot);root=Path(root)
    if root.is_symlink():raise ValueError('Resolver directory link preserved; recovery needs review')
    conflicts=[]
    for domain in snapshot['resolver_domains']:
        path=root/domain
        if not path.exists() and not path.is_symlink():continue
        try:matches=owned(path,content(snapshot,domain))
        except FileNotFoundError:continue
        if not matches:
            if path.exists() or path.is_symlink():conflicts.append(domain)
            continue
        try:path.unlink()
        except FileNotFoundError:pass  # Another recovery actor completed it.
    if root.is_dir():sync_directory(root)
    if conflicts:raise ValueError('Domain resolver changed externally; recovery record preserved')
