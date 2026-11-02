# 네이버 카페 홍보글 자동 게시기

## 지금 상태 (2026-11-02)

- 자동 게시: 정상. 11/2 00:00 글 게시 후 "정상적으로 1개 올라감" (확인은 `log.txt` 마지막 줄)
- 진행 중: 없음
- 다음 할 일: 1~2주 뒤 가입문의방 대화 내보내기를 다시 받아 입장 수 갱신 → 포트폴리오 반영

이 3줄은 일이 끝날 때마다 갱신한다. 자세한 기록과 할 일은 `작업기록.md`.

LRZ 클랜 모집 홍보글을 매일 00:00 / 12:00에 네이버 카페(롤카페 클랜 홍보 게시판)에 자동으로 올리는 Python 프로그램. 포트폴리오 프로젝트이기도 하다.

- Python 표준 라이브러리만 사용 (`pip install` 없음), Windows 전용 (`msvcrt`, 작업 스케줄러)
- 네이버 공식 카페 Open API만 사용 (브라우저 매크로 없음). OAuth 로그인 토큰은 `tokens.json`
- **지금 실제로 돌아가고 있다.** Windows 작업 스케줄러(`NaverCafeAutoPost`, `NaverCafeAutoPostWake`)가 00:00 / 12:00과 1시간마다 `cafe_poster.py run`을 실행한다.
- GitHub 공개 저장소: `Junkong171/naver-cafe-auto-poster`
- 현재 상태와 결정 기록은 `작업기록.md`(git 제외)를 먼저 읽는다.

## 사용자 안내 방식

- 사용자는 코딩 초보자다. 항상 **한국어**로, 단계별로 설명한다.
- 무엇을 왜 바꾸는지 먼저 말하고, 어려운 용어에는 짧은 풀이를 붙인다.
- 사용자가 직접 해야 하는 일(카페에서 확인, 게시 등)은 순서대로 번호를 매겨 안내한다. 가능하면 해당 페이지를 미리 열고, 붙여 넣을 값은 클립보드에 복사해 둔다.
- 외부 서비스를 추천하기 전에 무료 플랜에서 필요한 기능이 되는지 먼저 확인한다.

## 실행 명령어

| 명령 | 하는 일 | Claude가 실행해도 되나 |
|---|---|---|
| `py -m py_compile cafe_poster.py` | 문법 검사 | O |
| `py cafe_poster.py` | 사용법 출력 | O |
| `py cafe_poster.py preview` | `preview.html`을 만들고 브라우저로 미리보기 (게시 안 함) | O |
| `py cafe_poster.py login` | 네이버 로그인, `tokens.json` 저장 | 사용자 확인 후 |
| `py cafe_poster.py post` | **지금 바로 실제 게시** | X (hook이 차단, 사용자가 직접) |
| `py cafe_poster.py run` | 시간이 되었으면 **실제 게시** | X (hook이 차단, 사용자가 직접) |
| `py cafe_poster.py schedule` / `unschedule` | 작업 스케줄러 등록 / 해제 | X (hook이 차단, 사용자가 직접) |

자동 테스트는 없다. 검증은 문법 검사, 코드 읽기, 미리보기, 정시 게시 후 `log.txt` 확인으로 한다.

## 파일 구조

| 파일 | 내용 | git |
|---|---|---|
| `cafe_poster.py` | 프로그램 전체 (로그인, 게시, 게시 전 검토·게시 후 확인, 예약, 미리보기) | O |
| `config.example.json`, `post.example.txt` | 설정·글 예시 | O |
| `README.md` | 공개용 소개 (포트폴리오) | O |
| `CLAUDE.md`, `.claude/`, `docs/specs/` | 이 하네스 (규칙, hook, tester, 절차서, 명세) | O |
| `config.json` | Client ID/Secret, 카페·게시판 ID, 게시 시각, 첨부 사진 | **절대 X** |
| `tokens.json` | 네이버 로그인 토큰 (계정 열쇠) | **절대 X** |
| `post.txt`, `images/` | 실제 홍보글(첫 줄 제목, 나머지 HTML 본문)과 사진 | X |
| `state.json`, `run.lock`, `log.txt`, `preview.html` | 마지막 게시 시각, 동시 실행 잠금, 실행 기록, 미리보기 | X |
| `작업기록.md`, `사용법.md`, `포트폴리오.*` | 개인 메모와 포트폴리오 | X |

