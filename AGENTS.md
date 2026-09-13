# Shared game source

The user edits this game with Claude as well as Codex. Preserve concurrent work.

- Before editing `belt-runner-3d.html`, read its current contents from disk and record its SHA-256. Never restore or replace the whole file from an earlier task snapshot.
- Save a timestamped backup of the current file before changing it. Apply only the requested, narrowly scoped changes.
- Recheck the file hash immediately before writing. If it changed, reread and reconcile the latest contents before applying the patch. Do not blindly reapply edits that another process removed.
- Review the resulting diff against the immediate pre-edit backup. Preserve all unrelated changes from Claude or the user. If changes conflict and intent cannot be determined, ask the user.
- Before any push or publication, identify and check the authoritative latest game version, reconcile changes, and validate that exact result. A push request does not authorize overwriting newer work.
- This folder became a Git repository on 2026-09-12 (branch `main`). Git is at `C:\Program Files\Git\cmd\git.exe` if it is not on PATH.
- Remote `origin` is https://github.com/nrivali/BeltRunner (public, added 2026-09-12). GitHub Pages serves `main` at https://nrivali.github.io/BeltRunner/ (index.html redirects to the game), so every `git push origin main` is a deploy; the build takes about a minute. The GitHub CLI is at `C:\Program Files\GitHub CLI\gh.exe`, signed in as nrivali. Push only after the checks above.

## Git workflow (both agents)

- Edit files in place in this folder. Never copy a whole file in from elsewhere.
- Before starting a task: `git status` must be clean (commit or ask about anything left over), then `git log -1` to see the latest commit.
- Before editing `belt-runner-3d.html`: `git diff` / `git status` to confirm nothing uncommitted is sitting there from the other agent. If there is, leave it alone and ask the user.
- After finishing a change: `git add -A` and `git commit` with a message that says what changed and which agent made it (add a `Co-Authored-By:` trailer for the agent). One task, one commit.
- `elevenlabs.key`, `backups/`, `*.zip` and `*.blend1` are ignored on purpose. Do not force-add them.
- Publishing (Claude's artifact) always happens from the committed working tree, never from a copy.
- Bump `GAME_VERSION` in `belt-runner-3d.html` on every commit that changes gameplay or assets.
