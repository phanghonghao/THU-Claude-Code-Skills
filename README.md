# THU Awesome Skills

A curated collection of reusable Codex skills, organized by publicability and
privacy risk.

## Public collection

This repository currently contains **33 skills**:

- **Document and format conversion**: `any2md`, `html2md`, `html2pdf`,
  `html2tex`, `markitdown`, `md2docx`, `md2tex`, `pdf-reader`, `pdf2word`,
  `word2html`, `word2md`, `word2pdf`
- **Research and knowledge workflows**: `github-trending`,
  `paper-html-onepage`, `paper-repro`, `repo-docs`, `repo-docs-zh`,
  `web-search-fallback`
- **Writing, presentation, and media utilities**: `cheatsheat`, `fincomp-deck`,
  `html-slides`, `latex-beamer`, `merge`, `notes`, `poster`
- **Skill and tool synchronization**: `claude2anti`, `claude2codex`,
  `codex2claude`, `git-push`
- **Specialized reusable tools**: `ai-gen`, `assignment-word`, `img-reader`,
  `resume-builder`

Install all public skills into a Codex or Claude skills directory by copying
the contents of `skills/`.

```powershell
Copy-Item -Recurse .\skills\* "$env:USERPROFILE\.codex\skills\"
```

## Classification policy

The source inventory was classified into three groups:

1. **Public**: reusable skills without a necessary dependency on personal
   servers, accounts, private projects, or personal records.
2. **Audit-only**: potentially reusable skills that require sanitization,
   permission checks, or removal of personal examples. From this group,
   `resume-builder` is the only skill included in this repository.
3. **Private or excluded**: skills tied to personal infrastructure, training
   jobs, credentials, local machine state, or external projects.

## Excluded source material

The following source groups are intentionally absent:

- All `ts-*` skills: retained with their original source owner and not part of
  this collection.
- All `lark-*` skills: retained with their original source owner and not part
  of this collection.
- `jianying-editor`: retained with its original source owner and not included.
- `oh-my-rss`: retained with its original source owner and not included.
- GPU, remote-training, API-key, machine-health, and personal logging skills.
- The remaining audit-only skills, including personal documents, financial
  workflows, certificates, and project-specific agents.
- Codex `.system` skills, credentials, logs, caches, `.env` files, and runtime
  artifacts.

## Provenance

The public skills were selected from the original local Codex skills inventory.
Excluded skills remain traceable to that original inventory but are not
redistributed here. Individual skills may retain their own upstream attribution
and license notices where applicable.

## License

MIT. See [LICENSE](LICENSE).
