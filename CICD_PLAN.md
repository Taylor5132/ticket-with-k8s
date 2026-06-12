# CI/CD 계획서

## 인프라 구성

### 노드 현황

| 호스트명 | IP | 역할 |
|---------|-----|------|
| lb-01 | 192.168.0.16 | Load Balancer |
| etcd-01 | 192.168.0.43 | etcd |
| etcd-02 | 192.168.0.18 | etcd |
| etcd-03 | 192.168.0.19 | etcd |
| cp-01 | 192.168.0.46 | Control Plane |
| cp-02 | 192.168.0.21 | Control Plane |
| cp-03 | 192.168.0.22 | Control Plane |
| worker-01 | 192.168.0.23 | Worker |
| worker-02 | 192.168.0.24 | Worker |
| worker-03 | 192.168.0.25 | Worker |
| worker-04 | 192.168.0.50 | Worker |
| worker-05 | 192.168.0.51 | Worker |
| harbor | 192.168.0.237 | Harbor + GitLab + Runner |

### Harbor 노드 구성 (192.168.0.237)

```
Harbor    - 컨테이너 이미지 레지스트리 (HTTPS, 이미 운영 중)
GitLab CE - 소스코드 레포 + CI 파이프라인 (port 8443)
Runner    - Shell executor (GitLab Runner)
```

---

## GitLab 레포 구성

| 레포 | 용도 |
|------|------|
| team6/app-repo | 애플리케이션 소스코드 + .gitlab-ci.yml |
| team6/manifest | K8s 배포 manifest (ArgoCD가 watching) |

---

## 빌드 대상 이미지 (모노레포)

| 서비스 | Dockerfile 경로 |
|-------|----------------|
| frontend | apps/frontend/Dockerfile |
| auth-service | services/auth-service/Dockerfile |
| event-service | services/event-service/Dockerfile |
| saved-service | services/saved-service/Dockerfile |
| booking-service (api + worker) | services/booking-service/Dockerfile |
| payment-service | services/payment-service/Dockerfile |

---

## CI/CD 파이프라인 설계

### 전체 흐름

```
개발자 코드 push (app-repo)
    ↓
GitLab Runner (Shell, 192.168.0.237)
    ↓
[CI 단계]
1. 변경된 서비스만 이미지 빌드 (rules: changes 사용)
2. 이미지 Harbor push (192.168.0.237)
3. 해당 서비스의 manifest 레포 image tag만 업데이트
    ↓
[Webhook]
GitLab manifest 레포 → ArgoCD /api/webhook (즉시 감지)
    ↓
[CD 단계]
ArgoCD (K8s Worker 노드 파드)
    ↓
K8s 클러스터에 자동 배포
```

### .gitlab-ci.yml 구조

```yaml
workflow:
  rules:
    - when: always

stages:
  - build
  - update-manifest

variables:
  HARBOR_REGISTRY: 192.168.0.237

.build_template: &build_template
  stage: build
  before_script:
    - docker login $HARBOR_REGISTRY -u $HARBOR_USER -p $HARBOR_PASSWORD

.manifest_template: &manifest_template
  stage: update-manifest
  variables:
    GIT_SSL_NO_VERIFY: "true"
  before_script:
    - git clone https://ci-manifest-token:$MANIFEST_TOKEN@192.168.0.237:8443/team6/manifest.git
    - cd manifest
    - git config user.email "ci@gitlab.local"
    - git config user.name "GitLab CI"

# build 잡: 변경된 서비스만 빌드 (rules: changes - /**/* 패턴 필수)
build-frontend:
  <<: *build_template
  script:
    - docker build -t $HARBOR_REGISTRY/booking_ticket/frontend:$CI_COMMIT_SHORT_SHA ./apps/frontend
    - docker push $HARBOR_REGISTRY/booking_ticket/frontend:$CI_COMMIT_SHORT_SHA
  rules:
    - changes:
        - apps/frontend/**/*
      when: on_success
    - when: never

# ... (build-auth, build-event, build-saved, build-booking, build-payment 동일 패턴)

# update-manifest 잡: 서비스별로 분리 → 변경된 서비스 태그만 업데이트
update-manifest-frontend:
  <<: *manifest_template
  needs: [build-frontend]
  script:
    - 'sed -i "s|image: $HARBOR_REGISTRY/booking_ticket/frontend:.*|image: $HARBOR_REGISTRY/booking_ticket/frontend:$CI_COMMIT_SHORT_SHA|g" booking/05-frontend.yaml'
    - git add .
    - git diff --cached --quiet || git commit -m "update frontend to $CI_COMMIT_SHORT_SHA"
    - git pull --rebase
    - git push
  rules:
    - changes:
        - apps/frontend/**/*
      when: on_success
    - when: never

# ... (update-manifest-auth, event, saved, booking, payment 동일 패턴)
```

**핵심 설계 결정:**
- `rules: changes`에 `/**/*` 패턴 사용 (GitLab에서 서브디렉토리 파일 감지에 필수)
- update-manifest를 서비스별로 분리 → 빌드된 서비스 태그만 업데이트 (미빌드 서비스 태그 변경 방지)
- `needs: [build-xxx]` → 빌드 성공 후에만 manifest 업데이트 실행
- `git pull --rebase` → 여러 서비스 동시 업데이트 시 충돌 방지

