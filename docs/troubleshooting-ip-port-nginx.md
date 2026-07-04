# 🔧 트러블슈팅 보고서 — IP/포트에서 도메인 서브경로까지 (Streamlit + Nginx)

> **대상 서비스**: `apps/streamlit-sample` (Streamlit, 내부 포트 8501)
> **목표 URL**: `http://waterfirst.pro/app/`
> **환경**: Ubuntu 24.04 (Samsung 노트북 서버 `waterfirst-550XBE-350XBE`), Nginx 1.24.0, Docker
> **결론**: `127.0.0.1:8501` 로만 떠 있던 Streamlit 앱을, 포트를 외부에 직접 열지 않고 **Nginx 리버스 프록시**를 통해 `waterfirst.pro/app/` 서브경로로 공개하는 데 성공.

---

## 1. 전체 네트워크 구조 이해 (IP가 3개 존재한다)

서버에서 앱을 실행하면 접근 주소가 **계층별로 3개** 존재합니다. 이걸 헷갈리면 "왜 내 PC에선 되는데 외부에선 안 되지?" 에서 막힙니다.

```
인터넷
  │  waterfirst.pro = 221.153.204.191 (공인 IP)
  ▼
공유기 (192.168.x.1) ── 포트포워딩 80/443 ──▶ 서버로 전달
  ▼
Ubuntu 서버 (내부 IP 192.168.x.x)
  ├─ Nginx        : 0.0.0.0:80   ◀── 외부 트래픽 수신 (관문)
  │     ├─ location /      → /home/waterfirst/web  (정적 홈페이지)
  │     └─ location /app/  → proxy_pass 127.0.0.1:8501
  └─ Streamlit    : 127.0.0.1:8501  ◀── 루프백에만 바인드 (외부 직접 접근 불가)
```

| 주소 | 누가 접속 가능? | 용도 |
|------|----------------|------|
| `127.0.0.1:8501` | 서버 자기 자신만 (루프백) | 앱 백엔드. **외부 노출 안 함** |
| `192.168.x.x:8501` | 같은 공유기 LAN 기기 | 집 내부 테스트 |
| `221.153.204.191:8501` | 포트포워딩 열면 전세계 | IP:포트 직접 노출 (비권장) |
| `waterfirst.pro/app/` | 전세계 | **Nginx 경유 (권장 방식)** |

**핵심 원칙**: 앱은 `127.0.0.1`에만 바인드하고, 외부 노출·HTTPS·경로 라우팅은 전부 **Nginx** 한 곳에서 처리한다. 그래야 앱마다 포트를 열 필요 없이 `/app/`, `/api/` 같은 경로로 여러 서비스를 통합 관리할 수 있다.

---

## 2. 접속 방식 두 가지 비교

|  | 방법 A: IP:포트 직접 | 방법 B: Nginx 도메인 경유 |
|---|---|---|
| URL | `http://221.153.204.191:8501` | `https://waterfirst.pro/app/` |
| 앱 바인드 | `address = "0.0.0.0"` | `address = "127.0.0.1"` |
| 공유기 포트포워딩 | 8501 열어야 함 | 80/443만 (8501 닫아도 됨) |
| HTTPS | 적용 어려움 | Certbot 자동 |
| 여러 앱 | 앱마다 포트 1개 | 경로(`/app/`, `/api/`)로 통합 |
| 권장 | 개발/테스트 | **운영 서비스** |

이 보고서는 최종적으로 **방법 B**를 채택했다. 그 과정에서 만난 5개의 문제와 해결을 아래에 순서대로 기록한다.

---

## 3. 발생한 문제와 해결 (시간순)

### 문제 ① Nginx가 아예 설치되어 있지 않았다

```
ln: failed to create symbolic link '/etc/nginx/sites-enabled/streamlit-sample.conf': No such file or directory
```

- **원인**: `sites-enabled/` 디렉터리가 없음 = Nginx 미설치 상태였다.
- **해결**:
  ```bash
  sudo apt update
  sudo apt install nginx -y
  ```
