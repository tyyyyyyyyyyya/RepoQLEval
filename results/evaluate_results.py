#Compare detection results against a ground-truth JSON file.


from __future__ import annotations

import argparse
import csv
import json
import posixpath
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


PathRecord = Tuple[str, str]


def load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Invalid JSON in {path}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, dict):
        raise SystemExit(f"Top-level JSON value must be an object: {path}")
    return data


def extract_path(value: str) -> str:

    text = value.strip().strip('"').strip("'")
    if "|" in text:
        text = text.rsplit("|", 1)[-1].strip()
    return text.strip().strip('"').strip("'")


def normalize_path(file_path: str, case_sensitive: bool = False) -> str:
    path = extract_path(file_path)
    path = path.replace("\\", "/")
    path = re.sub(r"/+", "/", path)

    path = re.sub(r"^file:/+", "/", path, flags=re.IGNORECASE)

    while path.startswith("./"):
        path = path[2:]

    path = posixpath.normpath(path)
    if path == ".":
        path = ""

    return path if case_sensitive else path.casefold()


def _validate_string_list(
    value: Any,
    *,
    project_id: str,
    source_name: str,
    key_name: str | None = None,
) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        location = f", key '{key_name}'" if key_name is not None else ""
        raise ValueError(
            f"{source_name}: project '{project_id}'{location} must contain "
            f"a list, not {type(value).__name__}."
        )

    output: List[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            location = f", key '{key_name}'" if key_name is not None else ""
            raise ValueError(
                f"{source_name}: project '{project_id}'{location}, item "
                f"{index} must be a string, not {type(item).__name__}."
            )
        output.append(item)
    return output


def collect_project_paths(
    project_value: Any,
    *,
    project_id: str,
    source_name: str,
    case_sensitive: bool,
) -> List[PathRecord]:
    raw_values: List[str] = []

    if project_value is None:
        pass
    elif isinstance(project_value, list):
        raw_values.extend(
            _validate_string_list(
                project_value,
                project_id=project_id,
                source_name=source_name,
            )
        )
    elif isinstance(project_value, dict):
        for key_name, files in project_value.items():
            raw_values.extend(
                _validate_string_list(
                    files,
                    project_id=project_id,
                    source_name=source_name,
                    key_name=str(key_name),
                )
            )
    else:
        raise ValueError(
            f"{source_name}: project '{project_id}' must map to a list or "
            f"object, not {type(project_value).__name__}."
        )


    records: Dict[str, str] = {}
    for raw_value in raw_values:
        original = extract_path(raw_value)
        normalized = normalize_path(original, case_sensitive=case_sensitive)
        if normalized:
            records.setdefault(normalized, original)

    return sorted(records.items(), key=lambda item: item[0])


def split_components(path: str) -> Tuple[str, ...]:
    return tuple(part for part in path.split("/") if part not in {"", "."})


def paths_match(predicted: str, actual: str, match_mode: str) -> bool:
    if match_mode == "exact":
        return predicted == actual

    predicted_parts = split_components(predicted)
    actual_parts = split_components(actual)
    if not predicted_parts or not actual_parts:
        return False

    if len(predicted_parts) >= len(actual_parts):
        if predicted_parts[-len(actual_parts) :] == actual_parts:
            return True
    if len(actual_parts) >= len(predicted_parts):
        if actual_parts[-len(predicted_parts) :] == predicted_parts:
            return True
    return False


def maximum_path_matching(
    predicted_records: Sequence[PathRecord],
    actual_records: Sequence[PathRecord],
    match_mode: str,
) -> List[Tuple[int, int]]:
    candidates: List[List[int]] = []
    for predicted, _ in predicted_records:
        matched_indices = [
            index
            for index, (actual, _) in enumerate(actual_records)
            if paths_match(predicted, actual, match_mode)
        ]
        matched_indices.sort(
            key=lambda index: len(split_components(actual_records[index][0])),
            reverse=True,
        )
        candidates.append(matched_indices)

    actual_to_predicted: Dict[int, int] = {}

    def augment(predicted_index: int, visited_actual: set[int]) -> bool:
        for actual_index in candidates[predicted_index]:
            if actual_index in visited_actual:
                continue
            visited_actual.add(actual_index)
            current_predicted = actual_to_predicted.get(actual_index)
            if current_predicted is None or augment(current_predicted, visited_actual):
                actual_to_predicted[actual_index] = predicted_index
                return True
        return False

    prediction_order = sorted(
        range(len(predicted_records)),
        key=lambda index: (len(candidates[index]), -len(split_components(predicted_records[index][0]))),
    )
    for predicted_index in prediction_order:
        augment(predicted_index, set())

    return sorted(
        ((predicted_index, actual_index) for actual_index, predicted_index in actual_to_predicted.items()),
        key=lambda pair: pair[0],
    )


def safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def calculate_metrics(tp: int, predicted: int, actual: int) -> Tuple[float, float, float]:
    precision = safe_ratio(tp, predicted)
    recall = safe_ratio(tp, actual)
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )
    return precision, recall, f1


