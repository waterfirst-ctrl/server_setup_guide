
# 📑 [마스터 매뉴얼] 우분투 홈 랩 서버 운영 및 원격 배포 가이드

> **📌 기본 규칙**
> 모든 코딩과 기획은 메인 PC(윈도우)에서 진행하고, 실제 배포 및 하드웨어 통제는 VS Code 원격 터널을 통해 제어합니다. 인프라 설정 오류 방지를 위해 코드 수정 후에는 지정된 안전장치 스크립트만 실행합니다.

---

## 🏗️ 0장. 서버 구축 배경 및 디렉터리 설계

### 0-1. 왜 노트북 서버를 구축했나?

클라우드(AWS·GCP) 서버는 월 비용이 발생하고, 개인 프로젝트·실험용으로는 자택에 남는 노트북 한 대를 24시간 서버로 활용하는 것이 훨씬 경제적입니다.

| 항목 | 선택 이유 |
|------|-----------|
| **Ubuntu 22.04 LTS** | 안정적인 장기 지원, 풍부한 커뮤니티 |
| **노트북(NotePC)** | 자체 배터리 UPS 내장, 소음·전력 최적 |
| **Nginx** | 정적 파일 서빙 + 리버스 프록시 동시 처리 |
| **systemd** | OS 레벨 서비스 관리, 재부팅 자동 복구 |
| **VS Code Remote Tunnels** | 사내 방화벽(SSH 22 차단) 우회 가능 |

### 0-2. 디렉터리 구조 설계

```
/home/waterfirst/
├── web/                    # 메인 정적 홈페이지 (waterfirst.pro 연결)
│   ├── index.html
│   └── banner.png
├── web_8500/               # 기존 독립 테스트 웹 (포트 8500, Docker)
├── apps/                   # React, Streamlit, FastAPI 등 앱 서비스
│   └── streamlit-sample/   # Streamlit 샘플 (포트 8501)
│       ├── app.py
│       ├── requirements.txt
│       ├── .streamlit/config.toml
│       └── venv/
├── deploy/                 # 배포 설정 초안 보관
│   ├── nginx/              # Nginx 설정 초안
│   │   └── streamlit-sample.conf
│   └── systemd/            # systemd 서비스 파일 초안
│       └── streamlit-sample.service
└── logs/                   # 앱 로그 보관
    └── streamlit-sample/
```

> **설계 원칙**: `web/`(메인 정적 페이지)는 절대 건드리지 않고, 새 앱은 `apps/` 하위에 독립 디렉터리로 격리합니다. 배포 설정 파일은 `deploy/`에만 보관하고 심볼릭 링크로 시스템에 연결합니다.

---

## 🛠️ 1장. 우분투 서버 기본 세팅 및 하드웨어 유지보수

노트북(Note PC)을 서버로 사용할 때 가장 중요한 것은 전원 관리와 프로세스 모니터링입니다.

### [상황 1] 노트북 배터리 및 전원 상태 모니터링

```bash
upower -i /org/freedesktop/UPower/devices/battery_BAT0
```

### [상황 2] 노트북 덮개 닫아도 꺼지지 않게 설정

```bash
sudo sed -i 's/#HandleLidSwitch=suspend/HandleLidSwitch=ignore/' /etc/systemd/logind.conf
sudo systemctl restart systemd-logind
```

### [상황 3] 서버 재부팅 후 자동 로그인 (headless 운영)

```bash
sudo systemctl set-default multi-user.target   # GUI 비활성화
```

### [상황 4] 도커 컨테이너 구동 현황 파악

```bash
sudo docker ps -a
```

---

## 🌐 2장. VS Code 원격 터널(Remote Tunnels) 연결 및 제어

회사 보안 방화벽(22번 SSH 포트 차단)을 완벽하게 우회하여 집 서버를 내 모니터 앞으로 소환하는 핵심 통로입니다.

