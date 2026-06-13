# KOPIS 공연 데이터 동기화 CronJob

KOPIS OpenAPI에서 공연 정보를 매일 `event_db`에 동기화하는 스크립트 모음입니다.

## 파일 구조

```
cron/
├── daily_update_data.py   # KOPIS API → DB 동기화
├── daily_delete_data.py   # 만료 공연 삭제
├── pyproject.toml         # Python 의존성
└── Dockerfile             # 컨테이너 이미지 빌드
```

---

## 스크립트 설명

### daily_update_data.py

KOPIS OpenAPI에서 공연 정보를 수집해 `event_db`에 upsert합니다.

**수집 범위**: 오늘 ~ 오늘 +365일

**동작 순서**
1. 공연 목록 수집 (31일 단위 윈도우로 페이지네이션)
2. 공연별 상세 정보 조회 (출연진, 런타임, 소개 이미지 등)
3. 새 공연장(`venues`) 발견 시 API 조회 후 insert
4. `kopis_id` UNIQUE 제약 기반 upsert — 기존 데이터는 UPDATE, 신규 데이터는 INSERT

**연동 테이블**

| 테이블 | 주요 컬럼 |
|---|---|
| `venues` | kopis_id, name, address, province, district, seat_capacity, phone, latitude, longitude, halls_text |
| `performances` | kopis_id, venue_id, title, start_date, end_date, poster_url, genre, status, is_open_run, cast_text, runtime, age_rating, description, intro_image_urls, schedule |

**KOPIS API 엔드포인트**

| 용도 | 엔드포인트 |
|---|---|
| 공연 목록 | `GET /pblprfr?service=&stdate=&eddate=&cpage=&rows=` |
| 공연 상세 | `GET /pblprfr/{mt20id}?service=` |
| 공연장 상세 | `GET /prfplc/{mt10id}?service=` |

---

### daily_delete_data.py

`end_date`가 오늘 이전인 공연을 `performances` 테이블에서 삭제합니다.

```sql
DELETE FROM performances WHERE end_date < 오늘
```

---

## 환경변수

| 변수명 | 설명 | 예시 |
|---|---|---|
| `DATABASE_URL` | PostgreSQL 접속 URL | `postgresql://postgres:postgres@postgres:5432/event_db` |
| `KOPIS_API_KEY` | KOPIS OpenAPI 서비스 키 | `<발급받은 서비스 키>` (실키를 문서에 커밋하지 말 것) |

---

## 로컬 실행

```bash
pip install requests "psycopg[binary]"

# 동기화
DATABASE_URL=postgresql://postgres:비밀번호@localhost:5432/event_db \
KOPIS_API_KEY=발급받은키 \
python daily_update_data.py

# 삭제
DATABASE_URL=postgresql://postgres:비밀번호@localhost:5432/event_db \
python daily_delete_data.py
```

---

## Docker 이미지 빌드

```bash
docker build -t 192.168.0.237/booking_ticket/kopis-sync:latest .
docker push 192.168.0.237/booking_ticket/kopis-sync:latest
```

> ⚠ 이미지의 의존성은 uv 가상환경(`/app/.venv`)에 설치되므로 컨테이너 실행 명령은 반드시 `uv run python ...` (또는 `/app/.venv/bin/python`)이어야 한다. 맨 `python`으로 실행하면 시스템 인터프리터가 사용돼 `ModuleNotFoundError`가 난다.


---

## Kubernetes 배포

동일 이미지를 사용하는 CronJob 2개로 구성합니다.

| CronJob | 스케줄 (KST) | 실행 명령 |
|---|---|---|
| `kopis-daily-update` | `0 3 * * *` (매일 새벽 3시) | `uv run python daily_update_data.py` |
| `kopis-daily-delete` | `0 4 * * *` (매일 새벽 4시) | `uv run python daily_delete_data.py` |

