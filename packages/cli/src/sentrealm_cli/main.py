"""CLI entry point — direct core access, no HTTP (ADR-007)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Literal

import typer

from sentrealm_core import (
    SqliteSettingsStore,
    apply_runtime_overrides,
    preprocess,
)
from sentrealm_core.env import load_project_env
from sentrealm_core.pipeline import EmptyTextError
from sentrealm_core.store import SettingsStore

app = typer.Typer(help="SentRealm — local text preprocessing for video creators.")

EXIT_INPUT_ERROR = 1
EXIT_PROCESSING_ERROR = 2


@app.callback()
def main() -> None:
    """SentRealm command-line interface."""


def get_store() -> SettingsStore:
    return SqliteSettingsStore()


def _read_input_text(*, input_file: Path | None, use_stdin: bool) -> str:
    if use_stdin:
        return sys.stdin.read()
    assert input_file is not None
    return input_file.read_text(encoding="utf-8")


def _write_processed_output(processed: str, output_file: Path | None) -> None:
    if output_file is None:
        sys.stdout.write(processed)
        return
    output_file.write_text(processed, encoding="utf-8")


def _write_metadata_stderr(line_count: int, flagged_lines: list[int]) -> None:
    payload = {"line_count": line_count, "flagged_lines": flagged_lines}
    sys.stderr.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    sys.stderr.write("\n")


@app.command("preprocess")
def preprocess_command(
    input_file: Annotated[
        Path | None,
        typer.Option("-i", "--input", help="Input .txt file path"),
    ] = None,
    use_stdin: Annotated[
        bool,
        typer.Option("--stdin", help="Read manuscript from standard input"),
    ] = False,
    output_file: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Output file path; stdout when omitted"),
    ] = None,
    preset: Annotated[
        Literal["landscape", "portrait"] | None,
        typer.Option("--preset", help="One-shot preset override: landscape | portrait"),
    ] = None,
    max_chars: Annotated[
        int | None,
        typer.Option("--max-chars", min=1, help="One-shot max_chars override (implies custom)"),
    ] = None,
) -> None:
    """Preprocess manuscript text for Jianying draft matching."""
    load_project_env()
    if use_stdin and input_file is not None:
        typer.echo("Cannot use both --input and --stdin.", err=True)
        raise typer.Exit(code=EXIT_INPUT_ERROR)
    if not use_stdin and input_file is None:
        typer.echo("Either --input or --stdin is required.", err=True)
        raise typer.Exit(code=EXIT_INPUT_ERROR)

    try:
        text = _read_input_text(input_file=input_file, use_stdin=use_stdin)
    except FileNotFoundError:
        typer.echo(f"Input file not found: {input_file}", err=True)
        raise typer.Exit(code=EXIT_INPUT_ERROR) from None
    except OSError as exc:
        typer.echo(f"Failed to read input: {exc}", err=True)
        raise typer.Exit(code=EXIT_PROCESSING_ERROR) from exc

    if not text.strip():
        typer.echo("Input text must not be empty or whitespace-only.", err=True)
        raise typer.Exit(code=EXIT_INPUT_ERROR)

    settings = apply_runtime_overrides(
        get_store().load(),
        preset=preset,
        max_chars=max_chars,
    )

    try:
        result = preprocess(text, settings)
        _write_processed_output(result.processed, output_file)
        _write_metadata_stderr(result.line_count, result.flagged_lines)
    except EmptyTextError:
        typer.echo("Input text must not be empty or whitespace-only.", err=True)
        raise typer.Exit(code=EXIT_INPUT_ERROR) from None
    except OSError as exc:
        typer.echo(f"Failed to write output: {exc}", err=True)
        raise typer.Exit(code=EXIT_PROCESSING_ERROR) from exc
    except Exception as exc:
        typer.echo(f"Preprocessing failed: {exc}", err=True)
        raise typer.Exit(code=EXIT_PROCESSING_ERROR) from exc


if __name__ == "__main__":
    app()
