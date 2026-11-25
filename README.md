# 네이버 카페 홍보글 자동 게시기

게임 클랜의 클랜원 모집 홍보글을 **매일 정해진 시각(12:00 / 21:00)에 네이버 카페에 자동으로 올리는** Python 프로그램입니다.
바쁜 클랜 운영진이 하루 2번 같은 글을 직접 올리던 일을 대신합니다.

- **네이버 공식 카페 Open API**만 사용합니다. 브라우저 매크로를 쓰지 않아 약관 위반이나 계정 정지 위험이 없습니다.
- **Python 표준 라이브러리만** 사용합니다. `pip install`이 필요 없습니다.
- 기존에 직접 쓰던 글과 **같은 모양**으로 올립니다. 이미지 배치, 이미지 링크, 글자 서식, 대표사진까지 맞춥니다.

## 주요 기능

| 기능 | 설명 |
|---|---|
| OAuth 2.0 로그인 | 최초 1회 브라우저 로그인 → 토큰 저장, 만료 시 자동 갱신 |
| 글 게시 | 제목 + HTML 본문 + 대표사진 첨부(multipart), 전체 공개·검색 허용 |
| 미리보기 | 실제로 올리지 않고 브라우저에서 결과 확인 |
| 정시 자동 게시 | GitHub Actions(PC가 꺼져 있어도 동작) 또는 Windows 작업 스케줄러(절전 중인 PC를 깨워서 게시) |
| 시험 모드 | `check`: 글은 올리지 않고 토큰 갱신·게시판 읽기·사진 확인만 |
| 놓친 게시 보충 | 그 시각에 PC가 꺼져 있었으면 켜진 뒤 1시간 안에 게시 |
| 중복 방지 | 같은 시간대에는 한 번만 게시, 동시 실행 잠금 |
| 게시 전 검토 | 게시판에 이미 올라간 글이 있는지, 마지막 글과 3시간 이상 지났는지, 본문 사진 주소가 살아있는지 확인 |
| 게시 후 확인 | 게시판 목록에서 실제로 1개만 올라갔는지 확인해 로그에 기록 |
| 로그 | 성공·실패를 `log.txt`에 기록 |

## 동작 구조

```
Windows 작업 스케줄러
 ├─ 매일 12:00 / 21:00  (절전 중인 PC 깨우기)  ─┐
 └─ 1시간마다 (놓친 게시 확인)                   ─┴─> cafe_poster.py run
                                                     │
                     가장 최근 게시 시각 이후 아직 안 올렸나? ── 아니오 → 종료
                                                     │ 예
                         access token 확인 (만료 시 refresh token으로 갱신)
                                                     │
               POST /v1/cafe/{clubid}/menu/{menuid}/articles (multipart)
                                                     │
                                       state.json, log.txt 기록
```

## 개발하며 해결한 문제

공식 문서에 나오지 않는 카페 API 제약을 하나씩 실험해서 확인하고 우회했습니다.

| 문제 | 원인 | 해결 |
|---|---|---|
| `403 / code 999` 오류 | 본문 HTML 속성의 큰따옴표 (네이버 이슈 트래커 사례 확인) | 전송 직전 `"` → `'` 자동 변환 |
| 이미지가 지정한 위치에 들어가지 않음 | 첨부 이미지는 위치 지정과 상관없이 본문 맨 위에 모여서 붙음 | 네이버에 이미 올라간 이미지 주소를 본문에 직접 배치 → 위치·정렬·링크 적용 |
| 앨범형 보기에 글이 안 보임 | 첨부 파일이 없으면 대표사진이 생성되지 않음 | 대표사진용 이미지 1장만 첨부. 첨부 이미지는 정렬 지정이 안 돼서 양옆에 여백을 넣은 이미지로 가운데처럼 보이게 처리 |
| 로그인 안 한 사용자에게 글이 안 보임 | API 기본값이 멤버 공개 | `openyn`, `searchopen`을 명시 |
| 연속 게시 차단 | 짧은 간격의 재게시를 플랫폼이 제한 | 미리보기로 테스트 횟수를 줄이고, 시간대별 중복 방지 로직 추가 |

## 설치 및 실행

