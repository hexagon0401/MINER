"""Native macOS fixture: observe an inert client's loopback TCP, not Riot traffic."""
import json
from pathlib import Path
import socket
import subprocess
import zipfile


def run(binary, work):
    work = Path(work) / 'client-flow-fixture'
    work.mkdir()
    executable = work / ('long path with spaces ' * 6) / 'LeagueClient'
    executable.parent.mkdir()
    source = work / 'idle-client.c'
    source.write_text('#include <unistd.h>\n#include <stdlib.h>\n#include <arpa/inet.h>\n'
                      'int main(int argc,char **argv){if(argc!=2)return 2;int s=socket(AF_INET,SOCK_STREAM,0);'
                      'struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);'
                      'a.sin_port=htons(atoi(argv[1]));if(connect(s,(void*)&a,sizeof(a)))return 3;for(;;)pause();}\n')
    subprocess.run(['/usr/bin/clang', str(source), '-o', str(executable)], check=True, timeout=30)
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(executable)], check=True, timeout=15)
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0)); server.listen(); server.settimeout(5)
        child = subprocess.Popen([str(executable), str(server.getsockname()[1])])
        try:
            accepted, _ = server.accept()
            with accepted:
                report = work / 'client.zip'
                subprocess.run([str(binary), '--phase', 'error', '--client-event', 'presence_mismatch', '--output', str(report)], check=True, timeout=80)
                with zipfile.ZipFile(report) as z: row = json.loads(z.read('report.json'))['samples'][0]
                transport = row['client_transport']
                assert transport['query_ok'], 'Native client socket enumeration failed'
                assert any(f['role'] == 'league_backend' and f['destination_class'] == 'loopback' and f['tcp_state'] == 'ESTABLISHED' for f in transport['flows'])
                assert row['client_event']['kind'] == 'presence_mismatch'
                assert row['client_event']['delivery_verified_by_tool'] is False
                assert '127.0.0.1' not in json.dumps(transport) and str(executable) not in json.dumps(row)
                assert child.poll() is None, 'Recorder terminated fixture process'
                return True
        finally:
            child.terminate()
            child.wait(timeout=5)
