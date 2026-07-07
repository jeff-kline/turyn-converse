"""Transcription gate for capstone.tex vs. the companion source paper.

Extracts every theorem-like environment (theorem, lemma, proposition,
corollary, definition, remark, conjecture) from capstone.tex and requires
each one to appear, whitespace-normalized, verbatim inside
paper/companion/turyn_converse.tex. Zero mismatches required.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ENVIRONMENTS = [
    "theorem",
    "lemma",
    "proposition",
    "corollary",
    "definition",
    "remark",
    "conjecture",
]


def extract_blocks(tex: str) -> list[tuple[str, str]]:
    blocks = []
    for env in ENVIRONMENTS:
        pattern = re.compile(
            r"\\begin\{" + env + r"\}.*?\\end\{" + env + r"\}", re.DOTALL
        )
        for m in pattern.finditer(tex):
            blocks.append((env, m.group(0)))
    return blocks


def normalize(block: str) -> str:
    return " ".join(block.split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--capstone",
        default=str(Path(__file__).resolve().parents[2] / "paper" / "capstone.tex"),
    )
    parser.add_argument(
        "--companion",
        default=str(
            Path(__file__).resolve().parents[2]
            / "paper"
            / "companion"
            / "turyn_converse.tex"
        ),
    )
    args = parser.parse_args()

    capstone_tex = Path(args.capstone).read_text()
    companion_tex = Path(args.companion).read_text()

    capstone_blocks = extract_blocks(capstone_tex)
    companion_normalized = normalize(companion_tex)

    mismatches = []
    for env, block in capstone_blocks:
        if normalize(block) not in companion_normalized:
            mismatches.append((env, block[:120]))

    print(f"capstone.tex: {len(capstone_blocks)} theorem-like blocks extracted")
    by_env: dict[str, int] = {}
    for env, _ in capstone_blocks:
        by_env[env] = by_env.get(env, 0) + 1
    for env in ENVIRONMENTS:
        print(f"  {env}: {by_env.get(env, 0)}")

    if mismatches:
        print(f"MISMATCHES: {len(mismatches)}")
        for env, snippet in mismatches:
            print(f"  [{env}] {snippet!r}...")
        return 1

    print("mismatches=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
