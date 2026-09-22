# Skills: these files are the source, not a backup

Anthony's own Claude skills are not files on this machine. Checked 2026-09-16: the app hands them to
each session in a temporary folder under `%APPDATA%\Claude\local-agent-mode-sessions\`, and that
folder does not exist on disk outside a running session. `~/.claude/plugins/` holds the official
marketplace plugins and nothing of his. So the skills are managed by Claude, not stored by him.

That has one consequence worth stating plainly: **editing the file the session hands you does
nothing.** The edit lives as long as the session does. A whole Copywriting section was written that
way on 2026-09-16 and would have been lost, except it had been copied here first.

So the copy in this folder is not a backup. It is the source. The working version is whatever has
been pasted into the app, and the way to change a skill is:

1. Edit the file here, and commit it. The diff is the only history these skills have.
2. Paste the result into the skill in the app, under **Customize**.

Deliberately not `.claude/skills/`: a plain path means Claude does not load these as project skills,
so nothing here competes with the real one.

| Skill | What it covers |
|---|---|
| `marketing/SKILL.md` | YouTube titles and on-screen headlines for SDSP and Cymatics, and the email copy rules for Anthony's own tools |

**The other three live in the private `avp-tool-rules` repo**, at `Github Repos/skills/`, not here:
`tool-launch` (the pipeline from first build to published page), `editing` and `youtube-upload`.
They are there rather than here because THIS repo is public and publishes on push, and between them
they name his Mac tester, say which tools are held back as paid, document the unsigned-app install
workaround, and carry YouTube channel handles and credential file paths. `marketing` stays here: it is
copywriting frameworks, which are defensible in public.

Same rule applies to all four. The file is the source, the app copy is the working version, and a change
in one is not a change in the other until it is pasted into Customize.