def join_text(values: Iterable[str]) -> str:
    return "; ".join(sorted(values))


def compare(
    ground_truth: Mapping[str, Any],
    results: Mapping[str, Any],
    *,
    case_sensitive: bool,
    match_mode: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, float], List[str]]:
    rows: List[Dict[str, Any]] = []
    missing_ground_truth: List[str] = []

    total_tp = 0
    total_predicted = 0
    total_actual = 0

    for project_id, result_value in results.items():
        predicted_records = collect_project_paths(
            result_value,
            project_id=project_id,
            source_name="result file",
            case_sensitive=case_sensitive,
        )

        if project_id not in ground_truth:
            missing_ground_truth.append(project_id)
            actual_records: List[PathRecord] = []
        else:
            actual_records = collect_project_paths(
                ground_truth[project_id],
                project_id=project_id,
                source_name="ground-truth file",
                case_sensitive=case_sensitive,
            )

        matched_indices = maximum_path_matching(
            predicted_records, actual_records, match_mode
        )
        matched_predicted = {predicted_index for predicted_index, _ in matched_indices}
        matched_actual = {actual_index for _, actual_index in matched_indices}

        matched_pairs = [
            f"{predicted_records[predicted_index][1]} => "
            f"{actual_records[actual_index][1]}"
            for predicted_index, actual_index in matched_indices
        ]
        false_positive_files = [
            original
            for index, (_, original) in enumerate(predicted_records)
            if index not in matched_predicted
        ]
        missed_files = [
            original
            for index, (_, original) in enumerate(actual_records)
            if index not in matched_actual
        ]

        tp = len(matched_indices)
        predicted_count = len(predicted_records)
        actual_count = len(actual_records)
        precision, recall, f1 = calculate_metrics(tp, predicted_count, actual_count)

        total_tp += tp
        total_predicted += predicted_count
        total_actual += actual_count

        rows.append(
            {
                "project": project_id,
                "correct_files": tp,
                "detected_files": predicted_count,
                "actual_vulnerable_files": actual_count,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "matched_pairs": join_text(matched_pairs),
                "false_positive_files": join_text(false_positive_files),
                "missed_files": join_text(missed_files),
                "ground_truth_found": project_id in ground_truth,
            }
        )

    project_count = len(rows)
    macro_precision = safe_ratio(
        sum(row["precision"] for row in rows), project_count
    )
    macro_recall = safe_ratio(sum(row["recall"] for row in rows), project_count)
    macro_f1 = safe_ratio(sum(row["f1"] for row in rows), project_count)
    micro_precision, micro_recall, micro_f1 = calculate_metrics(
        total_tp, total_predicted, total_actual
    )

    summary = {
        "project_count": float(project_count),
        "total_correct_files": float(total_tp),
        "total_detected_files": float(total_predicted),
        "total_actual_vulnerable_files": float(total_actual),
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "micro_precision": micro_precision,
        "micro_recall": micro_recall,
        "micro_f1": micro_f1,
    }
    return rows, summary, missing_ground_truth


