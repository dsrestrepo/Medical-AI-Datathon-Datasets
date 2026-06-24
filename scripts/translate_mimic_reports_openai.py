#!/usr/bin/env python3
"""Translate one MIMIC-CXR split CSV report column to Spanish with OpenAI."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Event, Lock


DEFAULT_MODEL = "gpt-5-mini"
API_URL = "https://api.openai.com/v1/responses"
SYSTEM_PROMPT = (
    "You are a professional medical translator specializing in chest radiology. "
    "Translate English radiology reports into Spanish faithfully."
)
STOP_REQUESTED = Event()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read one MIMIC-CXR CSV, translate the `report` column to Spanish, "
            "and write a new CSV with `report_spanish`."
        )
    )
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--api-key-env", default="OPENAI_KEY")
    parser.add_argument("--model", default=os.environ.get("OPENAI_TRANSLATION_MODEL", DEFAULT_MODEL))
    parser.add_argument("--report-column", default="report")
    parser.add_argument("--output-column", default="report_spanish")
    parser.add_argument("--cache-file", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-retries", type=int, default=6)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=25,
        help="Rewrite the output CSV after this many completed translations.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_env_file(path: Path | None) -> None:
    if path is None or not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def report_hash(report: str) -> str:
    normalized = " ".join(report.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 4) + 1)


def load_cache(path: Path) -> dict[str, str]:
    translations: dict[str, str] = {}
    if not path.is_file():
        return translations
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            translations[row["report_hash"]] = row["report_spanish"]
    return translations


def append_cache(path: Path, digest: str, translation: str, lock: Lock) -> None:
    row = {"report_hash": digest, "report_spanish": translation}
    with lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def request_stop(signum: int, _frame: object) -> None:
    print(f"Received signal {signum}; checkpointing and stopping soon.", flush=True)
    STOP_REQUESTED.set()


def translation_prompt(report: str) -> str:
    return f"""Translate this chest radiology report from English to Spanish.

Rules:
- Preserve all clinical meaning exactly.
- Do not add, remove, infer, or explain findings.
- Preserve uncertainty, including possible, likely, concerning for, and cannot exclude.
- Preserve measurements, dates, device names, anatomy laterality, and section structure.
- Use standard Spanish radiology terminology.
- Output only the Spanish translation.

