#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch classifier for CodeQL compilation errors extracted from LLM repair logs.

Input:  a folder containing .txt files, each of which may contain blocks like
        ===== Error 1 =====
        ERROR: ... (path/to/test.ql:line,col-range)
        ...
        followed by prompt/code/context text.

Output: CSV/JSON/Markdown reports under the output directory.

Default behavior: only lines containing "ERROR:" are treated as compilation
errors. WARNING lines, source-code context, and non-CodeQL diagnostic text are
ignored by default.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


# -----------------------------
# Category definitions
# -----------------------------
# These categories are not an official CodeQL taxonomy. They are a practical
# grouping derived from common QL validity constraints: parsing, module/name
# resolution, type compatibility, binding/range restriction, declaration shape,
# and query/result requirements.

CATEGORY_ORDER = [
    "Syntax / parsing error",
    "Import / module resolution error",
    "Name / API resolution error",
    "Type compatibility error",
    "Binding / range-restriction error",
    "Class / predicate structure error",
    "Declaration / query-shape error",
    "Metadata / result-shape error",
    "Other compile error",
]

# Priority matters: syntax should be identified before broad name/API matching;
# binding should be identified before broad "could not resolve variable" in some cases.
CATEGORY_PATTERNS: List[Tuple[str, List[re.Pattern]]] = [
    (
        "Syntax / parsing error",
        [
            re.compile(r"\bunexpected input\b", re.I),
            re.compile(r"\bextraneous input\b", re.I),
            re.compile(r"\bmissing one of\b", re.I),
            re.compile(r"\bCould not parse\b", re.I),
            re.compile(r"\bmismatched input\b", re.I),
            re.compile(r"\bno viable alternative\b", re.I),
            re.compile(r"\bno viable parse\b", re.I),
            re.compile(r"\btoken recognition error\b", re.I),
            re.compile(r"\bExpected a term but found an expression instead\b", re.I),
            re.compile(r"\bExpected an expression but found a term instead\b", re.I),
            re.compile(r"\bThe right hand side of an ['\"]?in['\"]? term must be a range\b", re.I),
            re.compile(r"\bunterminated\b", re.I),
            re.compile(r"\bunclosed\b", re.I),
        ],
    ),
    (
        "Import / module resolution error",
        [
            re.compile(r"\bCould not resolve module\b", re.I),
            re.compile(r"\bModule\s+.+\s+is ambiguous\b", re.I),
            re.compile(r"\bmodule\s+.+\s+conflicts with existing declarations\b", re.I),
            re.compile(r"\bbrought into scope by this import\b", re.I),
            re.compile(r"\bCould not find (?:module|library|pack|qlpack)\b", re.I),
        ],
    ),
    (
        "Type compatibility error",
        [
            re.compile(r"\bis incompatible with\b", re.I),
            re.compile(r"\bincompatible type\b", re.I),
            re.compile(r"\bnot compatible with\b", re.I),
            re.compile(r"\bnot a subtype\b", re.I),
            re.compile(r"\bcannot be cast\b", re.I),
            re.compile(r"\bSignature incompatible with signature\b", re.I),
            re.compile(r"\btest is always false\b", re.I),
        ],
    ),
    (
        "Binding / range-restriction error",
        [
            re.compile(r"\bis not bound to a value\b", re.I),
            re.compile(r"\bunbound variable\b", re.I),
            re.compile(r"\bnot range[- ]restricted\b", re.I),
            re.compile(r"\binfinite result\b", re.I),
        ],
    ),
    (
        "Class / predicate structure error",
        [
            re.compile(r"\bmust implement toString\(\)", re.I),
            re.compile(r"\bClass must extend or implement at least one type\b", re.I),
            re.compile(r"\bThis predicate does not override another predicate\b", re.I),
            re.compile(r"\bAnnotation override can only be applied\b", re.I),
            re.compile(r"\bThis predicate requires a body\b", re.I),
            re.compile(r"\bPredicate aliases may not declare a return type\b", re.I),
            re.compile(r"\bExpected a predicate with result but found\b", re.I),
            re.compile(r"\bExpected a predicate without result but found\b", re.I),
            re.compile(r"\bmust implement abstract method\b", re.I),
            re.compile(r"\bCannot override the final method\b", re.I),
            re.compile(r"\bdoes not bind ['\"]?result['\"]? to a value\b", re.I),
            re.compile(r"\bdoes not bind ['\"]?this['\"]? to a value\b", re.I),
            re.compile(r"['\"]?this['\"]? cannot be used in this context", re.I),
            re.compile(r"\boverride\b.*\binvalid\b", re.I),
            re.compile(r"\bcharacteristic predicate\b", re.I),
        ],
    ),
    (
        "Declaration / query-shape error",
        [
            re.compile(r"\bconflicts with existing declarations\b", re.I),
            re.compile(r"\bmultiple select clauses\b", re.I),
            re.compile(r"\bSelect clauses can only appear at the top level\b", re.I),
            re.compile(r"\bmultiple query predicates\b", re.I),
            re.compile(r"\bdoes not have any queries in scope\b", re.I),
            re.compile(r"\bDeclaration of select clause\b", re.I),
            re.compile(r"\bduplicate declaration\b", re.I),
            re.compile(r"\balready defined\b", re.I),
            re.compile(r"\bVariable .+ is already declared\b", re.I),
            re.compile(r"\bOnly predicates and predicate aliases can be marked as ['\"]?query", re.I),
            re.compile(r"\bcannot be overloaded with signature\b", re.I),
        ],
    ),
    (
        "Metadata / result-shape error",
        [
            re.compile(r"\bmetadata\b", re.I),
            re.compile(r"\bunknown annotation\b", re.I),
            re.compile(r"@kind", re.I),
            re.compile(r"\bpath-problem\b", re.I),
            re.compile(r"\bresult(?:s)?\s+(?:set|shape|format|tuple)\b", re.I),
            re.compile(r"\bselect\b.*\b(?:must|requires|required|expected)\b", re.I),
            re.compile(r"\bSARIF\b", re.I),
        ],
    ),
    (
        "Name / API resolution error",
        [
            re.compile(r"\bCould not resolve type\b", re.I),
            re.compile(r"\bCould not resolve variable\b", re.I),
            re.compile(r"\bCould not resolve predicate\b", re.I),
            re.compile(r"\bCould not resolve field\b", re.I),
            re.compile(r"\bcannot be resolved for type\b", re.I),
            re.compile(r"\bAmbiguous predicate reference\b", re.I),
            re.compile(r"\bNo higher-order predicate with name\b", re.I),
            re.compile(r"\bCannot instantiate non-parameterised module\b", re.I),
            re.compile(r"\bCannot resolve\b", re.I),
        ],
    ),
]

