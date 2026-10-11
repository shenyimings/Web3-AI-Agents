"""Follow every T1 cohort member to T2 by date, not by category.

The T2 pool was assembled from a narrower set of categories than the T1 cohort,
so intersecting the two measures frame mismatch rather than attrition: NEAR,
Internet Computer, Bittensor and Render all scored as exits while trading
normally. A cohort is fixed at entry and followed forward, so each member's T2
value is read from its own history on 1 September 2026 and a member counts as gone
only when it has no market capitalisation on that date.
"""
import json, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = dict(l.strip().split("=", 1) for l in open(ROOT / ".env") if "=" in l)["COINGECKO_API_KEY"]
T2 = "01-09-2026"


def cg(path):
    for i in range(4):
        try:
            req = urllib.request.Request("https://pro-api.coingecko.com/api/v3" + path,
                                         headers={"x-cg-pro-api-key": KEY, "User-Agent": "research"})
            return json.loads(urllib.request.urlopen(req, timeout=120).read())
        except urllib.error.HTTPError as e:
            return {"__http__": e.code}
        except Exception:
            if i == 3:
                return {"__http__": "read-error"}
            time.sleep(2)


def main():
    raw = json.loads((ROOT / "data/raw/wayback/t1_union_raw.json").read_text())
    cohort = [u for u in raw if u["t1_market_cap"]]
    out = ROOT / "data/raw/wayback/t1_cohort_followup.json"
    done = {}
    if out.exists():
        done = {u["cg_id"]: u for u in json.loads(out.read_text())}
    todo = [u for u in cohort if u["cg_id"] not in done]
    print(f"capitalised at T1: {len(cohort)}; {len(todo)} to read at {T2} ...", flush=True)

    for i, u in enumerate(todo, 1):
        d = cg(f"/coins/{u['cg_id']}/history?date={T2}&localization=false")
        u["t2_market_cap"] = (None if "__http__" in d
                              else ((d.get("market_data") or {}).get("market_cap") or {}).get("usd"))
        u["t2_error"] = d.get("__http__") if "__http__" in d else None
        if i % 50 == 0:
            print(f"  {i}/{len(todo)}", flush=True)
        time.sleep(0.22)

    for u in cohort:
        if u["cg_id"] in done:
            u.update({k: done[u["cg_id"]][k] for k in ("t2_market_cap", "t2_error")})
    out.write_text(json.dumps(cohort, indent=2))
    alive = [u for u in cohort if u["t2_market_cap"]]
    print(f"\nstill capitalised at T2: {len(alive)}/{len(cohort)} ({len(alive)/len(cohort):.1%})")
    print(f"cohort T1 ${sum(u['t1_market_cap'] for u in cohort):,.0f} -> "
          f"T2 ${sum(u['t2_market_cap'] for u in alive):,.0f}")


if __name__ == "__main__":
    main()