- Namespace: `backend` — NetworkPolicy `allow-postgres-from-backend` 규칙에 의해 `db` 네임스페이스의 postgres:5432 접근이 허용됨
- DATABASE_URL 호스트: `postgres.db:5432` (postgres는 `db` 네임스페이스에 있음)
- Image: `192.168.0.237/booking_ticket/kopis-sync:latest`
- 환경변수: `DATABASE_URL`, `KOPIS_API_KEY` 모두 Secret → Sealed Secrets로 관리 (아래 참조)

### CronJob 주요 설정

```yaml
spec:
  concurrencyPolicy: Forbid          # 이전 실행 중이면 새 실행 건너뜀
  successfulJobsHistoryLimit: 1      # 성공 Job 1개만 보존 (로그 확인용)
  failedJobsHistoryLimit: 1          # 실패 Job 1개만 보존
  jobTemplate:
    spec:
      activeDeadlineSeconds: 3600    # 1시간 초과 시 강제 종료
      template:
        spec:
          restartPolicy: Never       # 실패 시 새 Pod 생성 (OnFailure 아님)
```

**`restartPolicy: Never` vs `OnFailure`**

| | `Never` | `OnFailure` |
|---|---|---|
| 실패 시 동작 | 새 Pod 생성 | 같은 Pod 내 컨테이너 재시작 |
| 로그 | 시도마다 Pod 분리 → 디버깅 용이 | 이전 시도 로그 덮어써짐 |
| 리소스 | 약간 무거움 | 가벼움 |

upsert 기반 배치 스크립트는 처음부터 재실행해도 안전하므로 `Never`가 적합하다.

**`activeDeadlineSeconds` 필요성**

KOPIS API 무응답 시 스크립트가 무한 대기할 수 있다. 3600초(1시간) 제한으로 hung Job을 자동 종료한다.

### 수동 테스트

```bash
# 수동으로 Job 실행
kubectl -n backend create job kopis-test --from=cronjob/kopis-daily-update

# 완료 대기 후 로그 확인
kubectl -n backend get pods | grep kopis-test
kubectl -n backend logs <pod-name>

# 테스트 Job 정리
kubectl -n backend delete job kopis-test
```

> ⚠ **Python stdout 버퍼링**: `kubectl logs -f`로 실시간 스트리밍이 안 될 수 있다.
> 컨테이너에 `PYTHONUNBUFFERED=1` 환경변수를 추가하면 해결된다.

> ⚠ **postgres 재시작 주의**: Job이 실행 중인 상태에서 postgres Pod를 재시작하면
> WAL 손상이 발생할 수 있다. Job 완료 후 postgres 변경을 적용할 것.

### CronJob 시간대(Timezone) 설정

CronJob의 schedule은 **기본값이 UTC**다. KST 기준 새벽 3시/4시에 실행하려면 두 곳에 모두 설정해야 한다.

**① CronJob spec의 `timeZone` 필드 (Kubernetes 1.27+ GA)**

```yaml
# 공식 문서: https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/#time-zones
spec:
  schedule: "0 3 * * *"
  timeZone: "Asia/Seoul"   # IANA tz database 이름 사용
```

`timeZone` 필드는 K8s 1.24 alpha → 1.25 beta → **1.27에서 stable(GA)** 로 졸업했다.
1.27 미만 버전에서는 `CronJobTimeZone` feature gate를 별도로 활성화해야 한다.
이 설정이 **job이 언제 실행될지**를 결정한다.

**② Dockerfile/컨테이너의 `TZ` 환경변수**

```dockerfile
ENV TZ=Asia/Seoul
```

이 설정이 **컨테이너 내 Python `date.today()`가 어느 날짜를 반환할지**를 결정한다.
설정하지 않으면 `date.today()`가 UTC 기준 날짜를 반환한다.

KST 새벽 4시 = UTC 전날 19시이므로, TZ 미설정 시 `daily_delete_data.py`의
`DELETE FROM performances WHERE end_date < 오늘`이 전날 날짜 기준으로 실행된다.
→ 당일 만료 공연이 삭제되지 않는다.

**두 설정의 역할 차이**