TOPIC_PATTERNS: List[Tuple[str, List[re.Pattern]]] = [
    (
        "DataFlow / TaintTracking / path query",
        [
            re.compile(r"\bDataFlow\b", re.I),
            re.compile(r"\bTaintTracking\b", re.I),
            re.compile(r"\bPathNode\b", re.I),
            re.compile(r"\bPathGraph\b", re.I),
            re.compile(r"\bhasFlow(?:Path)?\b", re.I),
            re.compile(r"\bisSource\b|\bisSink\b|\bisSanitizer\b", re.I),
        ],
    ),
    (
        "Import / library compatibility",
        [
            re.compile(r"\bimport\b", re.I),
            re.compile(r"\bmodule\b", re.I),
            re.compile(r"\bExternalAPIs\b", re.I),
            re.compile(r"\bsemmle\.", re.I),
            re.compile(r"\bcodeql\.", re.I),
        ],
    ),
    (
        "Class / inheritance / override",
        [
            re.compile(r"\bextends\b", re.I),
            re.compile(r"\boverride\b", re.I),
            re.compile(r"\bimplement\b", re.I),
            re.compile(r"\btoString\(\)", re.I),
        ],
    ),
    (
        "Query select / result",
        [
            re.compile(r"\bselect\b", re.I),
            re.compile(r"\bqueries in scope\b", re.I),
            re.compile(r"@kind", re.I),
        ],
    ),
]

# Match CodeQL diagnostic lines only. This avoids counting source-code strings
# such as cout << "ERROR: --flag is required" as compilation errors.
ERROR_LINE_RE = re.compile(r"^\s*['\"]?\s*(ERROR|WARNING):\s*(.*)")
BLOCK_RE = re.compile(r"^\s*=+\s*Error\s+(\d+)\s*=+\s*$", re.I)
# Example: (D:\yml\python-v1\cwe-20-1\test.ql:54,7-36)
QL_LOC_RE = re.compile(r"\(([^()]*?\.ql):(\d+)(?:,([^()]+?))?\)")


@dataclass
class ErrorRecord:
    source_file: str
    source_line: int
    block_id: Optional[int]
    severity: str
    raw_message: str
    clean_message: str
    message_template: str
    category: str
    topic: str
    ql_file: str
    ql_line: str
    ql_span: str


