#!/usr/bin/env node
// Claude Code Statusline - GSD Edition
// Shows: model+effort | cost | git branch+status | current task | directory | context usage

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

// ─── ANSI helpers ────────────────────────────────────────────────────────────
const c = {
  reset:   '\x1b[0m',
  dim:     '\x1b[2m',
  bold:    '\x1b[1m',
  blink:   '\x1b[5m',
  cyan:    '\x1b[36m',
  yellow:  '\x1b[33m',
  green:   '\x1b[32m',
  red:     '\x1b[31m',
  orange:  '\x1b[38;5;208m',
};

function paint(color, text) { return `${color}${text}${c.reset}`; }

// ─── Git helpers ─────────────────────────────────────────────────────────────
function gitExec(cmd, cwd) {
  return execSync(cmd, { cwd, timeout: 1000, stdio: ['pipe', 'pipe', 'pipe'] }).toString().trim();
}

function resolveGitRoot(candidates) {
  for (const dir of candidates) {
    if (!dir) continue;
    try { return gitExec('git rev-parse --show-toplevel', dir); } catch (_) {}
  }
  return null;
}

function getGitInfo(data) {
  const cwd = data.cwd || '';
  const currentDir = (data.workspace || {}).current_dir || '';
  const projectDir = (data.workspace || {}).project_dir || '';
  const gitRoot = resolveGitRoot([process.cwd(), process.env.PWD, cwd, currentDir, projectDir]);
  if (!gitRoot) return null;

  let branch;
  try { branch = gitExec('git rev-parse --abbrev-ref HEAD', gitRoot); } catch (_) { return null; }

  let dirty = false;
  try { dirty = gitExec('git status --porcelain', gitRoot).length > 0; } catch (_) {}

  let added = 0, removed = 0;
  const parse = (out) => {
    for (const line of out.split('\n')) {
      const p = line.trim().split(/\s+/);
      if (p.length >= 2) {
        const a = parseInt(p[0], 10), r = parseInt(p[1], 10);
        if (!isNaN(a) && !isNaN(r)) { added += a; removed += r; }
      }
    }
  };
  try { parse(gitExec('git diff --numstat', gitRoot)); } catch (_) {}
  try { parse(gitExec('git diff --cached --numstat', gitRoot)); } catch (_) {}

  return { branch, dirty, added, removed };
}

// ─── Read stdin ──────────────────────────────────────────────────────────────
let input = '';
const stdinTimeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  clearTimeout(stdinTimeout);
  try {
    const data = JSON.parse(input);
    const parts = [];
    const homeDir = os.homedir();
    const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(homeDir, '.claude');

    // 1. Model + effort
    const model = data.model?.display_name || 'Claude';
    let effort = '';
    try {
      const settings = JSON.parse(fs.readFileSync(path.join(claudeDir, 'settings.json'), 'utf8'));
      const level = (settings.effortLevel || '').toLowerCase();
      if (level === 'low')    effort = ' ' + paint(c.green,  'L');
      if (level === 'medium') effort = ' ' + paint(c.yellow, 'M');
      if (level === 'high')   effort = ' ' + paint(c.orange, 'H');
    } catch (_) {}
    parts.push(`${paint(c.cyan, model)}${effort}`);

    // 2. Session cost
    const cost = (data.cost || {}).total_cost_usd;
    if (cost != null) parts.push(paint(c.yellow, '$' + Number(cost).toFixed(2)));

    // 3. Git branch + status
    try {
      const git = getGitInfo(data);
      if (git) {
        const branchColor = git.dirty ? c.red : c.green;
        let gitPart = `${branchColor}${git.branch}${git.dirty ? '*' : ''}${c.reset}`;
        if (git.added > 0 || git.removed > 0) {
          if (git.added > 0)   gitPart += ` ${paint(c.green, '+' + git.added)}`;
          if (git.removed > 0) gitPart += ` ${paint(c.red, '-' + git.removed)}`;
        }
        parts.push(gitPart);
      }
    } catch (_) {}

    // 4. Current GSD task
    const session = data.session_id || '';
    const todosDir = path.join(claudeDir, 'todos');
    if (session && fs.existsSync(todosDir)) {
      try {
        const files = fs.readdirSync(todosDir)
          .filter(f => f.startsWith(session) && f.includes('-agent-') && f.endsWith('.json'))
          .map(f => ({ name: f, mtime: fs.statSync(path.join(todosDir, f)).mtime }))
          .sort((a, b) => b.mtime - a.mtime);
        if (files.length > 0) {
          const todos = JSON.parse(fs.readFileSync(path.join(todosDir, files[0].name), 'utf8'));
          const inProgress = todos.find(t => t.status === 'in_progress');
          if (inProgress && inProgress.activeForm) {
            parts.push(`${c.bold}${inProgress.activeForm}${c.reset}`);
          }
        }
      } catch (_) {}
    }

    // 5. Directory name
    const dir = data.workspace?.current_dir || data.cwd || process.cwd();
    parts.push(`${c.dim}${path.basename(dir)}${c.reset}`);

    // 6. Context window bar
    const remaining = (data.context_window || {}).remaining_percentage;
    if (remaining != null) {
      const BUFFER = 16.5;
      const usable = Math.max(0, ((remaining - BUFFER) / (100 - BUFFER)) * 100);
      const used = Math.max(0, Math.min(100, Math.round(100 - usable)));

      // Write bridge file for context-monitor hook
      if (session) {
        try {
          fs.writeFileSync(path.join(os.tmpdir(), `claude-ctx-${session}.json`), JSON.stringify({
            session_id: session, remaining_percentage: remaining,
            used_pct: used, timestamp: Math.floor(Date.now() / 1000)
          }));
        } catch (_) {}
      }

      const filled = Math.floor(used / 10);
      const bar = '\u2588'.repeat(filled) + '\u2591'.repeat(10 - filled);
      let color = c.green;
      let prefix = '';
      if (used >= 80)      { color = c.red; prefix = c.blink; }
      else if (used >= 65) { color = c.orange; }
      else if (used >= 50) { color = c.yellow; }
      parts.push(`${prefix}${color}${bar}${c.reset} ${color}${used}%${c.reset}`);
    }

    // GSD update banner
    let gsdUpdate = '';
    const cacheFile = path.join(claudeDir, 'cache', 'gsd-update-check.json');
    try {
      const cache = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
      if (cache.update_available) gsdUpdate = `${paint(c.yellow, '\u2b06 /gsd:update')} ${c.dim}\u2502${c.reset} `;
    } catch (_) {}

    process.stdout.write(gsdUpdate + parts.join(` ${c.dim}\u2502${c.reset} `));
  } catch (_) {}
});
