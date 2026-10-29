# 네이버 카페 홍보글 자동 게시기

게임 클랜의 클랜원 모집 홍보글을 **매일 정해진 시각(00:00 / 12:00)에 네이버 카페에 자동으로 올리는** Python 프로그램입니다.
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
| 정시 자동 게시 | Windows 작업 스케줄러 등록, 절전 중인 PC를 깨워서 게시 |
| 놓친 게시 보충 | 그 시각에 PC가 꺼져 있었으면 켜진 뒤 1시간 안에 게시 |
| 중복 방지 | 같은 시간대에는 한 번만 게시, 동시 실행 잠금 |
| 게시 전 검토 | 게시판에 이미 올라간 글이 있는지, 마지막 글과 3시간 이상 지났는지, 본문 사진 주소가 살아있는지 확인 |
| 게시 후 확인 | 게시판 목록에서 실제로 1개만 올라갔는지 확인해 로그에 기록 |
| 로그 | 성공·실패를 `log.txt`에 기록 |

## 동작 구조

```
Windows 작업 스케줄러
 ├─ 매일 00:00 / 12:00  (절전 중인 PC 깨우기)  ─┐
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
- `post.txt`: 첫 줄은 제목, 나머지는 본문(HTML)
- `images/`: 대표사진으로 첨부할 이미지 (jpg, png, gif)

### 3. 명령어
```
py cafe_poster.py login       # 처음 한 번: 네이버 로그인
py cafe_poster.py preview     # 브라우저 미리보기
py cafe_poster.py post        # 지금 바로 게시
py cafe_poster.py schedule    # 자동 게시 등록
py cafe_poster.py unschedule  # 자동 게시 해제
```

## 파일 구성

| 파일 | 설명 | 저장소에 포함 |
|---|---|---|
| `cafe_poster.py` | 프로그램 전체 | O |
| `config.example.json` | 설정 예시 | O |
| `post.example.txt` | 글 예시 | O |
| `config.json` | 실제 설정 (Client Secret 포함) | **X** |
| `tokens.json` | 네이버 로그인 토큰 | **X** |
| `post.txt`, `images/` | 실제 홍보글과 이미지 | X |
| `state.json`, `log.txt` | 마지막 게시 시각, 실행 기록 | X |

## 향후 계획
- GitHub Actions로 옮겨서 PC 전원과 상관없이 동작
- 게시 성공·실패 메신저 알림
- 여러 카페·게시판 동시 지원

---
AI 코딩 도구(Claude Code)를 활용해 개발했습니다.