- 설치 후 `/etc/nginx/sites-available/`, `/etc/nginx/sites-enabled/` 가 자동 생성됨을 확인.

---

### 문제 ② 포트 80을 Docker 컨테이너가 이미 점유 중

설치 로그 마지막 줄:
```
Not attempting to start NGINX, port 80 is already in use.
```

- **원인**: `nginx:alpine` Docker 컨테이너 `my-web-server`가 `0.0.0.0:80->80` 으로 떠 있었다.
  ```
  822ebbfe7369  nginx:alpine  0.0.0.0:80->80/tcp     my-web-server
  ecd9d9742c13  nginx:alpine  0.0.0.0:8500->80/tcp   web-server-8500
  ```
- **해결**: 포트 80을 시스템 Nginx로 넘기기 위해 해당 컨테이너만 중지.
  ```bash
  sudo docker stop my-web-server
  ```
  > `web-server-8500`(8500 포트)은 충돌이 없으므로 그대로 유지.

---

### 문제 ③ sudo 비밀번호 반복 실패

```
[sudo] password for waterfirst:
Sorry, try again.
```

- **원인**: 로그인 비밀번호를 잘못 입력. (sudo 비밀번호 = waterfirst 계정 로그인 비밀번호)
- **확인법**:
  ```bash
  sudo whoami   # → root 가 출력되면 성공
  ```
- **교훈**: 비밀번호가 필요한 `sudo` 명령은 **터미널에서 사람이 직접** 입력해야 한다. 여러 sudo 명령은 `sudo bash -c '...'` 로 묶으면 비밀번호를 **한 번만** 입력하면 된다.

---

### 문제 ④ `/app/` 접속 시 404 — `proxy_pass` 뒤 슬래시 문제

Nginx·Streamlit 모두 실행 중인데도 브라우저가 404를 반환.

- **원인**: `proxy_pass` URL 끝의 슬래시(`/`) 유무가 경로 전달 방식을 바꾼다.

  | Nginx 설정 | `/app/` 요청이 백엔드에 전달되는 경로 | 결과 |
  |---|---|---|
  | `proxy_pass http://127.0.0.1:8501/;` (슬래시 O) | `/` (← `/app/` 접두어 제거됨) | ❌ 404 |
  | `proxy_pass http://127.0.0.1:8501;` (슬래시 X) | `/app/` (그대로 전달) | ✅ 200 |

  Streamlit은 `baseUrlPath = "app"` 설정 때문에 **모든 요청이 `/app/`로 시작**해야 한다. 슬래시가 붙으면 접두어가 잘려 나가 앱이 경로를 못 찾는다.

- **해결**: `proxy_pass` 끝의 슬래시를 제거.
  ```nginx
  location /app/ {
      proxy_pass http://127.0.0.1:8501;   # ← 끝 슬래시 없음
      ...
  }
  ```
  → `curl -I http://localhost/app/` 에서 `HTTP/1.1 200 OK` 확인.

---

### 문제 ⑤ (핵심) 페이지는 뜨는데 `Connection failed with status 404` — WebSocket + reload 누락

브라우저에서 페이지 골격은 로드되지만 Streamlit 상단에 **`Connection error — Connection failed with status 404.`** 표시. 앱이 살아 움직이지 않음.

- **1차 원인 (설정)**: 별도로 두었던 `location /app/_stcore/` 블록이 경로를 `/_stcore/`로 재작성하고 있었다. Streamlit의 실시간 통신 채널인 WebSocket(`/app/_stcore/stream`)이 이 블록을 타면서 `/app/` 접두어를 잃어 404가 났다.
  - **해결**: `_stcore` 전용 블록을 **삭제**하고, `location /app/` **하나가** WebSocket 포함 모든 하위 경로를 처리하도록 통합. (WebSocket 업그레이드 헤더가 `/app/` 블록에 이미 존재)

