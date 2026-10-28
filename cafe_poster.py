"""네이버 카페 자동 글쓰기 (공식 카페 API 사용)

사용법:
  py cafe_poster.py login      처음 한 번: 네이버 로그인 후 토큰 저장
  py cafe_poster.py preview    올리지 않고 브라우저에서 미리보기
  py cafe_poster.py post       지금 바로 글 올리기 (시간 무시)
  py cafe_poster.py run        post_times 중 가장 최근 시각 이후 아직 안 올렸으면 올리기
  py cafe_poster.py schedule   윈도우 작업 스케줄러 등록 (post_times에 PC 깨워서 실행 + 1시간마다 놓친 글 확인)
  py cafe_poster.py unschedule 작업 스케줄러 등록 해제
"""

import json
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG_FILE = BASE / "config.json"
POST_FILE = BASE / "post.txt"
TOKEN_FILE = BASE / "tokens.json"
STATE_FILE = BASE / "state.json"
LOG_FILE = BASE / "log.txt"
IMAGE_DIR = BASE / "images"
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif"}

REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
TASK_NAME = "NaverCafeAutoPost"
WAKE_TASK_NAME = "NaverCafeAutoPostWake"


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_json(path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config():
    cfg = load_json(CONFIG_FILE)
    if not cfg:
        sys.exit("config.json 파일이 없습니다. config.example.json을 복사해서 만드세요.")
    if not cfg.get("client_id") or cfg["client_id"].startswith("여기에"):
        sys.exit("config.json에 client_id / client_secret을 먼저 입력하세요. (README.md 참고)")
    return cfg


def http_json(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from None


# ---------- 로그인 / 토큰 ----------

def login():
    cfg = load_config()
    state = secrets.token_urlsafe(16)
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result["code"] = qs.get("code", [None])[0]
            result["state"] = qs.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("로그인 완료! 이 창을 닫고 프로그램으로 돌아가세요.".encode("utf-8"))

        def log_message(self, *args):
            pass

    auth_url = "https://nid.naver.com/oauth2.0/authorize?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": REDIRECT_URI,
        "state": state,
    })
    print("브라우저에서 네이버 로그인을 진행하세요...")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", REDIRECT_PORT), Handler)
    while "code" not in result:
        server.handle_request()
    server.server_close()

    if not result["code"] or result["state"] != state:
        sys.exit("로그인에 실패했습니다. 다시 시도하세요.")

    token = http_json("https://nid.naver.com/oauth2.0/token?" + urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "code": result["code"],
        "state": state,
    }))
    if "access_token" not in token:
        sys.exit(f"토큰 발급 실패: {token}")
    token["obtained_at"] = time.time()
    save_json(TOKEN_FILE, token)
    log("로그인 성공, 토큰 저장됨")


def get_access_token(cfg):
    token = load_json(TOKEN_FILE)
    if not token:
        sys.exit("먼저 'py cafe_poster.py login'을 실행하세요.")

    # 만료 5분 전이면 갱신
    expires_in = int(token.get("expires_in", 0))
    if time.time() < token["obtained_at"] + expires_in - 300:
        return token["access_token"]

    new = http_json("https://nid.naver.com/oauth2.0/token?" + urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "refresh_token": token["refresh_token"],
    }))
    if "access_token" not in new:
        sys.exit(f"토큰 갱신 실패 (다시 login 하세요): {new}")
    token.update(new)
    token["obtained_at"] = time.time()
    save_json(TOKEN_FILE, token)
    return token["access_token"]


# ---------- 글쓰기 ----------

def read_post():
    if not POST_FILE.exists():
        sys.exit("post.txt 파일이 없습니다. post.example.txt를 복사해서 만드세요.")
    lines = POST_FILE.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        sys.exit("post.txt 첫 줄은 제목, 둘째 줄부터 본문이어야 합니다.")
    subject = lines[0].strip()
    # 본문은 HTML 그대로 사용 (<!-- --> 메모는 제거)
    content = re.sub(r"<!--.*?-->", "", "\n".join(lines[1:]), flags=re.S)
    content = "".join(line.strip() for line in content.splitlines())
    # HTML 속성에 큰따옴표(")가 있으면 카페 API가 403/999 오류를 내는 사례가 있어 작은따옴표로 바꿈
    content = content.replace('"', "'")
    return subject, content


def build_multipart(fields, files):
    boundary = "----CafePoster" + secrets.token_hex(12)
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8")
        )
    for path in files:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
            f"Content-Type: {IMAGE_TYPES[path.suffix.lower()]}\r\n\r\n".encode("utf-8")
            + path.read_bytes() + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def attached_images(cfg):
    # 첨부 사진은 카페에서 글 맨 위에 링크 없이 붙고, 첫 번째 사진이 대표사진(앨범형 썸네일)이 됨
    paths = [IMAGE_DIR / name for name in cfg.get("attach_images", [])]
    for path in paths:
        if not path.exists():
            sys.exit(f"첨부할 사진이 없습니다: {path}")
    return paths