## 지켜야 할 사실

- **원본 글 31359494를 지우거나 고치지 않는다.** 본문 사진이 그 글에 올라간 사진 주소(pstatic)를 쓴다. 지우면 매일 올라가는 글의 사진이 모두 깨진다.
- 글 안의 링크는 모두 `open.kakao.com/o/gNeGTWBc`. 단축 링크(bit.ly)는 무료 플랜에서 클릭 통계가 안 보여서 철회했다.
- 본문 HTML의 큰따옴표는 전송 직전 작은따옴표로 바뀐다 (네이버 403/999 오류 회피). 이 처리를 없애지 않는다.
- 포트폴리오·README에는 실제 데이터만 쓴다. 숫자를 지어내지 않는다.

## 규칙

- 파일 전체를 새로 쓰지 말고 **필요한 부분만** 수정한다.
- 기존 안전장치(동시 실행 잠금, 게시 전 검토: 게시판 중복·3시간 간격·사진 깨짐, 게시 후 확인)를 약하게 만들지 않는다.
- `config.json`에 새 항목이 필요하면 `config.example.json`과 README에도 추가하고, 항목이 없을 때도 동작하게 기본값을 둔다. `config.json` 자체는 사용자가 직접 고친다.
- 글 내용(`post.txt`)을 바꾸면 다음 정시 글부터 적용된다. 바꾼 뒤 `py cafe_poster.py preview`로 확인한다.
- 매 변경·결정 후 `작업기록.md`를 갱신한다: "지금 상태" 표, "기록"에 날짜별 항목, "할 일" 체크리스트.

## 금지 / 사용자 승인 필요

절대 하지 않는 것:

- `config.json`, `tokens.json`을 git에 넣기 (`git add -f` 포함), 내용을 화면·명세·커밋에 옮겨 적기
- 원본 글 31359494 삭제·수정
- 사용자 승인 없이 실제 게시 (`post`, `run`, 네이버 API 직접 호출)

반드시 사용자에게 먼저 묻고 승인받은 뒤에만 하는 것:

- 작업은 새 브랜치에서 하고, main에는 직접 푸시하지 않는다.
- 커밋, 푸시, PR 만들기, PR 병합 (병합은 `"C:/Program Files/GitHub CLI/gh.exe" pr merge`, 먼저 짧게 확인)
- 강제 푸시 (`git push --force`), `git reset --hard`, `git clean`
- 대량 삭제 (`rm -rf`, `Remove-Item -Recurse -Force` 등)
- 작업 스케줄러 등록 변경 (`schedule`, `unschedule`, `schtasks`)
- `config.json`, `tokens.json`, `.env*`, `.claude/settings.json` 수정
- `.gitignore`에서 비밀 파일 줄 빼기

`.claude/hooks/`의 guard 스크립트가 위 명령 대부분을 자동으로 차단한다. 막혔다고 우회하지 말고 사용자에게 물어본다.

## 작업 흐름

**가벼운 수정**은 명세와 tester 없이 바로 한다: 글 문구(`post.txt`), 문서(README, CLAUDE.md, 작업기록.md), 주석.
바로 한 뒤에도 금지 목록은 그대로 지키고, 커밋·푸시는 승인을 받고, `작업기록.md`를 갱신한다. `post.txt`를 고쳤으면 `py cafe_poster.py preview`로 확인한다.

**`cafe_poster.py`의 동작이 바뀌는 변경**(게시 조건, 안전장치, 예약, 로그인 등)은 아래 절차를 모두 밟는다.

1. **명세 작성**: `/new-feature`로 `docs/specs/F-xxx-*.md`를 쓰고 한국어로 보여준다.
2. **사용자 승인**: 승인 전에는 코드를 수정하지 않는다.
3. **구현**: 필요한 부분만 수정한다. `py -m py_compile cafe_poster.py`로 문법을 확인한다.
4. **독립 검증**: `/verify-feature <명세>`로 tester 서브에이전트에 맡긴다. 명세 경로와 변경 내용만 넘기고(구현 대화는 넘기지 않음), 결과 원문을 보여준다. FAIL이 있으면 완료가 아니다. 실제 게시 결과는 다음 정시 이후 `log.txt`로 사용자와 함께 확인한다.
5. **커밋·푸시 승인**: 커밋, 푸시, PR, main 반영은 사용자가 승인한 경우에만 한다.
6. **기록**: `작업기록.md`를 갱신한다.
