# F-002: PC가 꺼져 있어도 게시 (GitHub Actions)

- 상태: 승인됨
- 작성일: 2026-11-22
- 관련 파일: `cafe_poster.py`, `.github/workflows/post.yml`(새 파일), `README.md`, `config.example.json`

> 이 파일은 GitHub 공개 저장소에 올라갑니다. Client ID/Secret, 토큰, 개인 정보, 실제 카페·게시판 ID는 쓰지 않습니다.

## 목적

지금은 Windows 작업 스케줄러가 PC를 깨워서 게시한다. PC가 꺼져 있거나 깨우기가 실패하면 늦게 올라간다 (11/22 12:00 글 → 17:50, 11/20 12:00 → 13:17 등). GitHub의 서버에서 정해진 시각에 `run`을 실행해 PC 상태와 상관없이 게시한다.

## 확인한 사실 (출처)

- 공개 저장소에서 표준 GitHub 호스팅 러너는 무료 — GitHub 문서 "GitHub Actions billing"
- 예약(schedule) 실행은 부하가 높을 때 늦어지거나 빠질 수 있고, 매시 정각이 특히 붐빔 — GitHub 문서 "Events that trigger workflows > schedule"
- cron은 기본 UTC, 타임존 지정 가능 — 같은 문서
- 공개 저장소는 60일 동안 저장소 활동이 없으면 예약 실행이 자동으로 멈춤 — 같은 문서, GitHub 커뮤니티 토론
- 네이버 토큰 (`cafe_poster.py:130-151`): 접근 토큰은 1시간(`expires_in` 3600). 만료되면 `refresh_token`으로 새로 받는다. 10/27부터 약 4주 동안 같은 방식으로 문제없이 갱신됨 (`log.txt`).
- 네이버 로그인 API 명세(네이버 공식 GitHub `naver/naver-openapi-guide`의 `ko/login/api/api.md`, 4.3절·6.2.3 예시): 접근 토큰 **갱신 응답에는 `access_token`, `token_type`, `expires_in`만 있고 새 `refresh_token`은 없다** → GitHub Secrets에 넣은 `refresh_token`을 계속 쓸 수 있음 (Secrets를 자동으로 고칠 필요 없음)
- **확인 못 한 것**: `refresh_token` 유효기간 (명세에 적혀 있지 않음). 만료되면 갱신이 실패해 워크플로가 실패로 끝나고(AC-6) 메일이 옴 → PC에서 `login`을 다시 하고 Secret 1개를 바꾸면 됨. AC-9는 안전 확인용으로 유지
- **확인 못 한 것**: 해외(GitHub 서버) IP에서 네이버 카페 API 글쓰기가 막히는지 → 첫 시험 실행에서 확인

## 사용자 결정이 필요한 것

1. **글 내용과 사진을 어디에 둘지**: GitHub 서버에는 `post.txt`, `images/`가 없다 (지금은 git 제외).
   - (가) 공개 저장소에 `post.txt`·썸네일을 올림 — 어차피 카페에 공개되는 홍보글. 가장 간단
   - (나) 비공개 저장소를 따로 만들어 거기서 실행 — 실행 기록도 비공개. 무료 한도(월 2,000분) 안에서 충분하지만 저장소가 둘이 됨
2. **PC 예약을 어떻게 할지**:
   - (가) GitHub이 잘 되면 PC 예약 해제 — 두 곳이 같은 순간에 올리는 위험이 없음 (10/29 중복 사고와 같은 원인 차단)
   - (나) PC를 늦은 보충용으로 남김 — 정시 + 90분 이후에만 보충하도록 PC 쪽을 바꿔야 함 (코드 추가)

**사용자 결정 (2026-11-22)**: 1 → (가) 공개 저장소에 `post.txt`·썸네일 올림, 2 → (나) PC는 늦은 보충용으로 남김

## 동작 시나리오 (결정 1-가, 2-나 기준)