def iter_txt_files(input_dir: Path, recursive: bool) -> Iterable[Path]:
    pattern = "**/*.txt" if recursive else "*.txt"
    for path in sorted(input_dir.glob(pattern)):
        if path.is_file():
            yield path


def extract_ql_location(message: str) -> Tuple[str, str, str]:
    matches = list(QL_LOC_RE.finditer(message))
    if not matches:
        return "", "", ""
    m = matches[-1]
    return m.group(1), m.group(2), m.group(3) or ""


def clean_message(message: str) -> str:
    """Remove quoted wrappers and the final .ql source location."""
    msg = message.strip()
    # Logs sometimes contain a trailing quote because the original error text was
    # embedded in a JSON/string literal. Do not strip a leading quote blindly,
    # because diagnostics such as `'this' cannot be used...` are legitimate.
    if len(msg) >= 2 and msg[0] == msg[-1] and msg[0] in {"'", '\"'}:
        msg = msg[1:-1].strip()
    elif msg.endswith(("'", '\"')):
        msg = msg[:-1].strip()
    msg = QL_LOC_RE.sub("", msg).strip()
    if len(msg) >= 2 and msg[0] == msg[-1] and msg[0] in {"'", '\"'}:
        msg = msg[1:-1].strip()
    elif msg.endswith(("'", '\"')):
        msg = msg[:-1].strip()
    # Remove locations inside declarations such as "from test.ql:6".
    msg = re.sub(r"\bfrom\s+[^\s:()]+\.ql:\d+", "from <ql-file>:<line>", msg)
    # Collapse whitespace and repeated spaces caused by cleaning.
    msg = re.sub(r"\s+", " ", msg)
    return msg


def message_template(clean: str) -> str:
    """Create a coarser template for distribution statistics."""
    msg = clean
    replacements = [
        (r"Could not resolve module\s+[^\s]+", "Could not resolve module <module>"),
        (r"Could not resolve type\s+[^\s]*", "Could not resolve type <type>"),
        (r"Could not resolve variable\s+[^\s]+", "Could not resolve variable <variable>"),
        (r"Could not resolve predicate\s+[^\s]+", "Could not resolve predicate <predicate>"),
        (r"[A-Za-z_][\w:.$<>]*(?:\([^)]*\))? cannot be resolved for type [A-Za-z_][\w:.$<>]*(?:::[A-Za-z_][\w:.$<>]*)*", "<member> cannot be resolved for type <type>"),
        (r"Module\s+[^\s]+\s+is ambiguous between:.*", "Module <module> is ambiguous between multiple modules"),
        (r"The module\s+[^,]+, which was brought into scope by this import, conflicts with existing declarations:.*", "Imported module conflicts with existing declarations"),
        (r"Declaration of predicate\s+[^\s]+\s+conflicts with existing declarations:.*", "Declaration of predicate <predicate> conflicts with existing declarations"),
        (r"Declaration of select clause\s+[^\s]+\s+conflicts with existing declarations:.*", "Declaration of select clause conflicts with existing declarations"),
        (r"[^\s]+\s+must implement toString\(\)", "<class> must implement toString()"),
        (r"[^\s]+\s+is incompatible with\s+[^.]+", "<type> is incompatible with <type>"),
        (r"test is always false, as .* is incompatible with .*", "test is always false due to incompatible types"),
        (r"unexpected input\s+.+?\s+expecting one of:.*", "unexpected input <token> expecting one of <tokens>"),
        (r"extraneous input\s+.+?\s+expecting one of:.*", "extraneous input <token> expecting one of <tokens>"),
        (r"missing one of:.*", "missing one of <tokens>"),
        (r"token recognition error at:.*", "token recognition error at <token>"),
        (r"no viable parse for input .*", "no viable parse for input <fragment>"),
        (r"unknown annotation\s+\S+", "unknown annotation <annotation>"),
        (r"'[^']+' is not bound to a value\.", "<variable> is not bound to a value"),
        (r"\"[^\"]+\" is not bound to a value\.", "<variable> is not bound to a value"),
        (r"Only predicates and predicate aliases can be marked as ['\"]?query", "Only predicates and predicate aliases can be marked as query"),
        (r"Predicate predicate [^(]+\([^)]*\) cannot be overloaded with signature .*", "Predicate cannot be overloaded with an incompatible signature"),
        (r"Signature incompatible with signature of overridden method:.*", "Signature incompatible with overridden method"),
    ]
    for pat, repl in replacements:
        msg = re.sub(pat, repl, msg, flags=re.I)
    msg = re.sub(r"\s+", " ", msg).strip()
    return msg


