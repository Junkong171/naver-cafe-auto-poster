#!/usr/bin/env node
// 파일 편집(Edit / Write / MultiEdit / NotebookEdit) 전에 보호 파일을 막는 hook.
// Claude Code가 stdin으로 JSON({ tool_input: { file_path, ... }, cwd, ... })을 넘겨준다.
// 차단: 이유를 stderr에 쓰고 exit 2 / 통과: exit 0

const path = require("node:path");

function block(reason) {
  process.stderr.write(`[차단됨] ${reason}\n이 파일은 사용자 승인 없이 수정할 수 없습니다. 사용자에게 먼저 물어보세요.\n`);
  process.exit(2);
}

// .gitignore에서 비밀 파일 줄이 빠지면 다음 git add 때 비밀이 올라갈 수 있다.
const SECRET_IGNORES = ["config.json", "tokens.json"];

function keepsSecretIgnores(before, after) {
  return SECRET_IGNORES.every(name => !before.includes(name) || after.includes(name));
}

function check(toolInput, cwd) {
  const filePath = toolInput.file_path || toolInput.notebook_path || "";
  if (!filePath) return;
  // Windows 경로(\)를 /로 바꾸고, 대소문자 구분 없이 비교한다.
  const full = path.resolve(cwd, filePath).replace(/\\/g, "/").toLowerCase();
  const name = full.split("/").pop();

  if (name === "config.json") block("config.json: 네이버 Client ID/Secret이 들어 있는 실제 설정 파일입니다.");
  if (name === "tokens.json") block("tokens.json: 네이버 로그인 토큰(계정 열쇠) 파일입니다.");
  if (/^\.env(\..+)?$/.test(name)) block(`${name}: 환경 변수(.env 계열) 파일입니다.`);
  if (full.includes("/.git/")) block(".git 폴더 안의 파일은 git 내부 데이터입니다.");
  if (full.endsWith("/.claude/settings.json")) block(".claude/settings.json: 권한과 hook 설정 파일입니다.");

  if (name === ".gitignore") {
    if (typeof toolInput.content === "string" && !SECRET_IGNORES.every(n => toolInput.content.includes(n))) {
      block(".gitignore에서 config.json / tokens.json 줄을 빼면 비밀 정보가 GitHub에 올라갈 수 있습니다.");
    }
    const edits = toolInput.edits || [{ old_string: toolInput.old_string, new_string: toolInput.new_string }];
    for (const e of edits) {
      if (typeof e.old_string === "string" && !keepsSecretIgnores(e.old_string, e.new_string || "")) {
        block(".gitignore에서 config.json / tokens.json 줄을 빼면 비밀 정보가 GitHub에 올라갈 수 있습니다.");
      }
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
    process.stderr.write("guard-files: 입력 JSON을 읽지 못했습니다.\n");
    process.exit(1);
  }
  check(input.tool_input || {}, input.cwd || process.cwd());
  process.exit(0);
});