- **2차 원인 (진짜 범인)**: 설정 파일은 고쳤지만 **Nginx를 reload 하지 않아** 실행 중인 프로세스가 옛 설정을 그대로 물고 있었다.

  진단 근거 — 시각 비교로 확정:
  ```
  conf 파일 수정시각   : 20:54:07
  nginx 프로세스 시작   : 20:48:40   ← 파일 수정보다 6분 이르다 = 미반영
  ```
  경로별 응답으로 교차 검증:
  ```
  백엔드 직접  127.0.0.1:8501/app/_stcore/health  → 200  (앱은 정상)
  Nginx 경유   localhost/app/_stcore/health        → 404  (Nginx가 잘못 라우팅)
  ```
  → 앱은 멀쩡한데 Nginx만 옛 설정으로 404를 내고 있었다.

- **최종 해결**:
  ```bash
  sudo nginx -t && sudo systemctl reload nginx
  ```
  ```bash
  # 검증
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost/app/_stcore/health
  # → 200  ✅
  ```
  브라우저 강력 새로고침(Ctrl+Shift+R) 후 Connection error 사라지고 앱 정상 동작 확인.

---

## 4. 최종 동작 구성

```
http://waterfirst.pro/app/  (또는 http://221.153.204.191/app/)
        │
        ▼
   Nginx :80
   ├─ location /       → /home/waterfirst/web        (정적 홈페이지)
   └─ location /app/   → proxy_pass 127.0.0.1:8501   (Streamlit)
                          + WebSocket 업그레이드 헤더
        │
        ▼
   Streamlit 127.0.0.1:8501  (baseUrlPath=app)
```

| URL | 서비스 | 상태 |
|-----|--------|------|
| `http://waterfirst.pro/` | 정적 홈페이지 (`web/`) | ✅ |
| `http://waterfirst.pro/app/` | Streamlit 샘플 | ✅ |
| `http://<공인IP>:8500` | Docker 웹 (`web-server-8500`) | ✅ 유지 |

---

## 5. 다시 겪지 않기 위한 체크리스트

Streamlit(또는 유사 WebSocket 앱)을 Nginx 서브경로로 배포할 때:

- [ ] **앱은 `127.0.0.1`에만 바인드**, 외부 노출은 Nginx에 맡긴다.
- [ ] 서브경로 배포 시 앱의 `baseUrlPath`와 Nginx `location` 경로를 **일치**시킨다 (`app` ↔ `/app/`).
- [ ] `proxy_pass` 뒤 **슬래시 유무**를 의도에 맞게 결정한다. baseUrlPath를 쓰면 **슬래시 없이** 전체 경로를 그대로 넘긴다.
- [ ] WebSocket을 위해 `location` 블록에 아래를 포함한다. `_stcore`용 별도 블록은 필요 없다.
  ```nginx
  proxy_http_version 1.1;
  proxy_set_header Upgrade    $http_upgrade;
  proxy_set_header Connection $connection_upgrade;   # map 블록으로 정의
  ```
- [ ] **설정을 고쳤으면 반드시 반영**: `sudo nginx -t && sudo systemctl reload nginx`. (테스트가 안 맞으면 "reload 했나?"를 가장 먼저 의심)
- [ ] 문제 격리 순서: **백엔드 직접 curl → Nginx 경유 curl** 을 나눠서 찍으면 앱 문제인지 Nginx 문제인지 즉시 갈린다.
- [ ] 포트 충돌 확인: `ss -tlnp | grep ':80'` / `sudo docker ps`.

---

## 6. 유용했던 진단 명령어 모음

```bash
# 무엇이 어떤 포트를 듣고 있나
ss -tlnp | grep -E '8501|:80'

# 포트 80을 점유한 Docker 컨테이너 찾기
sudo docker ps -a --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"

# 앱(백엔드) vs Nginx(프록시) 응답 분리 진단
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8501/app/_stcore/health   # 백엔드
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/app/_stcore/health        # Nginx 경유

# 실행 중인 Nginx가 최신 설정인지 (파일 수정 vs 프로세스 시작 시각 비교)
stat -c '%y' /etc/nginx/sites-enabled/streamlit-sample.conf
ps -o lstart= -p "$(cat /run/nginx.pid)"

# 설정 검사 후 무중단 반영
sudo nginx -t && sudo systemctl reload nginx
```
