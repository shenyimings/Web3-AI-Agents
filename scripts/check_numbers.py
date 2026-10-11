r"""Guard the numbers: nothing typed in, and no frame mixed inside a section.

    uv run python scripts/check_numbers.py

Three checks, in the order they matter.

1. **Internal consistency.** The generated macros must add up -- classified plus
   residual is the screened population, and the shares of a total are a total.
   A failure here means the data changed shape, not the prose.
2. **Frame mixing.** Every ``\n...`` macro carries its frame. A section that
   uses two frames is reported with the offending lines, because that is the
   error the naming exists to make visible. A section may declare its frame
   with a ``% frame: Cls`` comment; where it does, foreign macros are an error
   rather than a warning.
3. **Typed-in numbers.** Any bare figure left in the prose, minus a whitelist
   of things that are not data (years, section and ERC numbers, page counts).
   This is a migration counter: it should fall to zero as the sweep proceeds.
"""

import collections
import json
import pathlib
import re
import sys

import stats

PAPER = stats.ROOT.parent / "paper"
MACROS = json.loads((stats.ROOT / "data/processed/macros.json").read_text())

FRAMES = ["Pop", "Scr", "Cls", "Coh", "Pan", "Rep", "Gov", "XFour", "Erc",
          "Std", "Date", "Window"]
# nAliveFloor / nStaleDays are thresholds shared by several frames, not frames.
# Numbers in the prose that are not measurements.
IGNORE = re.compile(
    r"""(?x)
    \\(?:cite|ref|label|autoref|input|include|section|cline|multirow|columnwidth
       |linewidth|textwidth|hspace|vspace|setlength|begin|end)\b.*
    | ERC-\d+ | EIP-\d+ | x402 | A2A | \bGPT-\d
    | \b(?:19|20)\d\d\b            # years
    | \b\d+(?:pt|em|ex|cm|mm|in)\b # lengths
    """)
BARE = re.compile(r"(?<![\w\\{-])\d+(?:[.,]\d+)*\\?%?")
# A line ending in this comment declares its numerals to be definitional
# constants -- a percentile, a tier edge, a threshold the statistic is defined
# by -- rather than measurements that a macro should carry.
LITERAL = re.compile(r"%\s*lit\b")


def files():
    return sorted(PAPER.glob("tex/*.tex")) + sorted(PAPER.glob("tables/*.tex"))


def frame_of(macro):
    for f in FRAMES:
        if macro.startswith("n" + f):
            return f
    return None


def check_consistency():
    """The generated numbers must agree with each other."""
    pop, cls, residual = stats.pop(), stats.cls(), stats.residual()
    total = sum(stats.mcap(r) for r in cls)
    problems = []

    coded = len(cls) + sum(residual.values())
    if coded != pop["n"]:
        problems.append(f"classified {len(cls)} + residual {sum(residual.values())} "
                        f"= {coded}, but the screened population is {pop['n']}")
    if total > pop["mcap"]:
        problems.append("classified value exceeds the population it is drawn from")

    subs = stats.by_subcategory(cls)
    facets = stats.by_facet(cls)
    if sum(f["n"] for f in facets.values()) != subs["infrastructure"]["n"]:
        problems.append("the facets do not partition the infrastructure subcategory")

    prim = stats.by_primary(cls)
    assignments = sum(len(r["labels"]) for r in cls)
    if sum(s["n"] for s in subs.values()) != assignments:
        problems.append("subcategory counts do not sum to label assignments")
    if sum(p["n"] for p in prim.values()) < len(cls):
        problems.append("primary categories do not cover every classified project")
    return problems


def blocks(text):
    """Split a file into (name, first_line, lines) at section boundaries.

    Frames are owned by subsections, not by files: RQ1 legitimately uses four
    of them, one per subsection, and it is inside a subsection that mixing is
    the error.
    """
    out, name, start, buf = [], "(preamble)", 1, []
    for i, line in enumerate(text.splitlines(), 1):
        if re.match(r"\\(?:sub)*section\*?\{", line):
            out.append((name, start, buf))
            name, start, buf = line.strip()[:60], i, []
        buf.append(line)
    out.append((name, start, buf))
    return [b for b in out if b[2]]


def check_frames():
    """Report the frames each subsection uses, and flag the ones mixing them.

    A block may declare which frames it is entitled to with a comment --
    ``% frame: Cls`` -- and the methodology, where every frame is defined,
    declares ``% frame: all``. Undeclared blocks fall back to the default rule:
    one value frame per subsection.
    """
    used, mixed, foreign = collections.Counter(), [], []
    for path in files():
        text = path.read_text()
        first = text.split("\n")[0]
        allow_file = {w for decl in re.findall(r"%\s*frames?:\s*([\w\s,]+)", first)
                      for w in re.split(r"[\s,]+", decl.strip()) if w}
        for name, start, lines in blocks(text):
            declared = set(allow_file)
            for decl in re.findall(r"%\s*frames?:\s*([\w\s,]+)", "\n".join(lines)):
                declared |= {w for w in re.split(r"[\s,]+", decl.strip()) if w}
            seen = collections.defaultdict(list)
            for offset, line in enumerate(lines):
                for macro in re.findall(r"\\(n[A-Z]\w*)", line):
                    if macro in MACROS and (f := frame_of(macro)):
                        seen[f].append((start + offset, macro))
            used[path] += sum(len(v) for v in seen.values())
            value_frames = {f for f in seen if f not in ("Date", "Window", "Scr")}
            if "all" in declared:
                continue
            where = f"{path.name} {name}"
            if declared:
                stray = {f: seen[f] for f in value_frames - declared}
                if stray:
                    foreign.append((where, declared, stray))
            elif len(value_frames) > 1:
                mixed.append((where, {f: seen[f] for f in value_frames}))
    return used, mixed, foreign


def check_typed_numbers():
    left = {}
    for path in files():
        text = path.read_text()
        if "GENERATED by scripts/" in text:
            continue  # written from stats.py; typed numerals are the point
        hits = []
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("%") or LITERAL.search(line):
                continue
            stripped = IGNORE.sub(" ", line)
            found = BARE.findall(stripped)
            if found:
                hits.append((i, found))
        if hits:
            left[path] = hits
    return left


def main():
    fail = False
    problems = check_consistency()
    print("consistency:", "ok" if not problems else "FAILED")
    for p in problems:
        print("  !", p)
    fail |= bool(problems)

    used, mixed, foreign = check_frames()
    print(f"macro use: {sum(used.values())} across {len(used)} files")
    for where, seen in mixed:
        print(f"  ! {where} mixes frames: "
              + ", ".join(f"{f} ({len(v)})" for f, v in seen.items()))
        for f, v in seen.items():
            print(f"      {f}: " + ", ".join(f"{m}@{i}" for i, m in v[:4]))
    for where, declared, stray in foreign:
        print(f"  ! {where} declares {'/'.join(sorted(declared))} but uses "
              + ", ".join(f"{f} ({len(v)})" for f, v in stray.items()))
        for f, v in stray.items():
            print(f"      {f}: " + ", ".join(f"{m}@{i}" for i, m in v[:4]))
    fail |= bool(mixed or foreign)

    left = check_typed_numbers()
    n = sum(len(h) for h in left.values())
    print(f"typed-in numbers: {n} lines still carry one")
    for path, hits in left.items():
        print(f"  {path.name:24s} {len(hits):4d}  e.g. line {hits[0][0]}: {hits[0][1][:4]}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