| 설정 | 위치 | 영향 범위 |
|---|---|---|
| `timeZone: "Asia/Seoul"` | CronJob spec | Job이 **언제 기동되는지** |
| `ENV TZ=Asia/Seoul` | Dockerfile | 컨테이너 내 `date.today()` **반환 날짜** |

---

## Secret / ConfigMap 관리

### 분류 기준

| 항목 | 종류 | 이유 |
|---|---|---|
| `DATABASE_URL` | **Secret** | postgres 비밀번호 포함 |
| `KOPIS_API_KEY` | **Secret** | 외부 API 키, 유출 시 차단/과금 위험 |
| `KOPIS_BASE_URL` | ConfigMap | 공개 URL, 노출돼도 무해 |
| 동기화 날짜 범위, 배치 크기 | ConfigMap | 운영 파라미터 |

### Sealed Secrets 사용 (채택)

**왜 Secret YAML을 그대로 git에 올리면 안 되는가**

Kubernetes Secret의 `.data`는 base64 인코딩이지 암호화가 아니다.
`echo "0f4460e0934c4fd19f5dbb034c66bafa" | base64 -d` 처럼 누구나 복원할 수 있다.
git에 평문 Secret을 커밋하면 히스토리에 영구히 남는다.

**Sealed Secrets 동작 원리**

```
[컨트롤러 설치]
  클러스터에 sealed-secrets-controller 배포
  → RSA-4096 키 쌍 자동 생성
  → 공개키(X.509 PEM)를 클러스터 외부에서 fetch 가능

[시크릿 봉인 — 로컬에서]
  kubeseal --fetch-cert > pub-cert.pem   # 공개키 다운로드 (git에 올려도 안전)
  kubeseal --cert pub-cert.pem --format yaml < secret.yaml > sealed-secret.yaml
  git add sealed-secret.yaml             # 암호화된 파일만 커밋

[복호화 — 클러스터에서 자동]
  kubectl apply -f sealed-secret.yaml
  → controller가 개인키로 복호화 → 일반 Secret 생성
```

**인증서 포맷 및 봉인 범위(scope)**

Sealed Secrets의 공개키는 항상 **X.509 PEM 포맷**이다.
봉인 범위는 3가지이며, 이 프로젝트에는 `strict`(기본값)이 적합하다.

| Scope | 봉인 대상 | 특징 |
|---|---|---|
| `strict` (기본) | name + namespace 고정 | 가장 안전. 다른 이름/NS에 적용 불가 |
| `namespace-wide` | namespace만 고정 | NS 내에서 이름 변경 가능 |
| `cluster-wide` | 제한 없음 | 어느 NS에나 적용 가능 (권한 필요) |

`kopis-sync-secret`은 name=`kopis-sync-secret`, namespace=`backend`로 고정이므로
`strict` scope 사용이 올바르다.

**적용 절차**

```bash
# 1. Sealed Secrets 컨트롤러 설치 (클러스터)
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml

# 2. kubeseal CLI 설치 (로컬)
# https://github.com/bitnami-labs/sealed-secrets/releases

# 3. 공개키 fetch (git에 커밋해도 안전)
kubeseal --fetch-cert \
  --controller-name=sealed-secrets-controller \
  --controller-namespace=kube-system \
  > pub-cert.pem

# 4. 원본 Secret 작성 (git에 절대 올리지 않음 — .gitignore에 추가)
cat > secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: kopis-sync-secret
  namespace: backend
type: Opaque
stringData:
  DATABASE_URL: "postgresql://postgres:<실제비밀번호>@postgres.db:5432/event_db"
  KOPIS_API_KEY: "<실제API키>"
EOF

# 5. 봉인 (strict scope = 기본값)
kubeseal --cert pub-cert.pem --format yaml < secret.yaml > sealed-secret.yaml

# 6. sealed-secret.yaml만 git에 커밋, secret.yaml은 삭제
git add sealed-secret.yaml pub-cert.pem
echo "secret.yaml" >> .gitignore
rm secret.yaml
```

---

## 백업 전략

### etcd와 Secret 저장 방식

Kubernetes는 모든 오브젝트(Secret 포함)를 etcd에 저장한다.
Secret의 `.data`는 base64일 뿐이며, **etcd 기본 설정에서는 평문으로 저장된다.**

