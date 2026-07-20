# fact-verify

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-purple.svg)

[한국어](README.md) · **English**

A [Claude Code](https://claude.com/claude-code) skill that **audits the sources behind AI-gathered research** before you trust them.
Not a general-purpose fact checker — a **source-discipline tool** for research and policy documents: it checks whether a source exists, whether it actually supports the claim attached to it, and whether several apparently independent sources all trace back to one press release.

<!-- demo GIF goes here -->

## What it catches

| Failure seen in practice | Device |
|---|---|
| Citations with nonexistent arXiv IDs or DOIs (hallucination) | **Step 3 — existence check**: resolve the identifier for real |
| Three news outlets that look like corroboration but all ran the same press release (**fake cross-validation**) | **Step 2 — re-quotation chain detection**: recount independent sources |
| A blog post cited as though it were a government statistic (credibility laundering) | **Step 1 — 4-tier classification**: Tier 4 can never stand alone; trace to the original |
| Korean-language papers and institute reports marked "unverifiable" because international databases don't index them | **Step 3-D — Korean verification sources**: KCI, RISS, National Assembly Library, NKIS |

That last row is **what international tools cannot do**. Korean journal articles, government-funded institute reports, and official publications frequently have no DOI at all, and CrossRef, OpenAlex, Semantic Scholar and arXiv index almost none of them. So a verification tool built on those databases reports a perfectly real article in *Korean Policy Studies Review* — a KCI-indexed journal — or a genuine KISTEP issue paper as "not found," and **real sources get flagged as hallucinations.** Deleting a real citation is as damaging as letting a fake one through.

→ [Why I built this · detailed usage](docs/why.md)

## The three-step protocol

```
Step 1 tier classification → Step 2 re-quotation chain detection → Step 3 existence check (+ 3-D Korean registries)
```

The default state is doubt; something has to earn a pass. Every item comes back with one of ✅ VERIFIED · ⚠️ NEEDS_REVIEW (not "wrong" but "could not be confirmed") · ❌ REJECT (take it out of the document) · 🚫 NO_SOURCE (a factual claim with no source), plus **a reason and an action** — and whatever does not pass also comes back as a **re-investigation request** you can hand straight to whoever did the research.
Place it as `research → fact-verify → writing` and any research pipeline gains a gate — which means nothing unless **the verifier is a different agent** from the researcher and the writer. YAML wiring in [SKILL.md](SKILL.md).

## Install

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/parkjui92/fact-verify.git
```

Restart Claude Code and it is picked up automatically; prompts work in Korean or English. A free [data.go.kr](https://www.data.go.kr) key in `DATA_GO_KR_KEY` upgrades Korean lookups to the KCI / RISS / National Assembly Library APIs, but **the key is a performance option, not a requirement** — without it the skill verifies what public search reaches and honestly leaves the rest at ⚠️.

## Usage

```
Here's this week's briefing draft. Verify the sources.         ← standard (default)
Are the references in this manuscript real? Many are Korean.   ← Korean-language check
This report is going out externally. Verify it at deep.        ← figures/dates vs. originals
I'm offline. Just tier classification and identifier formats.  ← quick (no network)
```

`quick` **does not check existence**, so re-run at standard or deeper before publishing. With no depth specified it runs `standard`.

## Sample output

| # | Claim (abbrev.) | Source | Tier | Verdict | Reason / action |
|---|---|---|---|---|---|
| 1 | New architecture doubles performance | arXiv 2404.99999 | 2 | ❌ | ID does not exist — remove or re-research |
| 2 | Industry investment surging | 2 business-daily articles | 3 | ⚠️ | Both re-quote the same press release — one independent source |
| 3 | Innovation cluster effects | Korean Policy Studies Review 32(1) | 2 | ✅ | Confirmed via KCI (citation year error flagged: 2022 → 2021) |

Above the table sits a summary line: item count, counts per verdict, tier distribution, depth and timestamp. Full report: [examples/verification-report-example.md](examples/verification-report-example.md)

## Limitations

- **Web access is required.** Offline, only `quick` depth is available; paywalled full texts (DBpia and similar) are held at ⚠️ when they cannot be checked — never declared wrong
- **A source-discipline tool, not a truth oracle.** It checks that a source exists and matches the claim; it does not certify the scholarly validity of the claim itself. Final responsibility stays with a human
- **The verifier runs on a model from the same family** as whatever produced the material. Gates reduce errors; they do not eliminate them
- The only things sent outside are **the URLs, identifiers, and search terms (title, author) being checked**. The document itself is never sent to an external service
- The default tier lists are written for **science and technology policy (STI)** — add your own field's agencies, journals, and trade press to [references/tier-rules.md](references/tier-rules.md)

## Series

**Agent-team kits** — [policy-research-kit](https://github.com/parkjui92/policy-research-kit) (policy research reports) · [rnd-proposal-kit](https://github.com/parkjui92/rnd-proposal-kit) (Korean government R&D proposals) · [socsci-paper-kit](https://github.com/parkjui92/socsci-paper-kit) (social science papers)

**Authoring kit** — [lecture-deck-kit](https://github.com/parkjui92/lecture-deck-kit) (HTML lecture decks with in-browser live editing)

**Standalone skills** — **fact-verify** (this repository, source verification) · [paper-proofread](https://github.com/parkjui92/paper-proofread) (Korean academic proofreading) · [form-tailor](https://github.com/parkjui92/form-tailor) (institutional document formats) · [report-to-brief](https://github.com/parkjui92/report-to-brief) (report compression)

## License

[MIT](LICENSE)