### 1. 집 우분투 서버에서 터널 생성 및 영구 서비스 등록

```bash
# CLI 도구 실행 및 Microsoft/GitHub 계정 최초 연동
./code tunnel

# [인증 완료 후] 터널을 시스템 서비스로 등록하여 평생 백그라운드에서 자동 구동되게 설정
./code tunnel service install
```

### 2. 회사/외부 PC에서 집 서버 접속 방법

**[상황] 회사 PC의 VS Code 앱에서 집 서버 폴더를 직접 제어하고 싶을 때**

1. VS Code 확장(`Ctrl + Shift + X`) 탭에서 **`Remote - Tunnels`** 설치
2. 왼쪽 하단 파란색 **`><` (원격 창 열기)** 클릭 → **`Connect to Tunnel...`** 선택
3. 집 서버 세팅 시 사용한 Microsoft 계정으로 로그인 후 **`server`** 클릭
4. 연결 후 [File] → [Open Folder]를 눌러 `/home/waterfirst/web` 경로 진입

**[상황] 회사 PC에 프로그램 설치가 불가능하여 웹 브라우저로 긴급 제어해야 할 때**

```text
https://vscode.dev/tunnel/server
```

---

## 🌍 3장. IP 주소를 도메인에 연결하는 방법

### 3-1. 구성 개요

```
인터넷 사용자
    ↓
waterfirst.pro   (도메인 네임서버 → 공인 IP)
    ↓
공유기/라우터   (포트포워딩 80, 443 → 서버 내부 IP)
    ↓
우분투 서버 (Nginx)
    ↓
├── /        → /home/waterfirst/web/ (정적 페이지)
└── /app/    → 127.0.0.1:8501 (Streamlit 앱)
```

### 3-2. 단계별 설정

#### Step 1. 도메인 구입 (예: Namecheap, Gabia, 후이즈)

1. 도메인 구매 후 **DNS 관리 패널** 접속
2. **A 레코드** 추가:
   ```
   Type : A
   Host : @          (루트 도메인)
   Value: 221.153.204.191   (← 공인 IP)
   TTL  : 300 (자동)
   ```
3. **www 서브도메인**도 동일하게 추가:
   ```
   Type : A
   Host : www
   Value: 221.153.204.191
   TTL  : 300
   ```

> ⏱️ DNS 전파는 최대 48시간 소요. `dig waterfirst.pro +short` 명령으로 확인 가능

#### Step 2. 공유기 포트포워딩

집 공유기 관리자 페이지(보통 `192.168.0.1` 또는 `192.168.1.1`)에서:

| 외부 포트 | 내부 IP (서버) | 내부 포트 | 설명 |
|-----------|---------------|-----------|------|
| 80        | 192.168.x.x   | 80        | HTTP |
| 443       | 192.168.x.x   | 443       | HTTPS |

서버의 내부 IP는 `hostname -I` 명령으로 확인합니다.

#### Step 3. 공인 IP 확인

```bash
curl ifconfig.me
# 출력: 221.153.204.191  ← 이 값을 DNS A 레코드에 입력
```

> ⚠️ **유동 IP 대비**: ISP(KT·SKT·LG)에서 유동 IP를 사용하는 경우 IP가 변경될 수 있습니다.
> DDNS(Dynamic DNS) 서비스(예: Cloudflare, No-IP)를 함께 사용하면 자동으로 IP를 업데이트할 수 있습니다.

#### Step 4. HTTPS(SSL) 설정 - Certbot

```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx -y

# 인증서 자동 발급 + Nginx 설정 자동 수정
sudo certbot --nginx -d waterfirst.pro -d www.waterfirst.pro

# 자동 갱신 확인
sudo systemctl status certbot.timer
```

---

## 🚀 4장. 포트별 다중 서비스 배포 전략

### 4-1. 배포 방식 비교

