# streamlit-sample

Streamlit 기반 샘플 서비스 앱.

## 구조

```
streamlit-sample/
├── app.py                  # 메인 Streamlit 앱
├── requirements.txt        # Python 의존성
├── .streamlit/
│   └── config.toml         # Streamlit 서버 설정 (포트 8501)
└── venv/                   # Python 가상환경 (로컬 생성, git 제외)
```

## 최초 설정

```bash
cd /home/waterfirst/apps/streamlit-sample

# 가상환경 생성
python3 -m venv venv

# 의존성 설치
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

## 로컬 실행 (테스트)

```bash
venv/bin/streamlit run app.py
# → http://localhost:8501
```

## 배포

1. **systemd 서비스 등록**

```bash
sudo ln -s /home/waterfirst/deploy/systemd/streamlit-sample.service \
           /etc/systemd/system/streamlit-sample.service
sudo systemctl daemon-reload
sudo systemctl enable --now streamlit-sample
sudo systemctl status streamlit-sample
```

2. **Nginx 설정 등록**

```bash
sudo ln -s /home/waterfirst/deploy/nginx/streamlit-sample.conf \
           /etc/nginx/sites-enabled/streamlit-sample.conf
sudo nginx -t
sudo systemctl reload nginx
```

3. **로그 확인**

```bash
# journalctl
journalctl -u streamlit-sample -f

# 파일 로그
tail -f /home/waterfirst/logs/streamlit-sample/stderr.log
```

## 포트 / 경로

| 항목 | 값 |
|------|-----|
| 내부 포트 | `8501` (127.0.0.1 전용) |
| 공개 경로 | `https://waterfirst.pro/app/` |
| 메인 사이트 | `https://waterfirst.pro/` (`/home/waterfirst/web`) |
