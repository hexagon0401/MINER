# 베타 2 학교 기록과 제보 시스템

## 현재 상태

- 앱의 내 기기 기록·학교 검색·진단·서명 보고서 내보내기와 로컬 Workers/D1 검토 서버를 구현합니다.
- 공개 운영은 하지 않습니다. 앱의 `data/community-config.json`은 `enabled:false`, 서버의 `COMMUNITY_ENABLED`도 `false`입니다. 학교 기능을 열 때 자동 제보하지 않습니다.
- 공식 NEIS API는 인증키 없이 샘플만 반환했습니다. 현재 배포용 학교 명부는 **미완료**입니다. 가짜 전국 학교 수·성공 수를 채우지 않습니다. 테스트 자료는 `fixtures/`에 분리하고 명시적으로 표시합니다.

## 명부 준비

나이스 교육정보 개방 포털의 **학교기본정보**, https://open.neis.go.kr/ 를 사용합니다. 교육청 코드와 학교 코드가 복합 식별자입니다. 초·중·고만 집계하며 명시적인 폐교·휴교 기록은 제외합니다. 동명 학교를 합치지 않습니다.

전체 API 키가 있으면 `v5`에서:

```bash
python3 -m community.catalog --fetch-neis --output community/data/schools.sqlite3
```

`NEIS_API_KEY`는 환경 변수 또는 CI Secret으로 설정합니다. 값은 로그·소스·앱에 포함하지 않습니다. 기본 샘플 응답, 반복 페이지, 누락 페이지와 수집 중 총수 변경은 거부합니다.

또는 포털에서 필터를 제거한 전체 CSV를 내려받아 **포털에 표시된 전체 행 수**와 함께 가져옵니다.

```bash
python3 -m community.catalog --csv /path/to/official.csv --expected-total PORTAL_TOTAL --as-of YYYY-MM-DD --output community/data/schools.sqlite3
```

UTF-8/CP949와 공식 한글/API 열 이름을 지원합니다. 전체 CSV 총수, 전국 17개 교육청 범위, 중복 ID와 명백한 일부 자료를 확인합니다. 출처·기준일·버전 해시·총수는 함께 기록합니다. DB는 임시 파일에서 완성한 뒤 교체하며 실패 시 기존 명부를 보존합니다. D1 가져오기는 시작 시 `catalog_ready`를 끄고 전체 반영·집계 검증 뒤에만 켭니다. 중단된 가져오기는 공개 API에서 빈 전국 현황으로 제공하지 않습니다. 원본 포털의 이용 조건과 출처 표시를 함께 유지하세요. 숫자는 원본에서 계산하며 고정된 전국 총수를 사용하지 않습니다.

## 앱 인증 흐름

설정 → 학교 현황 → 상세 내역에서 지역·학교명·학교급·깃발을 검색합니다. 내 기기와 전국 공유 범위를 구분합니다. 미개방 전국 집계는 `— / 전체 수`이며, 전체 명부 자체가 없으면 `— / —`입니다.

1. 학교 선택과 현재 학교 네트워크 사용을 본인이 확인합니다.
2. 메인 창에서 MINER를 시작하고 진단합니다. 진단은 기존 엔진 상태, 로컬 프록시, SOCKS5, TLS/WARP 경유 확인만 읽으며 경로를 변경하지 않습니다.
3. 실제 Riot/LoL 클라이언트 로그인·로비 사용을 확인합니다. 게임·영상·복귀는 별도 `pass/fail/not_tested`입니다.
4. 필수 확인을 통과하면 개인 기록에 성공을 저장합니다. 실패·미확인도 별도로 기록할 수 있습니다.
5. 제보 JSON은 선택적으로 내보냅니다. 공개 집계에는 운영자 승인이 필요합니다.

진단은 45초 제한이며 취소는 진단 프로세스에만 적용합니다. OS가 알려준 네트워크 경로 변경, 엔진 상태 변경, 학교 변경은 미저장 진단을 무효화합니다. 학교망에 실제로 있는지 또는 재학 중인지는 자동 증명하지 않습니다. Wi-Fi 내 이동을 OS가 통지하지 않는 경우까지 검출한다고 보장하지 않습니다.

초록 깃발은 누적 성공입니다. 90일이 지나도 유지하고 오래된 기록으로 표시합니다. 최근 실패는 별도 표시하며 성공 이력을 삭제하지 않습니다. 전국 공유에서는 잘못된 성공 승인이 모두 철회된 학교만 녹색에서 제외합니다.

## 보고서 계약 v1

TypeScript `src/protocol.ts`, Swift `SchoolReportBody`, `schemas/report.schema.json`과 공개 테스트 벡터가 계약을 정의합니다.

`payload`는 학교 ID·명부 버전·UTC 진단일·앱 버전·OS 주 버전·여섯 진단 결과·학교망/클라이언트 자기 확인·선택적 기능 결과·성공 여부만 포함합니다. 이름·학번·학생 계정·SSID·BSSID·IP·기기 일련번호·원본 로그는 넣지 않습니다. 전송 인프라는 접속 IP를 볼 수 있으므로, 향후 호스팅 설정에서도 접속 로그 보존을 최소화해야 합니다.