def classify_category(clean: str) -> str:
    for category, patterns in CATEGORY_PATTERNS:
        if any(p.search(clean) for p in patterns):
            return category
    return "Other compile error"


def classify_topic(clean: str) -> str:
    matched = [topic for topic, pats in TOPIC_PATTERNS if any(p.search(clean) for p in pats)]
    return "; ".join(matched) if matched else "General"


def parse_file(path: Path, include_warnings: bool = False) -> List[ErrorRecord]:
    records: List[ErrorRecord] = []
    block_id: Optional[int] = None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(f"Failed to read {path}: {exc}") from exc

    for line_no, line in enumerate(text.splitlines(), start=1):
        block_match = BLOCK_RE.match(line)
        if block_match:
            block_id = int(block_match.group(1))
            continue

        m = ERROR_LINE_RE.search(line)
        if not m:
            continue
        severity, rest = m.group(1), m.group(2)
        if severity == "WARNING" and not include_warnings:
            continue

        ql_file, ql_line, ql_span = extract_ql_location(rest)
        clean = clean_message(rest)
        templ = message_template(clean)
        category = classify_category(clean)
        topic = classify_topic(clean)
        records.append(
            ErrorRecord(
                source_file=path.name,
                source_line=line_no,
                block_id=block_id,
                severity=severity,
                raw_message=rest.strip(),
                clean_message=clean,
                message_template=templ,
                category=category,
                topic=topic,
                ql_file=ql_file,
                ql_line=ql_line,
                ql_span=ql_span,
            )
        )
    return records


def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def pct(n: int, denom: int) -> str:
    return f"{(100.0 * n / denom):.2f}%" if denom else "0.00%"