REPORT:
{report}
"""


def call_openai(
    api_key: str,
    model: str,
    report: str,
    max_retries: int,
) -> str:
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": translation_prompt(report)},
        ],
        "store": False,
    }
    if model.startswith("gpt-5"):
        payload["reasoning"] = {"effort": "minimal"}

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(max_retries + 1):
        request = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
            translation = extract_response_text(body)
            if not translation:
                raise RuntimeError("OpenAI returned an empty translation")
            return translation
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            if error.code not in {408, 409, 429, 500, 502, 503, 504} or attempt == max_retries:
                raise RuntimeError(f"OpenAI HTTP {error.code}: {body[:500]}") from error
        except (urllib.error.URLError, TimeoutError, RuntimeError) as error:
            if attempt == max_retries:
                raise

        sleep_seconds = min(60, 2**attempt)
        time.sleep(sleep_seconds)

    raise RuntimeError("unreachable retry state")


def extract_response_text(body: dict) -> str:
    output_text = body.get("output_text")
    if isinstance(output_text, str):
        return output_text.strip()

    chunks: list[str] = []
    for item in body.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                chunks.append(content["text"])

    return "".join(chunks).strip()


def read_rows(path: Path, max_rows: int | None) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path} has no header")
        rows = []
        for index, row in enumerate(reader):
            if max_rows is not None and index >= max_rows:
                break
            rows.append(row)
    return list(reader.fieldnames), rows


def write_output(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
    report_column: str,
    output_column: str,
    translations: dict[str, str],
) -> None:
    output_fields = list(fieldnames)
    if output_column not in output_fields:
        insert_at = output_fields.index(report_column) + 1
        output_fields.insert(insert_at, output_column)

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields)
        writer.writeheader()
        for row in rows:
            report = row.get(report_column, "").strip()
            output_row = {field: row.get(field, "") for field in output_fields}
            output_row[output_column] = translations.get(report_hash(report), "") if report else ""
            writer.writerow(output_row)
    temporary_path.replace(path)


def checkpoint_output(
    output_csv: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
    report_column: str,
    output_column: str,
    translations: dict[str, str],
    completed: int,
    total_missing: int,
) -> None:
    write_output(
        path=output_csv,
        fieldnames=fieldnames,
        rows=rows,
        report_column=report_column,
        output_column=output_column,
        translations=translations,
    )
    print(
        f"Checkpointed {output_csv} after {completed:,}/{total_missing:,} new translations",
        flush=True,
    )


def main() -> None:
    args = parse_args()
    input_csv = args.input_csv.expanduser().resolve()
    output_csv = args.output_csv.expanduser().resolve()
    env_file = args.env_file.expanduser().resolve() if args.env_file else None
    cache_file = (
        args.cache_file.expanduser().resolve()
        if args.cache_file
        else output_csv.with_suffix(output_csv.suffix + ".translation_cache.jsonl")
    )

    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    if args.checkpoint_every < 1:
        raise ValueError("--checkpoint-every must be at least 1")

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    load_env_file(env_file)
    api_key = os.environ.get(args.api_key_env)
    if not api_key and not args.dry_run:
        raise RuntimeError(
            f"Missing API key. Put {args.api_key_env}=... in {env_file or '.env'} "
            f"or export {args.api_key_env}."
        )

    fieldnames, rows = read_rows(input_csv, args.max_rows)
    if args.report_column not in fieldnames:
        raise ValueError(f"{input_csv} must contain column {args.report_column}")

    unique_reports: dict[str, str] = {}
    for row in rows:
        report = row.get(args.report_column, "").strip()
        if report:
            unique_reports.setdefault(report_hash(report), report)

    cached = load_cache(cache_file)
    missing = {
        digest: report
        for digest, report in unique_reports.items()
        if digest not in cached
    }
    input_tokens = sum(estimate_tokens(report) for report in missing.values())
    output_tokens = input_tokens

    print(f"Input rows: {len(rows):,}", flush=True)
    print(f"Unique non-empty reports: {len(unique_reports):,}", flush=True)
    print(f"Cached translations: {len(cached):,}", flush=True)
    print(f"Reports still to translate: {len(missing):,}", flush=True)
    print(
        f"Very rough token estimate for missing reports: "
        f"{input_tokens:,} input + {output_tokens:,} output",
        flush=True,
    )

    if args.dry_run:
        print("Dry run only. No API calls made.", flush=True)
        return

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_lock = Lock()
    translations = dict(cached)

    if missing:
        completed = 0
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    call_openai,
                    api_key,
                    args.model,
                    report,
                    args.max_retries,
                ): digest
                for digest, report in missing.items()
            }
            for future in as_completed(futures):
                if STOP_REQUESTED.is_set():
                    for pending in futures:
                        pending.cancel()
                    break

                digest = futures[future]
                translation = future.result()
                translations[digest] = translation
                append_cache(cache_file, digest, translation, cache_lock)
                completed += 1
                if completed % 100 == 0 or completed == len(missing):
                    print(
                        f"Translated {completed:,}/{len(missing):,} missing reports",
                        flush=True,
                    )
                if completed % args.checkpoint_every == 0:
                    checkpoint_output(
                        output_csv=output_csv,
                        fieldnames=fieldnames,
                        rows=rows,
                        report_column=args.report_column,
                        output_column=args.output_column,
                        translations=translations,
                        completed=completed,
                        total_missing=len(missing),
                    )

    checkpoint_output(
        output_csv=output_csv,
        fieldnames=fieldnames,
        rows=rows,
        report_column=args.report_column,
        output_column=args.output_column,
        translations=translations,
        completed=len(translations) - len(cached),
        total_missing=len(missing),
    )
    if STOP_REQUESTED.is_set():
        print("Stopped early after writing checkpoint. Re-run the same job to resume.", flush=True)
        sys.exit(143)
    print(f"Wrote complete output: {output_csv}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
