# etcd Encryption at Rest

> **작성 목적**: Kubernetes Secret이 etcd에 평문으로 저장되는 문제를 해결하기 위해
> AES-CBC 암호화를 적용한 절차를 기록한다.
> **적용 일자**: 2026-06-13
> **적용 환경**: cp-01(192.168.0.46), cp-02(192.168.0.21), cp-03(192.168.0.22)

---

## 배경

### Kubernetes Secret의 기본 저장 방식

Kubernetes Secret의 `.data` 필드는 base64 인코딩이지 암호화가 아니다.
base64는 누구나 복원할 수 있는 인코딩 방식이며, etcd 기본 설정에서 Secret은 사실상 평문으로 저장된다.

```bash
# etcd에 직접 접근하면 Secret 내용이 노출됨 (적용 전 상태)
etcdctl get /registry/secrets/backend/google-oauth
# → 평문 데이터 출력
```

### Encryption at Rest 동작 원리

암호화/복호화는 **etcd가 아닌 API server**가 담당한다.
etcd는 그냥 바이트를 저장하고 돌려줄 뿐이며, 데이터가 암호화되어 있는지 모른다.

```
[쓰기]
kubectl create secret
    ↓
API Server → AES-256 키로 직접 암호화
    ↓
etcd → 암호화된 바이트 저장 (내용 모름)

[읽기]
kubectl get secret
    ↓
API Server → etcd에서 암호화된 바이트 수신
    ↓
API Server → 자신이 가진 AES 키로 직접 복호화
    ↓
kubectl → 평문 반환
```

### Sealed Secrets와의 관계

두 가지는 독립된 보안 레이어다.

| | Sealed Secrets | etcd Encryption at Rest |
|---|---|---|
| 보호 대상 | **git 레포** (외부 유출 방지) | **etcd 스토리지** (내부 접근 방지) |
| 동작 위치 | 클라이언트(로컬)에서 암호화 | API server에서 암호화 |
| 선행 조건 | 없음 | API server 재시작 필요 |

etcd 암호화를 먼저 적용해야 Sealed Secrets로 생성되는 Secret도
etcd에 암호화된 상태로 저장된다.

---

## 클러스터 환경 정보

이 클러스터의 etcd 인증서 경로는 일반적인 kubeadm 경로(`/etc/kubernetes/pki/etcd/`)가 아니다.
kube-apiserver.yaml에서 확인한 실제 경로:

```bash
sudo grep etcd /etc/kubernetes/manifests/kube-apiserver.yaml
# --etcd-cafile=/etc/ssl/etcd/ssl/ca.pem
# --etcd-certfile=/etc/ssl/etcd/ssl/node-cp-01.pem
# --etcd-keyfile=/etc/ssl/etcd/ssl/node-cp-01-key.pem
# --etcd-servers=https://192.168.0.43:2379,https://192.168.0.18:2379,https://192.168.0.19:2379
```

etcd는 외부 전용 VM(etcd-01/02/03)에서 실행 중이며, cp 노드에는 etcd 서버 인증서가 없고
클라이언트 인증서만 `/etc/ssl/etcd/ssl/`에 존재한다.

---

## 적용 절차

### Step 1. AES 키 생성 (cp-01에서)

```bash
sudo mkdir -p /etc/kubernetes/enc

# 32바이트 랜덤 키 생성
KEY=$(head -c 32 /dev/urandom | base64)
echo "AES 키: $KEY"
```

> ⚠️ **이 키 값은 반드시 외부에 백업해야 한다.**
> 키를 잃으면 etcd에 암호화된 Secret을 영구적으로 복호화할 수 없다.
> 백업 방법은 하단 "키 백업" 섹션 참조.

### Step 2. encryption-config.yaml 작성 (cp-01에서)

`sudo cat >` 는 리다이렉션(`>`)을 ubuntu 권한으로 처리하므로 실패한다.
반드시 `sudo tee`를 사용해야 한다.

```bash
cat <<EOF | sudo tee /etc/kubernetes/enc/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets        # Secret 오브젝트만 암호화 (ConfigMap 등은 제외)
    providers:
      - aescbc:        # 신규 쓰기: API server가 AES-CBC로 암호화
          keys:
            - name: key1
              secret: ${KEY}
      - identity: {}   # 기존 평문 읽기 허용 — 이 줄 없으면 기존 Secret 전부 읽기 불가
EOF

sudo chmod 700 /etc/kubernetes/enc
sudo chmod 600 /etc/kubernetes/enc/encryption-config.yaml
```

**provider 순서의 의미**

| 순서 | provider | 쓰기 동작 | 읽기 동작 |
|---|---|---|---|
| 첫 번째 | aescbc | 항상 이 provider로 암호화 | aescbc 복호화 시도 |
| 두 번째 | identity | 해당 없음 | aescbc 실패 시 평문으로 읽기 |