def summarize(records: List[ErrorRecord], output_dir: Path, max_examples: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(records)

    # Detailed record table.
    record_dicts = [asdict(r) for r in records]
    if records:
        write_csv(output_dir / "error_records.csv", record_dicts, list(record_dicts[0].keys()))
    else:
        write_csv(output_dir / "error_records.csv", [], [f.name for f in ErrorRecord.__dataclass_fields__.values()])

    # Category distribution.
    category_counter = Counter(r.category for r in records)
    category_rows = []
    for category in CATEGORY_ORDER:
        n = category_counter.get(category, 0)
        category_rows.append({"category": category, "count": n, "percentage": pct(n, total)})
    write_csv(output_dir / "distribution_by_category.csv", category_rows, ["category", "count", "percentage"])

    # File/category matrix and per-file totals.
    file_counter = Counter(r.source_file for r in records)
    matrix_rows = []
    for source_file in sorted(file_counter):
        row = {"source_file": source_file, "total_errors": file_counter[source_file]}
        for category in CATEGORY_ORDER:
            row[category] = sum(1 for r in records if r.source_file == source_file and r.category == category)
        matrix_rows.append(row)
    write_csv(output_dir / "distribution_by_file.csv", matrix_rows, ["source_file", "total_errors"] + CATEGORY_ORDER)

    # Error-block distribution. One Error N block may contain multiple error lines/categories.
    block_map: Dict[Tuple[str, Optional[int]], List[ErrorRecord]] = defaultdict(list)
    for r in records:
        block_map[(r.source_file, r.block_id)].append(r)
    block_rows = []
    for (source_file, block_id), rs in sorted(block_map.items(), key=lambda x: (x[0][0], x[0][1] if x[0][1] is not None else -1)):
        cats = Counter(r.category for r in rs)
        primary = cats.most_common(1)[0][0] if cats else ""
        block_rows.append(
            {
                "source_file": source_file,
                "block_id": "" if block_id is None else block_id,
                "error_lines": len(rs),
                "primary_category": primary,
                "categories": "; ".join(f"{c}={n}" for c, n in cats.most_common()),
                "unique_templates": len(set(r.message_template for r in rs)),
            }
        )
    write_csv(output_dir / "distribution_by_error_block.csv", block_rows, ["source_file", "block_id", "error_lines", "primary_category", "categories", "unique_templates"])

    # Template / pattern distribution.
    template_counter = Counter((r.category, r.message_template) for r in records)
    template_rows = [
        {"category": cat, "message_template": tmpl, "count": n, "percentage": pct(n, total)}
        for (cat, tmpl), n in template_counter.most_common()
    ]
    write_csv(output_dir / "error_patterns.csv", template_rows, ["category", "message_template", "count", "percentage"])

    # Topic distribution.
    topic_counter = Counter()
    for r in records:
        for topic in r.topic.split("; "):
            topic_counter[topic] += 1
    topic_rows = [{"topic": t, "count": n, "percentage": pct(n, total)} for t, n in topic_counter.most_common()]
    write_csv(output_dir / "distribution_by_topic.csv", topic_rows, ["topic", "count", "percentage"])

    # Representative examples by category.
    examples_by_category: Dict[str, List[ErrorRecord]] = defaultdict(list)
    seen_examples = defaultdict(set)
    for r in records:
        if len(examples_by_category[r.category]) >= max_examples:
            continue
        if r.message_template in seen_examples[r.category]:
            continue
        examples_by_category[r.category].append(r)
        seen_examples[r.category].add(r.message_template)

    examples = []
    for category in CATEGORY_ORDER:
        examples.append(f"## {category}\n")
        if not examples_by_category.get(category):
            examples.append("No examples.\n")
            continue
        for r in examples_by_category[category]:
            loc = f"{r.ql_file}:{r.ql_line}" if r.ql_file and r.ql_line else f"{r.source_file}:line {r.source_line}"
            examples.append(f"- `{r.clean_message}`  ")
            examples.append(f"  - source: `{r.source_file}`, block: `{r.block_id}`, location: `{loc}`\n")
        examples.append("")
    (output_dir / "representative_examples.md").write_text("\n".join(examples), encoding="utf-8")

    # JSON summary for programmatic use.
    summary_json = {
        "total_errors": total,
        "total_files": len(file_counter),
        "category_distribution": category_rows,
        "top_patterns": template_rows[:50],
        "topic_distribution": topic_rows,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary_json, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown report.
    md = []
    md.append("# CodeQL Compilation Error Classification Report\n")
    md.append(f"- Total compilation error lines: **{total}**")
    md.append(f"- Files analyzed: **{len(file_counter)}**")
    md.append(f"- Error blocks: **{len(block_map)}**\n")

    md.append("## Category distribution\n")
    md.append("| Category | Count | Percentage |")
    md.append("|---|---:|---:|")
    for row in category_rows:
        md.append(f"| {row['category']} | {row['count']} | {row['percentage']} |")

    md.append("\n## Top error templates\n")
    md.append("| Rank | Category | Template | Count | Percentage |")
    md.append("|---:|---|---|---:|---:|")
    for rank, row in enumerate(template_rows[:30], start=1):
        safe_template = row["message_template"].replace("|", "\\|")
        md.append(f"| {rank} | {row['category']} | `{safe_template}` | {row['count']} | {row['percentage']} |")

    md.append("\n## Files with most errors\n")
    md.append("| Source file | Error lines |")
    md.append("|---|---:|")
    for source_file, n in file_counter.most_common(30):
        md.append(f"| `{source_file}` | {n} |")

    md.append("\n## Notes\n")
    md.append("- This script classifies compilation diagnostics by regex-based patterns. It is designed for batch statistics and error analysis, not for proving an official CodeQL taxonomy.")
    md.append("- Runtime/evaluation failures such as timeout or out-of-memory are intentionally outside the scope unless they appear as `ERROR:` lines in the input files.")
    md.append("- Warnings are ignored by default. Use `--include-warnings` if you want to keep them in `error_records.csv`.")

    (output_dir / "summary_report.md").write_text("\n".join(md), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify CodeQL compilation errors from .txt logs.")
    parser.add_argument("--input_dir", required=True, help="Folder containing .txt files.")
    parser.add_argument("--output_dir", default="codeql_compile_error_report", help="Output folder for reports.")
    parser.add_argument("--no_recursive", action="store_true", help="Only analyze .txt files directly under input_dir.")
    parser.add_argument("--include_warnings", action="store_true", help="Also include WARNING lines. Default: only ERROR lines.")
    parser.add_argument("--max_examples", type=int, default=5, help="Representative examples per category.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist or is not a directory: {input_dir}")

    records: List[ErrorRecord] = []
    txt_files = list(iter_txt_files(input_dir, recursive=not args.no_recursive))
    for path in txt_files:
        records.extend(parse_file(path, include_warnings=args.include_warnings))

    summarize(records, output_dir=output_dir, max_examples=args.max_examples)

    print(f"Analyzed txt files: {len(txt_files)}")
    print(f"Compilation error lines: {len(records)}")
    print(f"Reports written to: {output_dir}")


if __name__ == "__main__":
    main()
