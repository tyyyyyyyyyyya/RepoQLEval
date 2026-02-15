# CWE-119-3 Single-Project Case Study
**Supplementary Material for Section 7.1**

---

## 1. Setup and Goal

To control confounders, we evaluate six models on one C/C++ repository in our benchmark (anonymized as **Repo-X**, tagged **CWE-119-3**) that contains **exactly one vulnerable file**.

* **Zero-shot setting**: No repository context is provided to the models.
* **Evaluation focus**: Only CodeQL-side behavior — syntax viability (compile/execute), file-level localization.
* **Environment**: CodeQL CLI pinned to **v2.11.0**. Outputs must be **code-only** with canonical imports.
* **Scoring**: File-level (TP/FP/FN), consistent with the main protocol.

---

## 2. Results Summary

| Model | Files Flagged | TP | FP | FN | Compiled | Executed (≤300s) | Primary Failure Mode |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **CLA-Haiku** | 4 | 1 | 3 | 0 | Yes | Yes | Unbound destination variable |
| **Grok3** | 1 | 0 | 1 | 1 | Yes | Yes | Array-index only, misses call family |
| **DS-Reason** | 0 | 0 | 0 | 1 | Yes | Yes | Incomplete dangerous-call list |
| **Qwen32B** | 0 | 0 | 0 | 1 | Yes | Yes | Overly restrictive literal guards |
| **L3-8B** | 0 | 0 | 0 | 1 | No | Yes | Syntax errors |
| **QwenCoder+** | 3 | 1 | 2 | 0 | Yes | Yes | Broad family match, no guards |

---

## 3. Model-by-Model Analysis

### CLA-Haiku
**Findings:** 4 files flagged (TP=1, FP=3).
**Issue:** Destination variable not bound to the call site; size-based heuristic does not reflect real buffer capacity.
**Quick fix:** Bind destination to `arg(0)` and require a minimal guard (explicit bound/length check).


### Grok3
**Findings:** 1 file flagged (FP=1).
**Issue:** Focuses on ArrayExpr with range upper-bounds, missing the call-based ground truth.
**Quick fix:** Widen to a dual-template (array-index & call-family).



### DS-Reason
**Findings:** No hits.  
**Issue:** Dangerous-call list under-covers the pattern (call is indirect/macro-expanded).  
**Quick fix:** Include `memcpy`/`memmove`/`strncpy` family; lightly guard destination.



### Qwen32B
**Findings:** No hits.  
**Issue:** Over-restrictive argument typing (e.g., requiring string literals).  
**Quick fix:** Drop literal-only guards; prefer presence/absence-of-checks predicate.

### L3-8B
**Findings:** No hits.  
**Issue:** Syntax errors and incorrect class/predicate definitions cause CodeQL compilation to fail.  
**Quick fix:** Bind arguments correctly and use proper invocation syntax.

### QwenCoder+
**Findings:** 3 files flagged (TP=1, FP=2).  
**Issue:** Broad function-family match without parameter guards.  
**Quick fix:** Add destination binding and a minimal no-check predicate.

---

## 4. Failure Clusters and Template Fixes

Across all six models, four recurring failure modes explain both this controlled case and broader C/C++ trends:

1. **Unbound arguments** — destination/source not tied to the call site.
2. **Over-strong typing guards** — e.g., literal-only constraints that filter realistic uses.
3. **Template mismatch** — array-only patterns that miss call-based overflows.
4. **Fragile size heuristics** — do not track real buffer capacity.

**Reusable playbook** (recommended for future queries):

* Freeze imports and enforce code-only outputs.
* Always bind arguments to call positions (`arg(0)`, `arg(1)`, …).
* Prefer lightweight evidence of missing bound/length checks over platform-dependent size arithmetic.



