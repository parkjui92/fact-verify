# fact-verify

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-purple.svg)

[한국어](README.md) · **English**

A [Claude Code](https://claude.com/claude-code) skill that checks, on your behalf, whether the sources an AI gathered are real.

Ask an AI to do your research and it hands back a tidy list of sources. The trouble is that some of those papers **don't exist at all**, and some real numbers arrive attached to the wrong document. Reading the draft won't tell you which is which. This isn't a general-purpose fact checker that rules on whether a statement is true — it's a tool that **opens the sources one by one and looks.**

## What it catches

| What actually happens | What the skill does about it |
|---|---|
| A citation carrying a paper ID (arXiv, DOI) that leads nowhere | **Opens the link or the paper to see whether it's really there** |
| Three outlets reporting the same thing — reassuring, until you notice all three ran one press release | Groups the copies together and recounts them as **one independent source, not three** |
| A blog post quoted as if it were a government statistic | **Sorts sources into four levels by how far you can rely on them.** The lowest level never counts as evidence on its own; the skill traces it back to the original |
| A perfectly real Korean paper or institute report written off as "source unknown" | Looks Korean material up separately in **KCI, RISS, the National Assembly Library, and NKIS** |

That last row is the thing international tools can't do for you. Those four are Korea's own catalogues — the national index of scholarly journals, the shared catalogue of university libraries, the parliamentary library, and the portal for government-funded research institutes. Korean journal articles, institute reports, and official publications often carry no DOI at all, so CrossRef, arXiv and Semantic Scholar index almost none of them. Point an international verification tool at them and a genuine article in *Korean Policy Studies Review*, or a real KISTEP issue paper, comes back "not found" — meaning **a source that exists gets written off as something the AI made up.** Deleting a real source is as damaging as letting a fake one through.

→ [Why I built this, and fuller usage notes](docs/why.md)

## How it runs

```
① sort sources into four levels → ② group the ones tracing back to the same origin → ③ open them to see if they exist
```

The default stance is doubt: something has to be confirmed before it passes. Every item comes back marked ✅ verified · ⚠️ couldn't confirm (**which means "not checked," not "wrong"**) · ❌ take it out · 🚫 no source at all — along with **why it was marked that way and what to do about it.** Whatever doesn't pass is also gathered into a **request to go re-research it**, which you can hand straight to whoever did the research.

Slot the skill into the middle of **research → verify → write** and any workflow gains one place where things get stopped and checked. It only means something if the one doing the checking is **a different AI** from the one that did the research and the writing — nobody catches their own work. Wiring is in [SKILL.md](SKILL.md).

## Install

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/parkjui92/fact-verify.git
```

Restart Claude Code and it's picked up automatically. Prompts work in Korean or English.

A free key from [data.go.kr](https://www.data.go.kr), Korea's open data portal, set as `DATA_GO_KR_KEY`, lets it query KCI, RISS and the National Assembly Library through their APIs rather than plain search. But **the key makes it better, it isn't required** — with no key it does as much as public search reaches and honestly leaves the rest at ⚠️.

## Using it

Just ask in plain language. The note on the right is how deep to look.

```
Here's this week's briefing draft. Check the sources.        ← standard (the default)
Are the references in this manuscript real? Many are Korean. ← Korean-language check
This report is going out externally — verify it at deep.     ← figures and dates against originals
I'm offline. Just the source levels and the ID formats.      ← quick (no internet needed)
```

With no depth given it runs `standard`. `quick` uses no internet, so it **can't confirm whether anything actually exists** — always re-run at `standard` or deeper before the document goes anywhere.

## What the result looks like

You get one row per item, like this.

| # | The claim | Source | Level | Verdict | Why, and what to do |
|---|---|---|---|---|---|
| 1 | New architecture doubles performance | arXiv 2404.99999 | 2 | ❌ | No paper carries that ID — remove it or find a real one |
| 2 | Industry investment surging | 2 business-daily articles | 3 | ⚠️ | Both ran the same press release — one independent source, not two |
| 3 | Innovation cluster effects | *Korean Policy Studies Review* 32(1) | 2 | ✅ | Confirmed in KCI (cited year is wrong: 2022 should be 2021) |

A summary sits above the table: how many items were checked, how many landed on each verdict, how the levels are distributed, and at what depth and when.

## Good to know

- **It needs internet.** Offline you only get `quick`. And when a full text sits behind a paywall (DBpia and the like) and can't be opened, the item is held at ⚠️ — **never declared wrong.**
- **It checks sources; it doesn't rule on whether a claim is true.** It confirms that a source exists and supports what's attached to it, but it doesn't certify that the claim itself is scholarly sound. The last call is a person's.
- **The AI doing the checking comes from the same family** as the one that produced the material. A checkpoint reduces errors; it doesn't remove them.
- The only things that leave your machine are **the links, IDs, and search terms (title, author) being checked.** The document itself is never sent to an outside service.
- The default source levels are written for **science and technology policy.** If you work in another field, add its agencies and journals to [references/tier-rules.md](references/tier-rules.md).

## Related work

**Plugins that write reports and proposals** — [policy-research-kit](https://github.com/parkjui92/policy-research-kit) (policy research reports) · [rnd-proposal-kit](https://github.com/parkjui92/rnd-proposal-kit) (Korean government R&D proposals) · [socsci-paper-kit](https://github.com/parkjui92/socsci-paper-kit) (social science papers)

**Plugins that build and edit** — [lecture-deck-kit](https://github.com/parkjui92/lecture-deck-kit) (HTML lecture slides you edit right in the browser)

**Single-purpose tools** — **fact-verify** (this repository) · [paper-proofread](https://github.com/parkjui92/paper-proofread) (Korean academic proofreading) · [form-tailor](https://github.com/parkjui92/form-tailor) (match an organization's document format) · [report-to-brief](https://github.com/parkjui92/report-to-brief) (shorten long reports)

## License

[MIT](LICENSE)