def post_article():
    cfg = load_config()
    subject, content = read_post()
    access_token = get_access_token(cfg)

    url = f"https://openapi.naver.com/v1/cafe/{cfg['clubid']}/menu/{cfg['menuid']}/articles"
    # 네이버 카페 API는 한글이 깨지지 않게 제목/본문을 URL 인코딩해서 보내야 함
    fields = {
        "subject": urllib.parse.quote(subject),
        "content": urllib.parse.quote(content),
        # 지정하지 않으면 멤버공개로 올라가 로그인 안 한 사람에게는 안 보임
        "openyn": "true",
        "searchopen": "true",
    }
    body, content_type = build_multipart(fields, attached_images(cfg))
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": content_type,
    }
    # 절전에서 막 깨어났을 때는 인터넷 연결이 늦을 수 있어 몇 번 재시도
    for attempt in range(4):
        try:
            res = http_json(url, data=body, headers=headers)
            break
        except RuntimeError as e:
            log(f"글쓰기 실패: {e}")
            return False
        except urllib.error.URLError as e:
            if attempt == 3:
                log(f"글쓰기 실패 (인터넷 연결 안 됨): {e}")
                return False
            time.sleep(20)

    article_url = res.get("message", {}).get("result", {}).get("articleUrl", "")
    log(f"글쓰기 성공: {subject} {article_url}")
    save_json(STATE_FILE, {"last_posted_at": time.time()})
    return True


def post_times(cfg):
    return cfg.get("post_times", ["00:00", "12:00"])


def latest_slot(cfg, now):
    """지금 시각 기준으로 가장 최근에 지난 올리기 시각 (오늘 또는 어제)"""
    slots = []
    for day in (now.date(), now.date() - timedelta(days=1)):
        for hhmm in post_times(cfg):
            h, m = map(int, hhmm.split(":"))
            slot = datetime.combine(day, datetime.min.time()).replace(hour=h, minute=m)
            if slot <= now:
                slots.append(slot)
    return max(slots)


def run_if_due():
    cfg = load_config()
    now = datetime.now()
    slot = latest_slot(cfg, now)
    last = (load_json(STATE_FILE, {}) or {}).get("last_posted_at", 0)
    if last >= slot.timestamp():
        print(f"{slot:%m/%d %H:%M} 글은 이미 올렸습니다. 다음 시각: {', '.join(post_times(cfg))}")
        return
    post_article()


# ---------- 작업 스케줄러 ----------

def schedule():
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    cmd = f'"{exe}" "{BASE / "cafe_poster.py"}" run'
    subprocess.run([
        "schtasks", "/Create", "/F", "/TN", TASK_NAME,
        "/SC", "HOURLY", "/MO", "1", "/TR", cmd,
    ], check=True)
    # 노트북 배터리 사용 중에도 실행되도록 설정
    subprocess.run([
        "powershell", "-NoProfile", "-Command",
        "$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; "
        f"Set-ScheduledTask -TaskName {TASK_NAME} -Settings $s | Out-Null",
    ], check=True)
    # 정해진 시각마다 절전 중인 PC를 깨워서 run 실행
    cfg = load_config()
    triggers = ", ".join(
        f"(New-ScheduledTaskTrigger -Daily -At '{hhmm}')" for hhmm in post_times(cfg)
    )
    script = (
        f"$a = New-ScheduledTaskAction -Execute '{exe}' -Argument '\"{BASE / 'cafe_poster.py'}\" run'; "
        f"$t = @({triggers}); "
        "$s = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; "
        f"Register-ScheduledTask -TaskName {WAKE_TASK_NAME} -Action $a -Trigger $t -Settings $s -Force | Out-Null"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
    print(f"등록 완료: 매일 {', '.join(post_times(cfg))}에 글을 올립니다. (절전 중인 PC도 깨움)")
    print("그 시각에 PC가 꺼져 있었다면, 켜진 뒤 1시간 안에 놓친 글을 올립니다.")


def unschedule():
    subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK_NAME], check=True)
    subprocess.run(["schtasks", "/Delete", "/F", "/TN", WAKE_TASK_NAME])
    print("등록 해제 완료")


def preview():
    """카페에 올리지 않고 내 PC 브라우저에서 미리보기 (카페 화면과 약간 다를 수 있음)"""
    cfg = load_json(CONFIG_FILE, {}) or {}
    subject, content = read_post()
    attached = "".join(
        f"<p><img src='images/{path.name}' style='max-width:100%;' /></p>" for path in attached_images(cfg)
    )
    content = attached + content
    html = (
        "<!doctype html><meta charset='utf-8'><title>미리보기</title>"
        "<body style='margin:0;background:#f5f6f7;font-family:\"Nanum Gothic\",\"Malgun Gothic\",sans-serif;'>"
        "<div style='max-width:860px;margin:24px auto;background:#fff;padding:24px 30px;'>"
        f"<h2 style='font-weight:normal;font-size:26px;'>{subject}</h2><hr>{content}</div></body>"
    )
    out = BASE / "preview.html"
    out.write_text(html, encoding="utf-8")
    webbrowser.open(out.as_uri())
    print(f"미리보기를 열었습니다: {out}")


COMMANDS = {
    "preview": preview,
    "login": login,
    "post": post_article,
    "run": run_if_due,
    "schedule": schedule,
    "unschedule": unschedule,
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
