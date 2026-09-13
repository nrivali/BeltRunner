# Shared game source

The user edits this game with Claude as well as Codex. Preserve concurrent work.

- Before editing `belt-runner-3d.html`, read its current contents from disk and record its SHA-256. Never restore or replace the whole file from an earlier task snapshot.
- Save a timestamped backup of the current file before changing it. Apply only the requested, narrowly scoped changes.
- Recheck the file hash immediately before writing. If it changed, reread and reconcile the latest contents before applying the patch. Do not blindly reapply edits that another process removed.
- Review the resulting diff against the immediate pre-edit backup. Preserve all unrelated changes from Claude or the user. If changes conflict and intent cannot be determined, ask the user.
- Before any push or publication, identify and check the authoritative latest game version, reconcile changes, and validate that exact result. A push request does not authorize overwriting newer work.
- This folder had no Git repository or configured remote when checked on 2026-09-12. Do not claim remote freshness without verifying the actual source location.