1. `.github/workflows/post.yml`이 매일 12:00, 21:00(한국 시각) 조금 뒤(정각 혼잡을 피해 :07)에 실행된다. 30분 뒤 한 번 더 실행해 빠진 글을 보충한다.
2. 비밀 값은 GitHub 저장소의 Secrets(암호화 보관, 실행 기록에서 자동으로 가려짐)에서 읽는다: Client ID/Secret, refresh_token, 카페·게시판 ID.
3. 실행할 때마다 `config.json`·`tokens.json`을 서버 안에서만 임시로 만들고, 실행이 끝나면 서버째 사라진다 (저장소에 커밋하지 않음).
4. `cafe_poster.py run`을 그대로 실행한다. 게시판 중복 확인, 3시간 간격, 사진 깨짐 확인, 게시 후 확인을 그대로 거친다. `state.json`이 없으므로 중복 판단은 게시판 목록이 맡는다 (지금도 1순위 기준).
5. 같은 워크플로가 겹쳐 실행되지 않게 `concurrency`로 한 번에 하나만 실행한다 (PC의 잠금 파일 역할).
6. 실행 기록(Actions 로그)에 `log.txt` 내용이 출력된다. 공개 저장소면 누구나 볼 수 있으므로 비밀 값·토큰이 출력되지 않게 한다.
7. 저장소에 `post.txt`와 썸네일(`images/thumb_a.png`, `thumb_b.png`, `logo_center.png`)을 올린다. `.gitignore`에서 이 파일들만 예외로 허용하고, 비밀 파일 줄(`config.json`, `tokens.json` 등)은 그대로 둔다.
8. **PC는 늦은 보충용**: PC의 `config.json`에 `"backup_delay_minutes": 90`을 넣으면, PC의 `run`은 정시 + 90분이 지나기 전에는 아무것도 하지 않는다. 90분 뒤에도 게시판에 그 시간대 글이 없을 때만 PC가 올린다. 그래서 GitHub과 PC가 같은 순간에 올리지 않는다. 설정이 없으면(GitHub 쪽 포함) 지금처럼 바로 실행한다.

### 구현하면서 더한 것 (2026-11-24)

- `require_board_check`: GitHub 서버는 실행마다 `state.json`이 없다. 게시판 목록을 못 읽으면 12:07과 12:37 실행이 둘 다 올릴 수 있어서, 이 설정이 켜져 있으면 게시판을 못 읽을 때 올리지 않고 실패로 끝낸다. 워크플로가 켜고, PC 기본값은 꺼짐(지금과 같음). 안전장치를 더한 것이라 기존 검토는 그대로
- 예약 켜기/끄기 스위치: 저장소 변수 `AUTO_POST`가 `on`일 때만 예약 실행이 동작한다. 수동 실행(`workflow_dispatch`)은 항상 가능. 그래서 병합해도 시험 성공 전에는 실제로 올리지 않는다
- 시각: cron은 UTC로 `7,37 3,12 * * *` (= 한국 12:07·12:37·21:07·21:37), 실행 중 `TZ=Asia/Seoul`

## 수용 기준

