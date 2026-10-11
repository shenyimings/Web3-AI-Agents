"""Recover a self-description for screened T2 projects CoinGecko has no prose for.

Screening rule S3 admits a project only if it describes itself somewhere. The
sources are not equivalent evidence, so they are tried in a fixed order and the
one that supplied the text is recorded per row as `desc_source`: a project site
is self-description, a whitepaper is a formal claim, a repository blurb is a
developer's summary. Rows that yield nothing stay in the output with
`desc_source: null` so the classifier can report them as unclassifiable rather
than silently losing them.

Writes data/raw/fetched_descriptions.json. Resumable.
"""

import html
import json
import os
import pathlib
import re
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = RAW / "fetched_descriptions.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
      "(academic research; contact via repository)")
MIN_LEN = 80
MAX_LEN = 1500

DROP_TAGS = re.compile(r"<(script|style|noscript|svg|head)[^>]*>.*?</\1>",
                       re.S | re.I)
TAG = re.compile(r"<[^>]+>")
META = [re.compile(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']{40,})["\']', re.I),
        re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']{40,})["\']', re.I),
        re.compile(r'<meta[^>]+content=["\']([^"\']{40,})["\'][^>]+name=["\']description["\']', re.I)]


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(text)).strip()[:MAX_LEN]


def from_html(body):
    """Meta description first, then the longest run of visible prose."""
    for pat in META:
        m = pat.search(body)
        if m:
            return clean(m.group(1))
    stripped = TAG.sub(" ", DROP_TAGS.sub(" ", body))
    chunks = [clean(c) for c in re.split(r"\n{2,}|\. (?=[A-Z])", stripped)]
    best = max((c for c in chunks if len(c) >= MIN_LEN), key=len, default="")
    return best


def fetch(session, url):
    try:
        r = session.get(url, timeout=20, allow_redirects=True,
                        headers={"User-Agent": UA,
                                 "Accept": "text/html,application/xhtml+xml"})
    except Exception as e:
        return None, type(e).__name__
    if r.status_code != 200:
        return None, f"http{r.status_code}"
    if "html" not in r.headers.get("content-type", ""):
        return None, "not-html"
    return from_html(r.text), None


def github_blurb(session, repos, token):
    for url in repos[:3]:
        m = re.search(r"github\.com/([^/]+)/([^/#?]+)", url or "")
        if not m:
            continue
        r = session.get(f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}",
                        timeout=20, headers={"Authorization": f"Bearer {token}",
                                             "Accept": "application/vnd.github+json"})
        if r.status_code == 200:
            d = r.json()
            text = " ".join(filter(None, [d.get("description"),
                                          " ".join(d.get("topics") or [])]))
            if len(text) >= 40:
                return clean(text)
        time.sleep(0.3)
    return None


def main():
    det = {d["id"]: d for d in json.loads((RAW / "cg_details.json").read_text())}
    desc = json.loads((RAW / "cg_descriptions.json").read_text())
    links = json.loads((RAW / "cg_links.json").read_text())
    screened = json.loads((ROOT / "data/processed/t2_screened_ids.json").read_text())

    todo = [k for k in screened
            if not (desc.get(k, {}).get("description") or "").strip()]
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [k for k in todo if k not in done]
    print(f"{len(todo)} screened projects need a description", flush=True)

    token = os.environ.get("GITHUB_TOKEN", "")
    session = requests.Session()
    for n, cid in enumerate(todo, 1):
        lk, dt = links.get(cid, {}), det.get(cid, {})
        row = {"id": cid, "description": None, "desc_source": None,
               "attempts": {}}

        for source, url in [("homepage", (lk.get("homepage") or [None])[0]),
                            ("whitepaper", lk.get("whitepaper"))]:
            if not url:
                continue
            text, err = fetch(session, url)
            row["attempts"][source] = err or f"{len(text or '')} chars"
            if text and len(text) >= MIN_LEN:
                row.update(description=text, desc_source=source, source_url=url)
                break
            time.sleep(0.5)

        if not row["description"] and dt.get("github_repos") and token:
            text = github_blurb(session, dt["github_repos"], token)
            row["attempts"]["github"] = f"{len(text or '')} chars"
            if text:
                row.update(description=text, desc_source="github")

        done[cid] = row
        if n % 20 == 0 or n == len(todo):
            OUT.write_text(json.dumps(done, indent=1))
            got = sum(1 for v in done.values() if v["description"])
            print(f"  {n}/{len(todo)}  recovered {got}", flush=True)

    OUT.write_text(json.dumps(done, indent=1))
    got = [v for v in done.values() if v["description"]]
    print(f"\n{len(done)} attempted, {len(got)} recovered -> {OUT}")
    by = {}
    for v in got:
        by[v["desc_source"]] = by.get(v["desc_source"], 0) + 1
    print("  by source:", by)


if __name__ == "__main__":
    main()
