#!/usr/bin/env node
// Bash / PowerShell 명령 실행 전에 위험한 명령을 막는 hook.
// Claude Code가 stdin으로 JSON({ tool_name, tool_input: { command }, cwd, ... })을 넘겨준다.
// 차단: 이유를 stderr에 쓰고 exit 2 / 통과: exit 0

const { execSync } = require("node:child_process");

// 지우면 안 되는 원본 글. 본문 사진이 이 글에 올라간 사진 주소(pstatic)를 쓴다.
const ORIGINAL_ARTICLE = "31359494";
const SECRET_FILE = /\b(config|tokens)\.json\b/i;

function block(reason) {
  process.stderr.write(`[차단됨] ${reason}\n사용자 승인이 필요한 작업입니다. 사용자에게 먼저 물어보세요.\n`);
  process.exit(2);
}

// 한 줄 명령을 ; && || | 줄바꿈 기준으로 나눈다.
function splitSegments(command) {
  return command.split(/[;&|\n]+/).map(s => s.trim()).filter(Boolean);
}

function currentBranch(cwd) {
  try {
    return execSync("git rev-parse --abbrev-ref HEAD", { cwd, stdio: ["ignore", "pipe", "ignore"] })
      .toString()
      .trim();
  } catch {
    return "";
  }
}