| 방식 | 적합한 앱 | 특징 |
|------|-----------|------|
| **정적 파일 (Nginx)** | HTML/CSS/JS | 가장 빠름, 별도 프로세스 없음 |
| **Docker 컨테이너** | 격리가 필요한 앱 | 환경 독립, 이식성 최고 |
| **systemd + venv** | Python 앱 (Streamlit, FastAPI) | 경량, OS 통합 관리 |
| **PM2** | Node.js 앱 | JS 생태계 친화적 |

### 4-2. 메인 웹페이지 배포 (포트 80)

**[상황] 메인 웹페이지(`index.html`) 수정 및 배포**

```bash
# 직접 편집
nano /home/waterfirst/web/index.html

# 또는 cat으로 전체 덮어쓰기
sudo cat << 'EOF' > /home/waterfirst/web/index.html
<!-- 여기에 최신 HTML/CSS 코드를 붙여넣으세요 -->
EOF
```

**[상황] 코드 반영 후 화면 갱신 안 될 때**

```bash
/home/waterfirst/deploy.sh    # 마스터 치유 스크립트
```

### 4-3. Docker 기반 독립 포트 서비스 배포 (예: 포트 8500)

```bash
# 1. 포트 전용 독립 작업 디렉토리 생성
mkdir -p /home/waterfirst/web_8500

# 2. 해당 폴더에 콘텐츠 배치
cat << 'EOF' > /home/waterfirst/web_8500/index.html
<!-- 8500번 포트용 독립 웹 파일 코드 입력 -->
EOF

# 3. 8500번 포트 Nginx 컨테이너 기동
sudo docker run -d \
  --name web-server-8500 \
  -p 8500:80 \
  -v /home/waterfirst/web_8500:/usr/share/nginx/html \
  --restart always \
  nginx:alpine
```

**확인**: `http://221.153.204.191:8500`

---

## ⚡ 5장. Streamlit 앱 배포 (포트 8501, Nginx 서브경로)

앱이 늘어날수록 포트를 외부에 직접 노출하는 방식은 한계가 있습니다. **Nginx 리버스 프록시**를 사용해 하나의 도메인 아래 `/app/`, `/api/` 등 경로로 앱을 구분하는 구조가 권장됩니다.

### 5-1. Streamlit 앱 구조

```
apps/streamlit-sample/
├── app.py                  # 메인 앱 코드
├── requirements.txt        # Python 의존성
├── .streamlit/
│   └── config.toml         # 포트 8501 설정
└── venv/                   # Python 가상환경
```

### 5-2. 최초 설치

```bash
cd /home/waterfirst/apps/streamlit-sample

# Python 가상환경 생성
python3 -m venv venv

# 의존성 설치
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

### 5-3. 로컬 테스트 실행

```bash
venv/bin/streamlit run app.py
# → http://localhost:8501 에서 확인
```

### 5-4. systemd로 서비스 등록 (서버 재부팅 시 자동 시작)

```bash
# 1. 로그 디렉터리 생성
mkdir -p /home/waterfirst/logs/streamlit-sample

# 2. 시스템에 서비스 파일 심볼릭 링크 연결
sudo ln -s /home/waterfirst/deploy/systemd/streamlit-sample.service \
           /etc/systemd/system/streamlit-sample.service

# 3. systemd 재로드 및 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable --now streamlit-sample

# 4. 상태 확인
sudo systemctl status streamlit-sample
journalctl -u streamlit-sample -f
```

### 5-5. Nginx 리버스 프록시 등록 (도메인 서브경로로 노출)

```bash
# 1. Nginx 설정 파일 심볼릭 링크 연결
sudo ln -s /home/waterfirst/deploy/nginx/streamlit-sample.conf \
           /etc/nginx/sites-enabled/streamlit-sample.conf

# 2. 설정 문법 검사
sudo nginx -t

