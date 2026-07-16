# Pull-Request Patch Scan — 

The patch scan ([`main.py`](../main.py)) inspects **only the commit diff** of a
pull request — the lines added and removed. 

It runs **two checks** on every PR:
- **License check** — do the added lines introduce an incompatible license?
  (allowed = **permissive** — MIT, BSD, Apache-2.0, ISC, Zlib… — for a permissive
  repo, or the **copyleft** family — GPL/LGPL/AGPL — for a copyleft repo; the
  repo's own license defaults to **`BSD-3-Clause-Clear`** when none is detected.)
- **Copyright check** — do the removed lines delete an existing copyright holder?
  (detected by regex on the diff: every `+`/`-` line containing the word
  `Copyright` is collected, normalized to letters-only, and a holder is flagged
  when it appears on a removed line but no re-added line — except the built-in
  **Qualcomm Innovation Center → Qualcomm Technologies, Inc.** rename.)

**How licenses are detected:** both checks use [scancode](https://github.com/nexB/scancode-toolkit)
(run as `scancode --license`). The added/deleted diff lines are written to temp
files and scanned in a **single** batch invocation, and scancode returns an SPDX
license expression (e.g. `MIT`, `Apache-2.0`, `MIT OR GPL-2.0-only`) per file.
The repo's own license is detected the same way — scancode runs over its
`LICENSE`/`COPYING` file. Copyright statements are found by regex on the diff
(`Copyright` lines), not by scancode.

Both checks always run; the PR is **blocked if *either* one finds a blocking issue**. 

It does *not* look at unchanged legacy files.

---

## 1. Overall flow

```mermaid
%%{init: {'flowchart': {'rankSpacing': 70, 'nodeSpacing': 55}}}%%
flowchart TD
    A["PR opened / synchronized<br/>"] --> B["Checkout PR head<br/>+ fetch base as 'upstream'"]
    B --> C["git diff upstream/base &gt; pr.patch"]
    C --> D["action.yml (composite)<br/>setup Python 3.8<br/>pip install requirements.txt"]
    D --> E["python main.py<br/>&lt;patch_file&gt; &lt;repo_name&gt;"]

    E --> F["Patch(argv[1])<br/>parse diff into changes"]
    F --> G["get_license(repo_name) (default: BSD-3-Clause-Clear)"]
    G --> H{"license type?"}
    H -->|in PERMISSIVE_LICENSES| I1["allowed = PERMISSIVE_LICENSES"]
    H -->|in COPYLEFT_LICENSES| I2["allowed = COPYLEFT_LICENSES"]
    H -->|other| I3["allowed = [that license]"]

    I1 & I2 & I3 --> J["LicenseChecker(patch, repo, allowed).run()"]
    I1 & I2 & I3 --> K["CopyrightChecker(patch).run()"]

    J --> L["flagged_license_files<br/>{ file → [license issues] }"]
    K --> M["flagged_copyright_files<br/>{ file → [copyright issues] }"]

    L --> N{"per license issue:<br/>is_uncertain_license_issue()?"}
    N -->|uncertain only| O1["warning_files (non-blocking)"]
    N -->|otherwise| O2["flagged_files (blocking)"]
    M -->|"always blocking<br/>(never triaged)"| O2

    O1 & O2 --> P["beautify_output()"]
    P --> Q{"any flagged_files?"}
    Q -->|yes| R["print report<br/>exit len(flagged_files) (non-zero)"]
    Q -->|no| S["print report / no issues<br/>exit 0"]
```

---