```bash
# etcd에서 직접 Secret 값을 읽는 예시 (평문 노출)
ETCDCTL_API=3 etcdctl \
  --endpoints=https://192.168.0.43:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  get /registry/secrets/backend/kopis-sync-secret
```

### etcd Encryption at Rest (권장)

`EncryptionConfiguration`을 통해 etcd에 저장되는 Secret을 AES-GCM/AES-CBC로 암호화할 수 있다.
공식 문서: https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/

**기존 오브젝트와의 충돌 여부**: 충돌은 없다. 단, 암호화 설정을 적용해도
**기존에 저장된 데이터는 자동으로 재암호화되지 않는다.**
설정 후 아래 명령으로 강제 재암호화해야 한다.

```bash
# 모든 Secret 강제 재암호화 (암호화 설정 적용 후 1회 실행)
kubectl get secrets --all-namespaces -o json | kubectl replace -f -
```

**중요**: provider 순서가 읽기/쓰기 동작을 결정한다.
기존 평문 데이터가 있는 상태에서 전환할 때는 `identity`를 두 번째 provider로
유지해야 기존 데이터 읽기가 깨지지 않는다.

```yaml
# /etc/kubernetes/enc/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:              # 신규 쓰기: 암호화
          keys:
            - name: key1
              secret: <base64-32바이트-키>
      - identity: {}         # 기존 평문 읽기 허용
```

이 프로젝트처럼 **Sealed Secrets를 사용하면** etcd 암호화 없이도
KOPIS_API_KEY 등의 실제 값이 git에 평문으로 노출되는 문제는 해결된다.
다만 etcd 자체에 접근 권한이 있는 공격자 시나리오까지 막으려면
Encryption at Rest도 적용하는 것이 완전한 Defense in Depth다.

### etcd 스냅샷 백업

etcd 스냅샷은 클러스터 전체 상태를 복원할 수 있는 가장 확실한 백업 방법이다.
Secret, ConfigMap, Deployment 등 모든 K8s 오브젝트가 포함된다.
**Sealed Secrets 컨트롤러의 개인키도 etcd에 저장되므로 스냅샷에 포함된다.**

```bash
# 스냅샷 저장 (etcd 노드에서 실행)
ETCDCTL_API=3 etcdctl \
  --endpoints=https://192.168.0.43:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-$(date +%Y%m%d-%H%M%S).db

# 스냅샷 상태 확인
etcdctl snapshot status /backup/etcd-20260613-030000.db --write-out=table

# 복원 (클러스터 중단 후 실행)
etcdctl snapshot restore /backup/etcd-20260613-030000.db \
  --data-dir=/var/lib/etcd-restored
```

**이 프로젝트 etcd 구성 주의사항** (`K8S_STACK.md` 참조)

| etcd 노드 | 호스트 | 위험 |
|---|---|---|
| etcd-01 (192.168.0.43) | k8s | ⚠ |
| etcd-02 (192.168.0.18) | k8s | ⚠ 동일 Proxmox 호스트 |
| etcd-03 (192.168.0.19) | k8s2 | 안전 |

etcd-01과 etcd-02가 같은 Proxmox 호스트(`k8s`)에 있으므로
해당 호스트 장애 시 쿼럼이 깨진다 (3노드 중 2개 손실).
스냅샷은 3개 노드 중 **리더 노드**에서 찍는 것이 권장되며,
cron으로 자동화하는 것이 좋다.

```bash
# crontab — 매일 새벽 2시 스냅샷 (K8s CronJob 실행 1시간 전)
0 2 * * * ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-$(date +\%Y\%m\%d).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

**백업 계층 요약**

| 계층 | 방법 | 복원 범위 |
|---|---|---|
| Secret 소스 | Sealed Secrets YAML (git) | 개별 Secret 재배포 |
| 클러스터 전체 | etcd 스냅샷 | 전체 상태 복원 |
| 이미지 | Harbor 레지스트리 | 컨테이너 이미지 |