- [ ] AC-1: 워크플로가 `workflow_dispatch`(수동 실행)와 `schedule` 두 가지로 실행되고, 시각이 한국 시각 12:00·21:00 이후로 맞다.
- [ ] AC-2: 비밀 값은 모두 `secrets.*`에서만 읽고, 워크플로·코드·로그에 값이 적히지 않는다. `config.json`·`tokens.json`은 저장소에 커밋되지 않는다 (`.gitignore` 그대로).
- [ ] AC-3: `concurrency` 설정으로 같은 워크플로가 동시에 두 번 실행되지 않는다.
- [ ] AC-4: 게시 전 검토(게시판 중복·3시간 간격·사진 깨짐)와 게시 후 확인 코드가 바뀌지 않는다. `state.json` 없이도 게시판 목록 기준으로 같은 시간대 중복을 막는다.
- [ ] AC-5: **시험 모드**: 글을 올리지 않고 토큰 갱신 + 게시판 읽기 + 사진 확인까지만 하는 실행 방법이 있다 (예: `py cafe_poster.py check`). 처음엔 이것만 GitHub에서 돌려 본다.
- [ ] AC-6: 토큰 갱신 실패, 게시 실패 시 워크플로가 실패(빨간 X)로 끝나 GitHub이 메일로 알린다.
- [ ] AC-7: 로그에 토큰·Client Secret이 찍히지 않는다 (토큰 갱신 실패 메시지에서 응답 원문 대신 오류 코드만 출력).
- [ ] AC-8: Windows 전용 부분(`msvcrt` 잠금, 작업 스케줄러)이 Linux 서버에서 오류를 내지 않는다 (PC에서는 지금처럼 동작).
- [ ] AC-9: 시험 실행 결과로 "갱신 응답에 새 refresh_token이 오는지"를 값 없이(있다/없다, 같다/다르다) 로그에 남긴다. 새 값이 오면 Secrets 갱신 방법을 정한다.
- [ ] AC-10: 60일 멈춤 대비: README에 다시 켜는 방법을 적는다.
- [ ] AC-11: `py -m py_compile cafe_poster.py` 오류 없음, PC에서 `py cafe_poster.py preview`가 지금처럼 동작.
- [ ] AC-12: `backup_delay_minutes`가 있으면 `run`은 (가장 최근 정시 + 그 분)이 지나기 전에는 게시 검토도 하지 않고 끝난다. 없으면 지금과 같다. `config.example.json`과 README에 설명이 추가된다.
- [ ] AC-13: `.gitignore`의 비밀 파일 줄은 그대로이고, `post.txt`와 썸네일 3개만 예외로 허용된다. `git status`에 `config.json`, `tokens.json`, `state.json`, `log.txt`가 나오지 않는다.

## 비범위

- 실패 메신저 알림 (GitHub 기본 메일 알림만 사용)
- 썸네일별 조회수 자동 집계
- PC 예약 시각 변경 (작업 스케줄러는 그대로 두고 `backup_delay_minutes`로만 늦춤)

## 게시 영향

| 항목 | 내용 |
|---|---|
| 글 제목·본문 | 바뀌지 않음 |
| 게시 시각·횟수 | 12:00·21:00 하루 2번 그대로. GitHub 혼잡 때문에 몇 분~수십 분 늦을 수 있음 |
| 적용 시점 | 시험 모드 성공 → 사용자가 PC 예약 해제 → 그다음 정시부터 |
| 중복·누락 위험 | PC와 GitHub이 같이 돌므로 시간을 나눔: GitHub은 정시 ~ 정시+90분(정시 뒤와 30분 뒤 두 번), PC는 정시+90분 이후에만. GitHub 실행이 90분 넘게 늦어지는 드문 경우 같은 순간 실행 가능성이 남음 → 게시판 중복 확인이 한 번 더 막고, 게시 후 확인이 중복을 log에 경고 |
| 원본 글(31359494) 사진 | 계속 사용 |
| 설정 파일 | GitHub Secrets 사용 (값은 사용자가 GitHub 화면에서 직접 입력). `config.example.json`에 항목 추가 없음 예정 |

## 사용자가 직접 할 일 (구현 뒤)

1. GitHub 저장소 Settings → Secrets에 값 5개 직접 입력 (Claude는 값을 입력하지 않음)
2. Actions 탭에서 시험 모드 수동 실행 → 결과 확인
3. 시험 성공 뒤 PC `config.json`에 `"backup_delay_minutes": 90` 추가 (PC가 늦은 보충용이 됨), 그다음 GitHub 예약 켜기
4. 다음 정시 글이 GitHub에서 올라갔는지 log와 카페에서 확인

## 확인 방법

- 자동 (tester): 문법 검사, 워크플로 파일 읽기(비밀 값 출력 없음, concurrency, 시각), 코드 읽기
- 수동 (사용자): GitHub Actions 시험 모드 실행 결과, 전환 뒤 첫 정시 글의 카페 게시 확인