# 3. Nginx 재로드
sudo systemctl reload nginx
```

완료 후 `https://waterfirst.pro/app/` 으로 접속하면 Streamlit 앱이 표시됩니다.

### 5-6. 트래픽 흐름 요약

```
브라우저 요청: https://waterfirst.pro/app/
        ↓
Nginx (포트 443/80)
        ↓  proxy_pass
Streamlit (127.0.0.1:8501)  ← 외부에 직접 노출 안 됨
```

---

## 📁 6장. 새 앱 추가 시 체크리스트

새 서비스(예: FastAPI, React)를 추가할 때마다 아래 절차를 따릅니다.

```
[ ] 1. apps/<앱이름>/ 디렉터리 생성 및 코드 배치
[ ] 2. 내부 포트 결정 (8502, 8503 ... 순서대로)
[ ] 3. deploy/systemd/<앱이름>.service 작성
[ ] 4. deploy/nginx/<앱이름>.conf 작성 (location /경로/ 블록 추가)
[ ] 5. logs/<앱이름>/ 디렉터리 생성
[ ] 6. systemd 서비스 등록 및 활성화
[ ] 7. nginx -t 후 reload
[ ] 8. 도메인 서브경로로 접속 확인
```

### 앱 포트 할당 현황

| 앱 | 내부 포트 | 공개 경로 | 관리 방식 |
|----|-----------|-----------|-----------|
| 메인 홈페이지 | 80 (직접) | `waterfirst.pro/` | Nginx 정적 |
| 테스트 웹 | 8500 | `waterfirst.pro:8500` | Docker |
| streamlit-sample | 8501 | `waterfirst.pro/app/` | systemd + Nginx |
| (다음 앱) | 8502 | `waterfirst.pro/next/` | systemd + Nginx |

---

## 🔍 7장. 자주 쓰는 운영 명령어 모음

```bash
# ── 서비스 관리 ────────────────────────────────────────────────
sudo systemctl status streamlit-sample    # 상태 확인
sudo systemctl restart streamlit-sample   # 재시작
sudo systemctl stop streamlit-sample      # 중지
journalctl -u streamlit-sample -f         # 실시간 로그

# ── Nginx ──────────────────────────────────────────────────────
sudo nginx -t                             # 설정 문법 검사
sudo systemctl reload nginx               # 무중단 재로드
sudo systemctl status nginx               # 상태 확인

# ── Docker ─────────────────────────────────────────────────────
sudo docker ps -a                         # 전체 컨테이너 목록
sudo docker logs web-server-8500 -f       # 컨테이너 로그
sudo docker restart web-server-8500       # 컨테이너 재시작

# ── 네트워크 ────────────────────────────────────────────────────
curl ifconfig.me                          # 공인 IP 확인
dig waterfirst.pro +short                 # DNS 확인
ss -tlnp | grep LISTEN                    # 열린 포트 목록
```

---

## 📝 변경 이력

| 날짜 | 변경 내용 |
|------|-----------|
| 2026-07-04 | 🔧 트러블슈팅 보고서에 7장(효과적인 포트 관리 방안 — 다중 포트 vs Nginx 게이트웨이, 성능 판단 기준) 추가 |
| 2026-07-04 | 🔧 트러블슈팅 보고서에 문제⑥(멀티 호스팅 시 정적 사이트 `/` 404 — 홈 디렉터리 통과 권한) 추가 |
| 2026-07-04 | 🔧 [트러블슈팅 보고서](docs/troubleshooting-ip-port-nginx.md) 추가 — IP/포트 → 도메인 서브경로 배포 문제 해결 과정, Nginx conf 동작 버전 반영 |
| 2026-07-04 | 0장(배경·디렉터리 설계), 3장(IP→도메인), 5장(Streamlit 배포), 6장(신규 앱 체크리스트) 추가 |
| 초기 | 기본 우분투 세팅, VS Code Tunnel, Docker 멀티포트 배포 가이드 작성 |