서명은 CryptoKit P256 / ECDSA SHA-256이며 공개 키는 X9.63 65바이트, 서명은 raw 64바이트의 base64url입니다. 페이로드는 UTF-8, 키 정렬, 공백 없는 JSON이고 정수·문자열·불리언·명시적 null만 씁니다. `failureCode`와 `challenge`의 null 필드는 생략하지 않습니다. 설치별 개인 키는 키체인의 앱 전용 항목에 보관합니다. **서명은 변조·동일 제출 확인 수단이며 학교 위치나 수정되지 않은 앱의 증명이 아닙니다.**

로컬 내보내기는 `challenge:null`입니다. 온라인은 서버의 5분 일회성 확인값을 포함해 다시 서명하고, 실제 POST 전에 정확한 전송 봉투를 저장합니다. 재시도는 그 봉투를 그대로 사용합니다. 온라인 진단은 10분 이내여야 합니다. 보고서 ID가 같고 내용이 다르면 충돌로 거부합니다.

## 로컬 서버 실행: 계정·배포 불필요

Node 24 이상이 개발용으로 필요합니다. 앱 사용자에게 Node는 필요하지 않습니다.

```bash
cd v5/community/server
npm ci --ignore-scripts
npm run migrate
# 아래 자료는 테스트 전용입니다. 운영 데이터로 사용하지 마세요.
python3 ../export_catalog_sql.py ../fixtures/test-catalog.sqlite3 /tmp/miner-test-schools.sql --allow-fixture
npx wrangler d1 execute miner-community --local --file /tmp/miner-test-schools.sql
npm run local-key
npm run dev
```

`local-key`는 `.gitignore`된 `.local-keys/`와 `.dev.vars`에 로컬 전용 키를 만들고 기존 키는 덮어쓰지 않습니다. 비밀키를 화면·Git·앱에 넣지 않습니다. 테스트 명부 허용은 로컬 `.dev.vars`에서만 켭니다. 앱 배포본은 로컬 HTTP 서버를 사용하지 않습니다.

| API | 의미 |
|---|---|
| `GET /healthz` | 서비스 개방 상태 |
| `GET /v1/snapshot` | 승인된 누적 학교 현황의 Ed25519 서명 봉투 |
| `POST /v1/challenges` | 공개 키에 연결한 5분 일회성 확인값 |
| `POST /v1/reports` | 서명된 제보 접수, 기본 상태 pending |

공개 API에는 검토·승인·삭제 기능이 없습니다. 요청은 16KiB 제한, 알려진 필드만 허용합니다. 설치 키당 같은 학교 하루 1건·전체 하루 3건을 제한합니다. 이는 재설치·수정 앱까지 차단하는 신원 인증이 아니므로 운영자 검토가 필수입니다.

## 운영자 검토

```bash
npm run review -- list
npm run review -- import /path/to/exported-report.json
npm run review -- approve REPORT_ID "제보 근거를 검토함" hexagon0401
npm run review -- reject REPORT_ID "추가 근거 필요" hexagon0401
npm run review -- revoke REPORT_ID "선택 학교 오류 확인" hexagon0401
```

로컬이 기본입니다. 향후 `--remote`를 명시하면 Wrangler의 소유자 계정 인증이 필요합니다. 학생 GitHub 로그인이나 앱에 저장한 관리자 토큰은 사용하지 않습니다. 오프라인 파일은 서명을 확인해 검토 대기로 가져올 뿐 자동 승인하지 않습니다.

검토 상태는 pending → approved/rejected, rejected → approved, approved → revoked입니다. 사유와 운영자명이 필요하며 DB 트리거가 상태 변경·감사 이력·스냅샷 순번을 같은 SQL 작업으로 반영합니다. 집계는 승인된 success의 고유 학교 ID로 계산합니다. 검토 시 학교별 요약을 트리거로 갱신해 조회마다 전체 보고서 이력을 스캔하지 않으며, 공개 스냅샷만 10분 캐시합니다.

서명 스냅샷에는 학교별 마지막 성공/실패 날짜만 포함하며 설치 키나 개인 보고서가 없습니다. 클라이언트는 신뢰한 공개 키·명부 버전·고유 학교 ID·집계 일치·순번을 검증하고 더 오래된 순번은 거부합니다. 통신 실패는 마지막 정상 캐시와 갱신일을 보존합니다.

## 공개 운영은 나중에

Cloudflare 로그인·D1 생성/바인딩·운영용 Ed25519 키 등록은 아직 하지 않았습니다. 공개 전에는 운영용 키를 별도로 만들고, 공식 명부를 서비스 비개방 상태에서 가져와 검증한 뒤 서버를 활성화합니다. 앱에는 실제 HTTPS 주소와 스냅샷 공개 키를 넣어 새 빌드를 배포합니다. 개발용 키·테스트 명부를 운영에 재사용하지 않습니다. 계정·도메인·공개 전환은 사용자 작업으로 남깁니다.

테스트:

```bash
npm run typecheck
npm test
# v5 폴더에서
python3 -m unittest discover -s tests -v
```