function check(command, cwd) {
  // 0) 원본 글 31359494 삭제·수정 (명령 전체에서 확인: 주소와 DELETE가 다른 줄에 있어도 막는다)
  if (command.includes(ORIGINAL_ARTICLE) && /delete|remove|-X\s*(PUT|PATCH)|-Method\s+(Put|Patch)/i.test(command)) {
    block(`원본 글(${ORIGINAL_ARTICLE})을 지우거나 고치면 매일 올리는 글의 본문 사진이 모두 깨집니다.`);
  }

  for (const seg of splitSegments(command)) {
    const tokens = seg.split(/\s+/);

    // 1) rm -rf (bash): rm 뒤에 재귀(r) + 강제(f) 옵션이 모두 있으면 차단
    const rmMatch = seg.match(/(?:^|\s|\()(?:sudo\s+)?rm\s+(.*)$/i);
    if (rmMatch) {
      const args = rmMatch[1].split(/\s+/);
      const hasR = args.some(a => /^-[a-zA-Z]*[rR][a-zA-Z]*$/.test(a) || a === "--recursive");
      const hasF = args.some(a => /^-[a-zA-Z]*f[a-zA-Z]*$/i.test(a) || a === "--force");
      if (hasR && hasF) block("rm -rf (재귀 강제 삭제)는 파일을 되돌릴 수 없게 지웁니다.");
    }

    // 2) PowerShell: Remove-Item(및 별칭) -Recurse -Force
    const isDelete = /(?:^|\s|\()(remove-item|ri|rm|rmdir|rd|del|erase|unlink)\s/i.test(seg);
    if (isDelete) {
      const hasRecurse = /\s-r(e(c(u(r(s(e)?)?)?)?)?)?\b/i.test(seg);
      const hasForce = /\s-fo(r(c(e)?)?)?\b/i.test(seg);
      if (hasRecurse && hasForce) block("Remove-Item -Recurse -Force (재귀 강제 삭제)는 파일을 되돌릴 수 없게 지웁니다.");
    }

    // 3) cmd 방식: rmdir /s /q, del /s /q
    if (/(?:^|\s)(rmdir|rd|del|erase)\s/i.test(seg) && /\s\/s\b/i.test(seg) && /\s\/q\b/i.test(seg)) {
      block("rmdir/del /s /q (하위 폴더까지 묻지 않고 삭제)는 되돌릴 수 없습니다.");
    }

    // 4) 비밀 파일(config.json, tokens.json) 지우기·덮어쓰기
    if (SECRET_FILE.test(seg)) {
      if (isDelete || /(?:^|\s)(mv|move|move-item|ren|rename-item)\s/i.test(seg)) {
        block("config.json / tokens.json을 지우거나 옮기면 자동 게시가 멈춥니다.");
      }
      if (/>\s*["']?[^\s"']*(config|tokens)\.json/i.test(seg) || /\b(set-content|out-file|add-content|clear-content)\b/i.test(seg)) {
        block("config.json / tokens.json을 덮어쓰면 설정이나 로그인 정보가 사라집니다.");
      }
    }

    // 5) 비밀 파일을 git에 넣는 명령
    if (/\bgit\b.*\badd\b/i.test(seg)) {
      if (/\s(-f|--force)\b/i.test(seg) || /\s-[a-zA-Z]*f[a-zA-Z]*\b/.test(seg)) {
        block("git add -f(강제 추가)는 .gitignore를 무시해서 비밀 파일이 올라갈 수 있습니다.");
      }
      if (SECRET_FILE.test(seg)) block("config.json / tokens.json은 비밀 정보라 git에 넣을 수 없습니다.");
    }
    if (/\bgit\b.*\bupdate-index\b/i.test(seg) && SECRET_FILE.test(seg)) {
      block("config.json / tokens.json을 git에 넣을 수 있는 명령입니다.");
    }

    // 6) git clean: -x 옵션이면 .gitignore로 숨긴 config.json / tokens.json까지 지운다
    if (/\bgit\b.*\bclean\b/i.test(seg)) {
      block("git clean은 git이 모르는 파일(config.json, tokens.json, 사진 등)을 되돌릴 수 없게 지웁니다.");
    }

    // 7) git push 관련
    if (/\bgit\b.*\bpush\b/i.test(seg)) {
      if (/\s(--force|--force-with-lease|--force-if-includes)\b/i.test(seg) || /\s-[a-zA-Z]*f\b/.test(seg) || /\s\+\S/.test(seg)) {
        block("git push --force(강제 푸시)는 원격 저장소의 기록을 덮어씁니다.");
      }
      if (/\s(--all|--mirror)\b/i.test(seg)) {
        block("git push --all / --mirror는 main 브랜치까지 한꺼번에 푸시합니다.");
      }
      if (/(\s|:)(main|master)(\s|$)/i.test(seg)) {
        block("main 브랜치로 직접 푸시할 수 없습니다. 새 브랜치에서 작업하고 푸시하세요.");
      }
      // 'git push' 또는 'git push origin'처럼 브랜치를 생략하면 현재 브랜치가 푸시된다.
      const afterPush = tokens.slice(tokens.findIndex(t => /^push$/i.test(t)) + 1).filter(t => !t.startsWith("-"));
      if (afterPush.length <= 1) {
        const branch = currentBranch(cwd);
        if (branch === "main" || branch === "master") {
          block(`지금 브랜치가 ${branch}입니다. main 브랜치로 직접 푸시할 수 없습니다.`);
        }
      }
    }

    // 8) git reset --hard
    if (/\bgit\b.*\breset\b.*--hard\b/i.test(seg)) {
      block("git reset --hard는 저장하지 않은 변경 사항을 모두 지웁니다.");
    }

    // 9) 실제 네이버 카페 게시 / 자동 게시 일정 변경
    const poster = seg.match(/cafe_poster\.py["']?\s+(post|run|schedule|unschedule)\b/i);
    if (poster) {
      const what = { post: "지금 바로 카페에 글을 올립니다", run: "조건이 맞으면 카페에 글을 올립니다",
        schedule: "Windows 작업 스케줄러의 자동 게시 등록을 바꿉니다", unschedule: "자동 게시를 멈춥니다" };
      block(`cafe_poster.py ${poster[1].toLowerCase()}: ${what[poster[1].toLowerCase()]}. 사용자가 직접 실행해야 합니다.`);
    }
    if (/NaverCafeAutoPost/i.test(seg) && /(\/delete|\/change|\/end|unregister-scheduledtask|disable-scheduledtask|set-scheduledtask|stop-scheduledtask)/i.test(seg)) {
      block("자동 게시 예약 작업(NaverCafeAutoPost)을 지우거나 바꾸면 00:00 / 12:00 게시가 멈춥니다.");
    }

    // 10) 네이버 API에 직접 쓰기·지우기 요청 (글 삭제·수정·게시)
    if (/naver\.com/i.test(seg) && /(-X\s*(DELETE|PUT|PATCH|POST)|-Method\s+(Delete|Put|Patch|Post)|--request\s+(DELETE|PUT|PATCH|POST))/i.test(seg)) {
      block("네이버 카페 API에 직접 쓰기·삭제 요청을 보내는 명령입니다.");
    }
  }
}

let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => (raw += chunk));
process.stdin.on("end", () => {
  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    process.stderr.write("guard-bash: 입력 JSON을 읽지 못했습니다.\n");
    process.exit(1);
  }
  const command = (input.tool_input && input.tool_input.command) || "";
  check(command, input.cwd || process.cwd());
  process.exit(0);
});
