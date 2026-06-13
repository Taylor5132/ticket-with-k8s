# Sealed Secrets 운영 가이드

> **작성 목적**: Kubernetes Secret을 git에 안전하게 관리하기 위한 Sealed Secrets 적용 절차를 기록한다.
> **적용 일자**: 2026-06-13
> **관련 문서**: `docs/ops/ETCD_ENCRYPTION.md` (etcd 암호화 레이어)

---

## 보안 레이어 구조

Sealed Secrets와 etcd Encryption at Rest는 독립된 두 레이어다.

| 레이어 | 도구 | 보호 대상 |
|---|---|---|
| 1 | Sealed Secrets | **git 레포** — 평문 Secret 커밋 방지 |
| 2 | etcd Encryption at Rest | **etcd 스토리지** — 클러스터 내부 접근 방지 |

---

## 관리 중인 Sealed Secrets 목록

| SealedSecret 이름 | Namespace | 포함 키 | 사용처 |
|---|---|---|---|
| `kopis-sync-secret` | `backend` | DATABASE_URL, KOPIS_API_KEY | KOPIS CronJob |
| `postgres-credentials` | `db` | POSTGRES_USER, POSTGRES_PASSWORD | postgres Deployment |
| `postgres-credentials` | `backend` | POSTGRES_USER, POSTGRES_PASSWORD | 백엔드 서비스 5개 |

매니페스트 위치: `manifest/booking/14-sealed-kopis-sync.yaml`, `15-sealed-postgres-db.yaml`, `16-sealed-postgres-backend.yaml`

---

## 백엔드 서비스 Secret 참조 방식

`04-app-services.yaml`의 5개 서비스(auth, event, payment, booking-api, booking-worker)는
`postgres-credentials` Secret을 환경변수 치환으로 참조한다.

```yaml
# Kubernetes 환경변수 치환 방식 — $(VAR_NAME) 문법
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: postgres-credentials
      key: POSTGRES_PASSWORD
- name: DATABASE_URL
  value: "postgresql+psycopg://postgres:$(DB_PASSWORD)@postgres.db:5432/auth_db"
```

**주의**: `$(DB_PASSWORD)` 치환은 같은 `env` 블록 안에서 `DB_PASSWORD`가 먼저 선언되어야 동작한다.
순서가 바뀌면 치환되지 않고 리터럴 문자열 `$(DB_PASSWORD)`로 전달된다.

---

## PostgreSQL Secret 참조

`02-postgres.yaml`의 postgres Deployment는 `db` namespace의 `postgres-credentials`를 참조한다.

```yaml
- name: POSTGRES_USER
  valueFrom:
    secretKeyRef:
      name: postgres-credentials
      key: POSTGRES_USER
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: postgres-credentials
      key: POSTGRES_PASSWORD
```

---

## pub-cert.pem (공개키)

Sealed Secrets 컨트롤러의 RSA 공개키. 새 Secret을 봉인할 때 사용한다.

- **위치**: 앱 레포 루트 `pub-cert.pem`
- **git 커밋**: 안전 (공개키라 암호화에만 사용 가능, 복호화 불가)
- **갱신 시점**: 컨트롤러 키 교체 시 재발급 필요

```bash
# 공개키 재발급
kubeseal --fetch-cert \
  --controller-name=sealed-secrets-controller \
  --controller-namespace=kube-system \
  > pub-cert.pem
```

---

## Secret 재봉인 절차 (비밀번호 변경 시)

비밀번호나 API 키가 바뀌면 아래 절차로 재봉인한다.

```bash
# 1. 원본 Secret 작성 (git 커밋 금지)
cat > secret-postgres.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: postgres-credentials
  namespace: backend
type: Opaque
stringData:
  POSTGRES_USER: "postgres"
  POSTGRES_PASSWORD: "새비밀번호"
EOF

# 2. 봉인
kubeseal --cert pub-cert.pem --format yaml \
  < secret-postgres.yaml > sealed-postgres-backend.yaml

# 3. 원본 삭제
rm secret-postgres.yaml

# 4. manifest 레포 push → ArgoCD 자동 apply
```

> ⚠ namespace가 다르면 **반드시 따로 봉인**해야 한다.
> Sealed Secrets 기본 scope(`strict`)는 name + namespace 조합으로 암호화하므로
> `backend`용 봉인 파일을 `db` namespace에 apply하면 복호화 실패한다.

---

## Sealed Secrets 컨트롤러 확인

```bash
# 컨트롤러 상태
kubectl -n kube-system get pods | grep sealed-secrets

# SealedSecret 동기화 상태 확인
kubectl get sealedsecrets.bitnami.com -A

# 특정 SealedSecret 상세
kubectl -n backend describe sealedsecret kopis-sync-secret
```

`SYNCED: True`이면 컨트롤러가 복호화해 일반 Secret을 생성한 상태다.