### CI Variables (app-repo → Settings → CI/CD → Variables)

| Key | 설명 |
|-----|------|
| HARBOR_USER | Harbor 로그인 계정 |
| HARBOR_PASSWORD | Harbor 비밀번호 |
| MANIFEST_TOKEN | manifest 레포 Project Access Token (Maintainer) |

---

## 단계별 구축 계획

### 1단계: 기본 CI/CD 파이프라인

- [x] Harbor 설치 및 운영
- [x] GitLab CE 설치 (192.168.0.237:8443)
- [x] GitLab HTTPS 설정 (Harbor 인증서 재사용)
- [x] GitLab Runner 설치 및 등록 (Shell executor, HTTPS)
- [x] team6 그룹 생성
- [x] app-repo, manifest 레포 생성 (Private)
- [x] 팀원 계정 생성 및 권한 설정 (Developer)
- [x] app-repo에 소스코드 push (GitHub → GitLab 이전)
- [x] manifest 레포에 K8s yaml 파일 push
- [x] manifest 레포 Project Access Token 발급 (ci-manifest-token, Maintainer)
- [x] CI Variables 등록 (HARBOR_USER, HARBOR_PASSWORD, MANIFEST_TOKEN)
- [x] ArgoCD 설치 (K8s 클러스터, argocd 네임스페이스)
- [x] ArgoCD manifest 레포 연결 (HTTPS)
- [x] ArgoCD Application 생성 (ticket-app, booking/)
- [x] .gitlab-ci.yml 작성 및 동작 확인
- [x] GitLab Webhook → ArgoCD 연동 (manifest push 즉시 sync)

### 2단계: 보안 스캔 추가

- [ ] Trivy 연동 (.gitlab-ci.yml에 scan stage 추가)
- [ ] SonarQube CE 설치 (Harbor 노드)
- [ ] SonarQube 연동

---

## Runner 구성

| 항목 | 내용 |
|------|------|
| 위치 | Harbor 노드 (192.168.0.237) |
| Executor | Shell |
| 이름 | team6-shell-runner |
| 범위 | Instance runner (전체 레포 공유) |
| TLS 설정 | tls-ca-file = /etc/harbor/certs/harbor.crt |

### Shell executor 선택 이유

- 학습용 랩 환경 (팀 4명, 동시 push 드묾)
- Harbor와 같은 노드 → 이미지 push 로컬 통신으로 빠름
- Worker 노드 리소스를 서비스 파드에 집중
- 설정 단순

### K8s executor 전환 조건

팀이 커지거나 동시 빌드 빈도가 높아지면 전환 고려.
전환 방법: K8s에 Runner Helm chart 설치 후 기존 Shell Runner 삭제.

---

## ArgoCD 구성

- 설치 위치: K8s 클러스터 내부 (argocd 네임스페이스)
- Worker 노드에 파드로 스케줄링
- manifest 레포를 watching하여 변경 감지 시 자동 sync
- 버전: v3.4.3

### ArgoCD 컴포넌트

| 컴포넌트 | 종류 | 역할 |
|---------|------|------|
| argocd-server | Deployment | Web UI / API |
| argocd-repo-server | Deployment | manifest 레포 clone |
| argocd-application-controller | StatefulSet | Git vs 클러스터 상태 비교 |
| argocd-dex-server | Deployment | 인증 |
| argocd-redis | Deployment | 내부 캐시 |

### 설치 명령어

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### ArgoCD Application 설정

| 항목 | 값 |
|------|-----|
| Application Name | ticket-app |
| Project | default |
| Sync Policy | Automatic |
| Repository URL | https://192.168.0.237:8443/team6/manifest.git |
| Path | booking |
| Cluster URL | https://kubernetes.default.svc |

### ArgoCD NodePort

| 프로토콜 | NodePort |
|---------|----------|
| HTTP | 32489 |
| HTTPS | 31386 |

### ArgoCD 접근

```bash
# NodePort로 외부 접근 설정
kubectl patch svc argocd-server -n argocd \
  -p '{"spec": {"type": "NodePort"}}'

# 초기 비밀번호 확인
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

---

## GitLab Webhook → ArgoCD 연동

manifest 레포 push 시 ArgoCD가 즉시 sync하도록 Webhook 설정.

| 항목 | 값 |
|------|-----|
| Webhook URL | http://192.168.0.23:32489/api/webhook |
| Trigger | Push events |
| SSL verification | 비활성화 |

**GitLab 관리자 설정 필수:**
Admin Area → Settings → Network → Outbound requests
→ "Allow requests to the local network from webhooks and integrations" 체크

---

## 네트워크

- 전체 노드: 192.168.0.x 동일 대역
- Harbor HTTPS 인증서: 전체 노드에 등록 완료
- K8s 파드 내부망(Cilium CNI)에서 Harbor 접근: 노드 IP(192.168.0.237)로 접근