def print_report(rows: Sequence[Mapping[str, Any]], summary: Mapping[str, float]) -> None:
    header = (
        f"{'Project':<18} {'Correct':>8} {'Detected':>9} {'Actual':>7} "
        f"{'Precision':>10} {'Recall':>10} {'F1':>10}"
    )
    print(header)
    print("-" * len(header))

    for row in rows:
        print(
            f"{row['project']:<18} "
            f"{row['correct_files']:>8d} "
            f"{row['detected_files']:>9d} "
            f"{row['actual_vulnerable_files']:>7d} "
            f"{row['precision']:>10.4f} "
            f"{row['recall']:>10.4f} "
            f"{row['f1']:>10.4f}"
        )

    print("\nMacro averages (all projects in result file, including empty lists)")
    print(f"Projects:          {int(summary['project_count'])}")
    print(f"Average precision: {summary['macro_precision']:.4f}")
    print(f"Average recall:    {summary['macro_recall']:.4f}")
    print(f"Average F1:        {summary['macro_f1']:.4f}")

    print("\nMicro totals (additional reference)")
    print(f"Correct files:     {int(summary['total_correct_files'])}")
    print(f"Detected files:    {int(summary['total_detected_files'])}")
    print(f"Actual files:      {int(summary['total_actual_vulnerable_files'])}")
    print(f"Micro precision:   {summary['micro_precision']:.4f}")
    print(f"Micro recall:      {summary['micro_recall']:.4f}")
    print(f"Micro F1:          {summary['micro_f1']:.4f}")


def write_csv(rows: Sequence[Mapping[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "project",
        "correct_files",
        "detected_files",
        "actual_vulnerable_files",
        "precision",
        "recall",
        "f1",
        "matched_pairs",
        "false_positive_files",
        "missed_files",
        "ground_truth_found",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            output_row = dict(row)
            output_row["precision"] = f"{row['precision']:.6f}"
            output_row["recall"] = f"{row['recall']:.6f}"
            output_row["f1"] = f"{row['f1']:.6f}"
            writer.writerow(output_row)


def write_summary_json(summary: Mapping[str, float], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    integer_keys = {
        "project_count",
        "total_correct_files",
        "total_detected_files",
        "total_actual_vulnerable_files",
    }
    cleaned = {
        key: int(value) if key in integer_keys else round(value, 6)
        for key, value in summary.items()
    }
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(cleaned, file, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare a result JSON file with ground truth and calculate "
            "per-project precision, recall and F1."
        )
    )
    parser.add_argument("ground_truth", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument(
        "--csv", type=Path, default=Path("comparison_details.csv")
    )
    parser.add_argument(
        "--summary-json", type=Path, default=Path("comparison_summary.json")
    )
    parser.add_argument(
        "--match-mode",
        choices=("suffix", "exact"),
        default="suffix",
        help="suffix: component-wise path suffix match; exact: full path match",
    )
    parser.add_argument("--case-sensitive", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when a result project is absent from ground truth.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ground_truth = load_json(args.ground_truth)
    results = load_json(args.results)

    try:
        rows, summary, missing_ground_truth = compare(
            ground_truth,
            results,
            case_sensitive=args.case_sensitive,
            match_mode=args.match_mode,
        )
    except ValueError as exc:
        print(f"Data format error: {exc}", file=sys.stderr)
        return 2

    if missing_ground_truth:
        message = (
            "The following result projects were not found in ground truth: "
            + ", ".join(missing_ground_truth)
        )
        if args.strict:
            print(message, file=sys.stderr)
            return 3
        print(f"Warning: {message}", file=sys.stderr)
        print(
            "Warning: these projects are evaluated with zero actual files.",
            file=sys.stderr,
        )

    print_report(rows, summary)
    write_csv(rows, args.csv)
    write_summary_json(summary, args.summary_json)
    print(f"\nDetailed CSV written to: {args.csv}")
    print(f"Summary JSON written to: {args.summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())