암호화 설정 전에 저장된 평문 Secret은 aescbc 복호화가 실패하고
identity로 폴백되어 읽힌다. 전환 완료 후 `identity: {}`를 제거하면
이후 평문 Secret은 읽기 불가 상태가 된다.

**파일 권한 설명**

`ubuntu` 계정에는 이 파일에 대한 접근 권한을 줄 필요가 없다.
kube-apiserver가 root로 실행되기 때문에 `root:root 600`이 올바른 설정이다.

```bash
sudo ls -la /etc/kubernetes/enc/
# -rw------- 1 root root  /etc/kubernetes/enc/encryption-config.yaml
```

### Step 3. cp-02, cp-03에 동일한 파일 배포

**반드시 동일한 KEY 값을 사용해야 한다.**
노드마다 다른 키를 쓰면 한 노드에서 암호화한 Secret을 다른 노드에서 복호화하지 못한다.

cp-01에서 ubuntu 계정 간 SSH 키가 설정되어 있지 않으므로
로컬 PC에서 각 노드에 직접 접속하여 생성한다.

```bash
# cp-01에서 /tmp로 임시 복사 (ubuntu가 읽을 수 있게)
sudo cp /etc/kubernetes/enc/encryption-config.yaml /tmp/encryption-config-backup.yaml
sudo chmod 644 /tmp/encryption-config-backup.yaml

# cp-01에서 cp-02로 전송
scp /tmp/encryption-config-backup.yaml ubuntu@192.168.0.21:~/
sudo rm /tmp/encryption-config-backup.yaml

# 로컬 PC에서 cp-02 접속
ssh ubuntu@192.168.0.21

# cp-02에서 실행
sudo mkdir -p /etc/kubernetes/enc
sudo mv ~/encryption-config-backup.yaml /etc/kubernetes/enc/encryption-config.yaml
sudo chmod 700 /etc/kubernetes/enc
sudo chmod 600 /etc/kubernetes/enc/encryption-config.yaml
sudo cat /etc/kubernetes/enc/encryption-config.yaml   # KEY 값 일치 확인

# cp-03도 동일하게 반복 (192.168.0.22)
```

### Step 4. kube-apiserver static pod manifest 수정

kube-apiserver는 static pod이므로 manifest 파일을 수정하면
kubelet이 변경을 감지하여 자동으로 재시작한다. **약 30초~1분 소요.**

cp-01부터 수정하고, Running 상태로 복구된 것을 확인한 후 cp-02, cp-03 순서로 진행한다.

```bash
# 백업 먼저
sudo cp /etc/kubernetes/manifests/kube-apiserver.yaml \
        /etc/kubernetes/kube-apiserver.yaml.bak

# 수정
sudo vi /etc/kubernetes/manifests/kube-apiserver.yaml
```

추가할 내용 3곳:

```yaml
# 1. spec.containers[0].command 섹션 끝에 추가
- --encryption-provider-config=/etc/kubernetes/enc/encryption-config.yaml

# 2. spec.containers[0].volumeMounts 섹션 끝에 추가
- mountPath: /etc/kubernetes/enc
  name: enc
  readOnly: true

# 3. spec.volumes 섹션 끝에 추가
- hostPath:
    path: /etc/kubernetes/enc
    type: DirectoryOrCreate
  name: enc
```

```bash
# 저장 후 API server 재시작 확인
watch -n 2 "kubectl -n kube-system get pods | grep apiserver"
# kube-apiserver-cp-01이 다시 Running이 될 때까지 대기

# cp-01 정상 확인 후 cp-02, cp-03 동일하게 수정
```

---

## 암호화 동작 확인

### etcdctl 설치 (cp-01에서)

cp-01에는 etcdctl이 기본 설치되어 있지 않다.
etcd 인증서가 cp-01의 `/etc/ssl/etcd/ssl/`에 있으므로 cp-01에서 설치한다.

```bash
ETCD_VER=v3.5.16
curl -L https://github.com/etcd-io/etcd/releases/download/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz \
  -o /tmp/etcd.tar.gz
tar xzf /tmp/etcd.tar.gz -C /tmp
sudo mv /tmp/etcd-${ETCD_VER}-linux-amd64/etcdctl /usr/local/bin/
sudo apt install binutils -y   # strings 명령어 포함

etcdctl version
```

### 테스트 Secret 생성 및 확인

```bash
# 테스트 Secret 생성
kubectl create secret generic test-enc --from-literal=key=value -n default

# etcd에서 직접 읽기
sudo ETCDCTL_API=3 etcdctl \
  --endpoints=https://192.168.0.43:2379 \
  --cacert=/etc/ssl/etcd/ssl/ca.pem \
  --cert=/etc/ssl/etcd/ssl/node-cp-01.pem \
  --key=/etc/ssl/etcd/ssl/node-cp-01-key.pem \
  get /registry/secrets/default/test-enc | strings | head -5

# 출력 예시 (암호화 성공):
# /registry/secrets/default/test-enc
# k8s:enc:aescbc:v1:key1:   ← 이 줄이 보이면 성공
# (이후 암호화된 바이너리 데이터)

# 테스트 Secret 삭제
kubectl delete secret test-enc -n default
```

