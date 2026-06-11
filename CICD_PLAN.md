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
3. manifest 레포 image tag 업데이트
    ↓
[CD 단계]
ArgoCD (K8s Worker 노드 파드)
    ↓
manifest 레포 변경 감지
    ↓
K8s 클러스터에 자동 배포
```

### .gitlab-ci.yml 구조

```yaml
stages:
  - build
  - update-manifest

variables:
  HARBOR_REGISTRY: 192.168.0.237

.build_template: &build_template
  stage: build
  before_script:
    - docker login $HARBOR_REGISTRY -u $HARBOR_USER -p $HARBOR_PASSWORD

build-frontend:
  <<: *build_template
  script:
    - docker build -t $HARBOR_REGISTRY/booking_ticket/frontend:$CI_COMMIT_SHORT_SHA ./apps/frontend
    - docker push $HARBOR_REGISTRY/booking_ticket/frontend:$CI_COMMIT_SHORT_SHA
  rules:
    - changes:
        - apps/frontend/**

build-auth:
  <<: *build_template
  script:
    - docker build -t $HARBOR_REGISTRY/booking_ticket/auth-service:$CI_COMMIT_SHORT_SHA ./services/auth-service
    - docker push $HARBOR_REGISTRY/booking_ticket/auth-service:$CI_COMMIT_SHORT_SHA
  rules:
    - changes:
        - services/auth-service/**

build-event:
  <<: *build_template
  script:
    - docker build -t $HARBOR_REGISTRY/booking_ticket/event-service:$CI_COMMIT_SHORT_SHA ./services/event-service
    - docker push $HARBOR_REGISTRY/booking_ticket/event-service:$CI_COMMIT_SHORT_SHA
  rules:
    - changes:
        - services/event-service/**

build-saved:
  <<: *build_template
  script:
    - docker build -t $HARBOR_REGISTRY/booking_ticket/saved-service:$CI_COMMIT_SHORT_SHA ./services/saved-service
    - docker push $HARBOR_REGISTRY/booking_ticket/saved-service:$CI_COMMIT_SHORT_SHA
  rules:
    - changes:
        - services/saved-service/**

build-booking:
  <<: *build_template
  script:
    - docker build -t $HARBOR_REGISTRY/booking_ticket/booking-api:$CI_COMMIT_SHORT_SHA ./services/booking-service
    - docker push $HARBOR_REGISTRY/booking_ticket/booking-api:$CI_COMMIT_SHORT_SHA
  rules:
    - changes:
        - services/booking-service/**

build-payment:
  <<: *build_template
  script:
    - docker build -t $HARBOR_REGISTRY/booking_ticket/payment-service:$CI_COMMIT_SHORT_SHA ./services/payment-service
    - docker push $HARBOR_REGISTRY/booking_ticket/payment-service:$CI_COMMIT_SHORT_SHA
  rules:
    - changes:
        - services/payment-service/**

update-manifest:
  stage: update-manifest
  script:
    - git clone https://ci-manifest-token:$MANIFEST_TOKEN@192.168.0.237:8443/team6/manifest.git
    - cd manifest
    - git config user.email "ci@gitlab.local"
    - git config user.name "GitLab CI"
    - |
      for service in frontend auth-service event-service saved-service booking-api booking-worker payment-service; do
        sed -i "s|image: $HARBOR_REGISTRY/booking_ticket/$service:.*|image: $HARBOR_REGISTRY/booking_ticket/$service:$CI_COMMIT_SHORT_SHA|g" booking/04-app-services.yaml
      done
    - git add .
    - git commit -m "update image tags to $CI_COMMIT_SHORT_SHA"
    - git push
  rules:
    - changes:
        - apps/**
        - services/**
```

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
- [ ] .gitlab-ci.yml 작성 후 app-repo push
- [ ] 파이프라인 동작 확인

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

## 네트워크

- 전체 노드: 192.168.0.x 동일 대역
- Harbor HTTPS 인증서: 전체 노드에 등록 완료
- K8s 파드 내부망(Cilium CNI)에서 Harbor 접근: 노드 IP(192.168.0.237)로 접근
