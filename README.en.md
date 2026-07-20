# fact-verify

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-purple.svg)

[한국어](README.md) · **English**

> A [Claude Code](https://claude.com/claude-code) skill that **audits the sources behind AI-gathered research** before you trust them.
> Not a general-purpose fact checker — a **source-discipline tool** for research and policy documents. It checks whether a source exists, whether it actually supports the claim attached to it, and whether several apparently independent sources all trace back to one press release. Every item comes back with a verdict — ✅ / ⚠️ / ❌ / 🚫 — and **what to do about it**.
> **It also verifies Korean-language scholarship and policy literature (KCI, RISS, National Assembly Library, NKIS), which is what international tools cannot do.**

---

## Why I built this

Anyone who has handed research to an LLM has had the same experience. **The output is smooth.** The prose is good, the structure is plausible, and there are ten working URLs at the bottom. So it looks like a document that has already been checked.

The trouble starts when you open those URLs one by one:

- **Indicator confusion** — "AI service usage rate: 67.8%." The figure 67.8% is real. It just belongs to an entirely different indicator (digital literacy level among those aged 65+, 2023). This is not a fabricated number; it is a **real number attached to the wrong indicator**, which makes it *harder* to catch than an invented one.
- **Misattribution** — the research report cited as evidence does not contain the figure at all. The full 237-page PDF was parsed to confirm. The real source was a different survey by a different institution.
- And both errors were written in a **tone of certainty**. With ten genuine URLs listed at the end, the document read as though **the whole thing had been verified.**

> Both examples are quoted from a measured audit published by the sister repository policy-research-kit, run against vanilla Claude Code output. A neutral third-party session opened all 14 cited URLs from both sides and checked them against the primary sources. It is a single run on a single topic — read it as a reproducible case, not a statistical claim. Full record: [policy-research-kit/docs/vanilla-vs-kit.md](https://github.com/parkjui92/policy-research-kit/blob/main/docs/vanilla-vs-kit.md)

This is not a model-quality problem. It is what happens when a process **attaches 10 citations while opening zero source documents**. Citations get completed from search-result snippets, so when one is wrong, nothing marks the spot. And in research output that is unusually expensive: a figure published in a briefing gets re-cited, becomes the basis for a report, and comes back months later as "where did this number come from?"

So what was needed was not a better summary. It was **a step that filters before you believe**.

This skill began as the built-in verifier (`fact-verifier`) inside an **R&D trends research agent team** (built April 2026). It ran in production as the gate that screened the weekly briefing material an investigator agent had gathered, before any of it reached the writer. This repository is that gate, generalized so it can be dropped into any research pipeline. Which is why it is designed as **a step in a process**, not as a document reader: it issues a verdict, and for anything that does not pass, it produces a **re-investigation request** you can hand straight back to whoever did the research.

The failures encountered in practice were of different kinds, and each kind demanded a different device. The three-step protocol was assembled one piece at a time.

| Failure seen in practice | Device |
|---|---|
| Citations with nonexistent arXiv IDs or DOIs (hallucination) | **Step 3 — existence check**: resolve the identifier for real |
| A URL that loads but does not contain the cited content (source–claim mismatch) | **Step 3 — existence check**: fetch the page and compare it to the claim |
| Three news outlets that look like corroboration but all ran the same press release (**fake cross-validation**) | **Step 2 — re-quotation chain detection**: recount independent sources |
| A blog post cited as though it were a government statistic (credibility laundering) | **Step 1 — 4-tier classification**: Tier 4 can never stand alone; trace to the original |
| Korean-language papers and institute reports marked "unverifiable" because international databases don't index them | **Step 3-D — Korean verification sources** (v1.1): KCI, RISS, National Assembly Library, NKIS |

### Why Korean sources need their own verifier

That last row is the problem you only hit when you work in Korea, and it is the reason this skill exists in the form it does.

Korean-language scholarship and policy literature largely lives outside the international citation infrastructure. **Korean journal articles, government-funded institute reports, and official publications frequently have no DOI at all**, and CrossRef, OpenAlex, Semantic Scholar, and arXiv index almost none of them. So a verification tool built on those databases will report a perfectly real article in *Korean Policy Studies Review* — a KCI-indexed journal — or a genuine KISTEP issue paper as "not found." Run verification in that state and **real sources get flagged as hallucinations.** Deleting a real citation is as damaging as letting a fake one through.

The fix is to query the Korean registries directly. For readers unfamiliar with them:

| Source | What it is |
|---|---|
| **KCI** (Korea Citation Index) | The national index of Korean scholarly journals, operated by the National Research Foundation of Korea. Coverage of accredited domestic journals and their citation data — roughly the Korean analogue of Web of Science for domestic publications |
| **RISS** | Research Information Sharing Service, operated by KERIS (the national education/research IT agency). University theses and dissertations, plus academic resources |
| **National Assembly Library** | Broad bibliographic coverage — books, articles, and legislative bills — from the library of Korea's legislature |
| **NKIS** | National Knowledge Information System, the portal aggregating reports from Korea's government-funded research institutes (KDI, KIEP, STEPI, KISTEP and peers). These reports carry real policy weight and are cited constantly, but they are not journal articles and carry no DOI |
| **PRISM** | The government's registry of commissioned policy research projects |
| **NTIS** | Korea's national R&D project database. Project numbers are 10 digits and are routinely cited in proposals and reports |
| **National Library of Korea** | ISBN and bibliographic records for books and monograph-form reports |

Two more names that appear below: **DBpia** is a major Korean academic database whose full texts sit behind a paywall, and **data.go.kr** is Korea's national open-data portal, which issues free API keys for several of the registries above.

---

## How it works — the three-step protocol

**The design stance is skepticism.** The default state is doubt; something has to earn a pass. The skill assumes as a constant that an AI may have written the material, and scrutinizes plausible-sounding claims *more* rather than less. When in doubt, it excludes.

**Step 1 — Source tier classification.** Every source is sorted into four tiers. **Tier 1**, official government and institutional sources (`.go.kr`, `.gov`, `europa.eu`, and equivalents); **Tier 2**, scholarly and government-funded research (peer-reviewed journals, KCI-indexed Korean journals, institutes such as KISTEP and STEPI); **Tier 3**, major news media; **Tier 4**, blogs, social media, forums, anonymous material. Tiers 1 and 2 can stand as sole evidence. **Tier 4 never can** — if a Tier 4 item looks useful, the skill traces the paper or official announcement it cites and, on confirmation, **promotes the citation to that original source's tier** rather than citing the blog. Domains not on the list are classified conservatively (downward), with the reasoning recorded.

**Step 2 — Cross-consistency.** This is where the skill's signature feature, **re-quotation chain detection**, runs.

```
❌ Fake cross-validation
   Claim X is reported by three business dailies.
   → If all three ran the same ministry press release, that is one source.

✅ Real cross-validation
   Claim X appears consistently in ① an official government release,
   ② independently reported journalism, ③ a journal commentary
   → three independent sources.
```

The skill looks for shared-origin markers in each article — "according to a statement by," "the ministry announced," "per the press release" — walks the citation chain back, collapses re-quotations into a single count, and reports how many genuinely independent sources remain. Where sources report the same figure differently, it checks the original or holds the item.

**Step 3 — Existence check.** URLs are actually fetched: a 404 raises hallucination suspicion, and a page that loads but does not contain the claim is a source–claim mismatch. DOIs are resolved through `doi.org` and their metadata compared against the citation; arXiv IDs are checked at `arxiv.org/abs/` for existence and title. NTIS project numbers (10 digits) and ISBNs are checked for format and record. Publication dates are compared against the source, and cited figures are compared to the original **including units and base year**.

**Step 3-D — Korean scholarship and policy verification (v1.1).** Because Korean-language material is expected *not* to appear in the international path above, it gets its own route through KCI, RISS, the National Assembly Library, NKIS, PRISM, and the National Library of Korea (see the table earlier for what each covers).

The skill queries by author, title, year, and publication venue, then compares the returned bibliographic record against the citation — which catches **wrong year, wrong volume/issue, and wrong journal name** on sources that do exist. Only when an item cannot be found in *either* the Korean or the international registries is it treated as a suspected hallucination. Details and access notes are in [references/korea-sources.md](references/korea-sources.md).

---

## Install

Install into Claude Code's user skills directory (`~/.claude/skills/`).

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/parkjui92/fact-verify.git
```

Restart Claude Code and it is picked up automatically. No configuration is required; requests like "verify the sources in this" will trigger it. Prompts work in Korean or English.

### Optional — enable precise Korean API verification

The skill **works with no key at all**, using each portal's public search. Setting a free [data.go.kr](https://www.data.go.kr) API key (most datasets are auto-approved) upgrades it automatically to the KCI / RISS / National Assembly Library REST APIs, which allow **bulk and field-level** verification.

```bash
# in ~/.zshrc or equivalent
export DATA_GO_KR_KEY="your_decoded_key"
```

The key is a performance option, not a requirement. Without it the skill verifies what public search can reach and honestly leaves the rest at ⚠️ — **it does not pretend to capabilities it does not have.** Dataset list and signup steps: [references/korea-sources.md](references/korea-sources.md).

---

## How to use it

Two input shapes are accepted: **structured input** (a list of `claim — source` pairs, typically the output of another research agent or skill) and **free text** (a briefing, report draft, or article draft). With free text, the skill first extracts "factual claim + attached source" pairs to build the verification list — and in doing so, any **factual claim with no source at all** is flagged 🚫 `NO_SOURCE` on its own. The question is never how many URLs the document carries; it is **which sentence rests on what**.

### Scenario 1 — Before publishing a briefing (standard)

```
Here's this week's trends briefing draft. Verify the sources I'm about to publish.
```

The most common use, and the default. Claim–source pairs are extracted, tiered, URLs opened, DOIs and arXiv IDs resolved, Korean-language items checked against KCI and NKIS. You get back a per-item verdict table plus a re-investigation request.

### Scenario 2 — Do these references actually exist? (including Korean)

```
Check whether the references in this manuscript are real publications.
A lot of them are Korean-language.
```

The most dangerous spot in any AI-assisted manuscript. The point here is that a Korean-language work returning "not found" from an international database is **not** treated as a hallucination on that basis alone. And verification does not stop at existence: the journal name, volume/issue, and year in the record are compared against the citation, so items where "the paper is real but the volume number is wrong" surface too. Those don't need the passage removed — just the reference corrected.

### Scenario 3 — Documents that leave the building (deep)

```
This report is going out externally. Verify it at deep.
```

On top of standard, this requires **two independent sources for key claims** and compares each cited figure and date against the original. Re-quotation chain detection runs in earnest at this depth — this is where "reported by three outlets" comes back as one independent source. Use it for submissions, articles, and external reports: anything you cannot recall after it ships.

### Scenario 4 — No network, or still drafting (quick)

```
I'm offline. Just run the tier classification and identifier format checks.
```

Tier classification and identifier *format* checks only, no network needed. Problems like an arXiv ID that violates the `YYMM.NNNNN` pattern, or a document whose key claims all rest on Tier 4, are already visible at this stage. But quick **does not check existence**, so re-run at standard or deeper before publishing.

### Choosing a depth

| Depth | Scope | When |
|---|---|---|
| `quick` | Step 1 (tier classification) + identifier **format** check. No network required | Fast pass on an early draft; offline |
| `standard` **(default)** | + Step 3 existence check (URL fetch, DOI/arXiv resolve, Korean registries via public search) | Before publishing a briefing or internal report |
| `deep` | + Step 2 cross-independence (two independent sources for key claims), figure and date comparison against originals | External reports, articles, submissions |

Deeper settings mean more external lookups and more time. Running `deep` on an early draft is usually waste; pushing an external document out on `quick` is usually an incident. If you don't specify a depth, it runs `standard`.

### Sample output

| # | Claim (abbrev.) | Source | Tier | Verdict | Reason / action |
|---|---|---|---|---|---|
| 1 | Government AI R&D budget up 20% | msit.go.kr press release | 1 | ✅ | Original confirmed, figure matches |
| 2 | New architecture doubles performance | arXiv 2404.99999 | 2 | ❌ | ID does not exist — remove or re-research |
| 3 | Industry investment surging | 2 business-daily articles | 3 | ⚠️ | Both re-quote the same press release — one independent source |
| 4 | Innovation cluster effects | Korean Policy Studies Review 32(1) | 2 | ✅ | Confirmed via KCI (citation year error flagged: 2022 → 2021) |
| 5 | Results from an overseas case | Personal blog | 4 | ❌ | Tier 4 cannot stand alone — locate the original report |

Above the table sits a summary line: item count, counts per verdict, tier distribution, depth and timestamp. A complete report is at [examples/verification-report-example.md](examples/verification-report-example.md) (a worked example over eight items from a hypothetical briefing draft).

---

## What to do with each of the four verdicts

A verdict is a **signal to support your judgment**, not a sign-off. That is why every verdict carries a reason and an action.

### ✅ VERIFIED — passed, but read the tier with it

It means the item cleared all three steps, not that it is unconditionally safe. If a claim rests on a Tier 3 (news) source alone, prefer promoting the citation to the Tier 1 or 2 original where one exists. Also note that VERIFIED sometimes arrives **with a bibliographic correction attached** — the work is real, but the cited volume or year is wrong. That is not a reason to cut the passage; it is a reference-list fix. Don't skip past it.

### ⚠️ NEEDS_REVIEW — not "wrong," but "could not be confirmed"

The most frequent verdict and the most frequently misread. **The action depends on the cause:**

- **Paywalled or login-gated originals** (DBpia full texts and similar) → have someone with access open them. Until then, either carry the sentence with an explicit downgrade marker or drop it.
- **Re-quotation chain** → **replace the citation** with the original press release or announcement. Adding more articles from the same lineage is not a fix.
- **Figure mismatch** → open the original and determine which value is correct.
- **Only a partial title match found** → pick the right candidate from those offered, or ask the researcher for the exact bibliographic record.

The one thing that matters is not quietly promoting ⚠️ to ✅. **Recording that something could not be confirmed is far safer than implying it was.**

### ❌ REJECT — take it out of the document

This covers 404s, identifiers that don't resolve, source–claim mismatches, and Tier 4 standing alone. The trap is treating it as "just find another source." **If an arXiv ID does not exist at all, the citation format isn't what's broken — you should be asking where the claim itself came from.** Send it back for re-investigation, and if it still cannot be confirmed, record it as a confirmed REJECT.

### 🚫 NO_SOURCE — attach a source, soften the claim, or cut it

Sentences like "industry sources say deregulation is imminent." Three options: ① find and attach a source, ② downgrade it from assertion to observation or estimate, ③ remove it. Anything but leaving it standing in a tone of certainty — in the failure cases above, the most dangerous property was not the error itself but the fact that **the error was written as settled fact**.

### The re-investigation request

Verifying and stopping there just leaves the next person stuck in the same place. So alongside the verdict table, the skill writes a per-item request stating **what is wrong, why, and what would resolve it** — in a form you can hand to a human researcher or to an investigator agent unchanged.

```
#3: arXiv 2404.99999 does not exist. If this is a real paper, please confirm
    the correct ID or DOI. If it can't be confirmed, we drop it.
#7: A KISTEP issue paper is expected to be absent from international
    databases. Please confirm the exact publication number and title via
    NKIS (nkis.re.kr) or KISTEP's publications page.
```

If an item still cannot be confirmed after re-investigation, it is finalized as `REJECT` and recorded.

---

## As a gate in an agent pipeline

This is where the skill came from. Place it as `research → fact-verify → writing` and any research pipeline gains a verification gate. For the gate to mean anything, **the verifier must be a different agent from the researcher and the writer** — a structure where you clear your own evidence is not a gate.

```markdown
---
name: fact-verifier
description: Independent verifier for research output. Invoked after research completes, before writing begins.
tools: [WebFetch, WebSearch, Read, Write]
---
Follow the fact-verify three-step protocol, verify the research output,
and return a verification_report. REJECT items may not be used in writing.
```

When another agent needs to consume the result programmatically, ask for **YAML** instead of Markdown (`verification_report:` — totals, `by_tier`, `rejected_items` with reason and action, `review_needed`, `verified_items`). Wire the writing agent to read `rejected_items` and exclude that evidence, and the gate enforces itself. Details in [SKILL.md](SKILL.md).

---

## Limitations

Stated plainly.

- **Web access is required.** URL existence, DOI resolution, and Korean registry lookups use WebFetch/WebSearch. Offline, only `quick` depth is available.
- **Precise Korean API verification requires a data.go.kr key.** Without one, the skill verifies what public search reaches and holds the rest at ⚠️.
- **Paywalled full texts** (DBpia and similar) are held at ⚠️ when they cannot be checked — never declared wrong.
- **This is a source-discipline tool, not a truth oracle.** It checks that a source exists and matches the claim; it does not certify the scholarly validity of the claim itself. Final responsibility stays with a human.
- **The verifier runs on a model from the same family** as whatever produced the material. Gates reduce errors; they do not eliminate them.
- The only things sent outside during verification are **the URLs, identifiers, and search terms (title, author) being checked**. The document itself is never sent to an external service.

## Customizing

The default tier lists are written for **science and technology policy (STI)**. Add your own field's agencies, journals, and trade press to [references/tier-rules.md](references/tier-rules.md) — for public health, for example, add the disease control agency, the drug regulator and WHO to Tier 1; your field's national institutes and flagship journals to Tier 2; its trade press to Tier 3. The lists are examples, not a closed set: the classification principles (official standing, peer review, independence) take precedence over the list.

## Series

Sister repositories built on the same design philosophy — verification as the default, and unverified things marked unverified.

**Agent-team kits** — [policy-research-kit](https://github.com/parkjui92/policy-research-kit) (policy research reports) · [rnd-proposal-kit](https://github.com/parkjui92/rnd-proposal-kit) (Korean government R&D proposals) · [socsci-paper-kit](https://github.com/parkjui92/socsci-paper-kit) (social science papers)

**Standalone skills** — **fact-verify** (this repository, source verification) · [paper-proofread](https://github.com/parkjui92/paper-proofread) (Korean academic proofreading) · [form-tailor](https://github.com/parkjui92/form-tailor) (institutional document formats) · [report-to-brief](https://github.com/parkjui92/report-to-brief) (report compression)

## License

[MIT](LICENSE)