---

## 기존 Secret 재암호화

암호화 설정 적용 전에 저장된 Secret들은 자동으로 재암호화되지 않는다.
아래 명령으로 모든 Secret을 강제로 다시 쓰면 새 write가 aescbc로 암호화된다.

```bash
kubectl get secrets --all-namespaces -o json | kubectl replace -f -
```

이 명령은 각 Secret을 읽어서 그대로 다시 쓰는 작업이다.
실패하더라도 기존 Secret은 삭제되지 않으며, 해당 Secret만 평문 상태로 남는다.

### 재암호화 확인

```bash
sudo ETCDCTL_API=3 etcdctl \
  --endpoints=https://192.168.0.43:2379 \
  --cacert=/etc/ssl/etcd/ssl/ca.pem \
  --cert=/etc/ssl/etcd/ssl/node-cp-01.pem \
  --key=/etc/ssl/etcd/ssl/node-cp-01-key.pem \
  get /registry/secrets/backend/google-oauth | strings | head -3

# k8s:enc:aescbc:v1:key1: 확인
```

---

## 키 백업

### 백업 방법 (GPG 암호화)

encryption-config.yaml에는 AES 키가 평문으로 들어있으므로 git에 올리면 안 된다.
GPG로 암호화한 후 클러스터 외부에 보관한다.

```bash
# cp-01에서 /tmp에 임시 복사
sudo cp /etc/kubernetes/enc/encryption-config.yaml /tmp/encryption-config-backup.yaml
sudo chmod 644 /tmp/encryption-config-backup.yaml

# GPG 대칭키 암호화
gpg --symmetric --cipher-algo AES256 /tmp/encryption-config-backup.yaml
# 프롬프트에서 GPG 비밀번호 입력 → encryption-config-backup.yaml.gpg 생성

# 평문 임시 파일 삭제
sudo rm /tmp/encryption-config-backup.yaml

# 로컬 PC로 복사 (로컬 PC에서 실행)
scp ubuntu@192.168.0.46:/tmp/encryption-config-backup.yaml.gpg ~/
```

### 복원 방법 (cp 노드 장애 시)

```bash
# .gpg 파일로부터 복원
gpg --decrypt encryption-config-backup.yaml.gpg > encryption-config.yaml

# 새 노드에 배포
scp encryption-config.yaml ubuntu@<새노드IP>:~/
ssh ubuntu@<새노드IP> "
  sudo mkdir -p /etc/kubernetes/enc &&
  sudo mv ~/encryption-config.yaml /etc/kubernetes/enc/ &&
  sudo chmod 700 /etc/kubernetes/enc &&
  sudo chmod 600 /etc/kubernetes/enc/encryption-config.yaml
"
```

### 보관 원칙

| 항목 | 보관 위치 | 이유 |
|---|---|---|
| `encryption-config.yaml` | 각 cp 노드 `/etc/kubernetes/enc/` | kube-apiserver 직접 사용 |
| `encryption-config-backup.yaml.gpg` | 로컬 PC 또는 USB | 노드 장애 시 복원용 |
| GPG 비밀번호 | 비밀번호 매니저 (Bitwarden, KeePassXC 등) | .gpg 복호화에 필요 |

> ⚠️ AES 키와 etcd 스냅샷을 같은 장소에 보관하지 말 것.
> 키와 암호화된 데이터가 함께 유출되면 암호화가 의미 없어진다.

---

## 주의사항

### identity provider 제거 시점

기존 Secret의 재암호화가 완료된 후 `identity: {}`를 제거할 수 있다.
제거 전 반드시 모든 Secret에 `k8s:enc:aescbc:v1:key1:`이 있는지 확인해야 한다.

제거하면 평문으로 저장된 Secret은 읽기 불가 상태가 된다.
재암호화가 완전히 끝나지 않은 상태에서 제거하면 일부 Secret이 접근 불가가 되므로 주의.

### etcd 쿼럼 위험 (K8S_STACK.md 참조)

이 클러스터는 etcd-01(192.168.0.43)과 etcd-02(192.168.0.18)가 같은 Proxmox 호스트에 있다.
해당 호스트 장애 시 쿼럼이 깨지므로 encryption-config.yaml 백업이 더욱 중요하다.
복구 시 동일한 AES 키를 새 etcd 클러스터에도 적용해야 기존 스냅샷 데이터를 읽을 수 있다.

### etcd 스냅샷과 키의 관계

etcd 스냅샷에는 암호화된 상태의 Secret이 저장된다.
스냅샷만 있고 AES 키가 없으면 Secret 데이터를 복호화할 수 없다.
**스냅샷과 키는 반드시 별도 장소에 보관해야 한다.**