### 1. 준비
- Windows, Python 3.10 이상
- [네이버 개발자센터](https://developers.naver.com/apps/#/register)에서 애플리케이션 등록
  - 사용 API: **네이버 로그인** → 권한: **카페 글쓰기**
  - 서비스 환경 PC 웹 — 서비스 URL `http://localhost:8765`, Callback URL `http://localhost:8765/callback`

### 2. 설정 파일 만들기
```
copy config.example.json config.json
copy post.example.txt post.txt
```
- `config.json`: Client ID/Secret, 카페 ID(`clubid`), 게시판 ID(`menuid`), 게시 시각, 대표사진 파일
  - 카페 ID와 게시판 ID는 카페 글 주소의 `cafes/{clubid}/...menuid={menuid}`에서 확인할 수 있습니다.
  - `thumbnail_rotation` (선택): 대표사진 A/B 비교용 이미지 목록. 넣으면 글마다 번갈아 첫 번째 첨부 사진(대표사진)으로 쓰고, 날마다 시간대 순서를 바꿔 한쪽이 늘 같은 시각에 몰리지 않게 합니다. 어떤 사진을 썼는지 `log.txt`에 `대표사진:` 줄로 남습니다. 빼면 `attach_images`를 그대로 씁니다.
  - `backup_delay_minutes` (선택, 기본 0): GitHub Actions와 PC를 같이 쓸 때 PC 쪽에 넣습니다. 예: `90`이면 PC의 `run`은 정시 + 90분이 지나기 전에는 아무것도 하지 않고, 그 뒤에도 게시판에 그 시간대 글이 없을 때만 보충합니다. 두 곳이 같은 순간에 올리는 일을 막습니다.
  - `require_board_check` (선택, 기본 false): `true`면 게시판 목록을 읽지 못했을 때 올리지 않습니다. `state.json`이 남지 않는 GitHub 서버용이며 워크플로가 자동으로 켭니다.
  - `post_window_minutes` (선택, 기본 0 = 제한 없음): 정시 + 이 분이 지나면 `run`이 올리지 않습니다. GitHub 서버용(워크플로가 80으로 설정)이며, PC의 `backup_delay_minutes`(90)보다 작게 두어 GitHub(정시~80분)과 PC(90분~)가 올리는 시간이 겹치지 않게 합니다.
- `post.txt`: 첫 줄은 제목, 나머지는 본문(HTML)
- `images/`: 대표사진으로 첨부할 이미지 (jpg, png, gif)

### 3. 명령어
```
py cafe_poster.py login       # 처음 한 번: 네이버 로그인
py cafe_poster.py preview     # 브라우저 미리보기
py cafe_poster.py check       # 시험 모드 (글은 올리지 않음)
py cafe_poster.py post        # 지금 바로 게시
py cafe_poster.py schedule    # 자동 게시 등록
py cafe_poster.py unschedule  # 자동 게시 해제
```

### 4. GitHub Actions로 실행 (PC가 꺼져 있어도 게시)
`.github/workflows/post.yml`이 GitHub 서버에서 한국 시각 12:05~13:15, 21:05~22:15에 약 15분 간격으로 6번 `run`을 실행합니다(GitHub 예약 실행은 늦어지거나 빠질 수 있어서 여러 번). 먼저 올린 뒤의 실행은 "이미 있어서 건너뜀", 정시 + 80분이 지나 시작된 실행은 "올리지 않음"으로 끝나며 정상입니다. 공개 저장소는 무료입니다.

1. 저장소 Settings → Secrets and variables → Actions → **Secrets**에 5개 입력
   `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `NAVER_REFRESH_TOKEN`(PC의 `tokens.json` 안 refresh_token), `CAFE_CLUBID`, `CAFE_MENUID`
2. Actions 탭 → "카페 글 게시" → Run workflow → mode `check`로 시험 실행 (글은 올리지 않음)
3. 시험이 성공하면 같은 화면의 **Variables**에 `AUTO_POST` = `on` 추가 → 예약 실행 시작 (끄려면 `off`)
4. PC도 같이 쓰면 PC `config.json`에 `"backup_delay_minutes": 90` 추가 → PC는 늦은 보충용

- 비밀 값은 Secrets에서만 읽고, `config.json`·`tokens.json`은 실행하는 서버 안에서만 임시로 만듭니다.
- 게시 실패, 검토 실패, 토큰 갱신 실패면 실행이 실패(빨간 X)로 끝나고 GitHub이 메일로 알립니다.
- 네이버 refresh_token은 갱신해도 바뀌지 않아서(네이버 로그인 API 명세) Secret을 한 번만 넣으면 됩니다. 만료되어 실패하면 PC에서 `login`을 다시 하고 `NAVER_REFRESH_TOKEN`만 바꿉니다.
- **60일 멈춤**: 공개 저장소는 60일 동안 커밋 등 활동이 없으면 GitHub이 예약 실행을 자동으로 멈춥니다. Actions 탭 → "카페 글 게시" → **Enable workflow**를 누르면 다시 켜집니다 (GitHub이 멈추기 전에 메일로 알려줍니다).

## 파일 구성

| 파일 | 설명 | 저장소에 포함 |
|---|---|---|
| `cafe_poster.py` | 프로그램 전체 | O |
| `config.example.json` | 설정 예시 | O |
| `post.example.txt` | 글 예시 | O |
| `config.json` | 실제 설정 (Client Secret 포함) | **X** |
| `tokens.json` | 네이버 로그인 토큰 | **X** |
| `.github/workflows/post.yml` | GitHub Actions 예약 실행 | O |
| `post.txt`, `images/thumb_a.png`·`thumb_b.png`·`logo_center.png` | 실제 홍보글과 대표사진 (GitHub 서버 게시용, 카페에 공개되는 내용) | O |
| `images/`의 나머지 | 클랜 이미지 | X |
| `state.json`, `log.txt` | 마지막 게시 시각, 실행 기록 | X |

## 향후 계획
- 게시 성공·실패 메신저 알림
- 여러 카페·게시판 동시 지원

---
AI 코딩 도구(Claude Code)를 활용해 개발했습니다.
