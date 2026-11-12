"""In-feed and dark (paid-only) benchmarks are never averaged together."""
import csv
from app.compute.benchmarks import compute_live_benchmarks

COLS = ["Campaign", "Client", "Benchmark Category", "Franchise / IP", "Content Type",
        "Distribution", "Tentpole?", "Tentpole Moment", "Year", "Program",
        "Instagram", "Facebook", "X", "TikTok", "LinkedIn", "YouTube Shorts", "YouTube",
        "Meta (Dark)", "All Platforms", "Spend ($)", "Include in Benchmarks", "Group"]


def _row(name, cat, dist, allp, group=""):
    r = {c: "" for c in COLS}
    r.update({"Campaign": name, "Benchmark Category": cat, "Distribution": dist,
              "Program": "Sponsored", "All Platforms": allp,
              "Include in Benchmarks": "Yes", "Group": group})
    return r


def test_dark_and_infeed_are_separate(tmp_path):
    p = tmp_path / "c.csv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerow(_row("A", "Video: Custom Social (Organic + Boosted)", "Organic + Boosted", "0.04", "In-feed"))
        w.writerow(_row("A", "Video: Custom Social (Dark Only)", "Dark Only", "0.01", "Dark"))
        # no Group column value -> inferred from distribution
        w.writerow(_row("B", "Video: Custom Social (Dark Only)", "Dark Only", "0.03"))
    live = compute_live_benchmarks(p, tmp_path / "missing.csv")
    cats = {c["name"]: c for c in live["categories"]}
    assert cats["Video: Custom Social (Organic + Boosted)"]["group"] == "In-feed"
    assert cats["Video: Custom Social (Dark Only)"]["group"] == "Dark"
    assert cats["Video: Custom Social (Dark Only)"]["all"] == 2.0  # (1+3)/2, in-feed 4 not blended
    assert live["all_sponsored"]["n_campaigns"] == 1  # in-feed only
    assert live["all_sponsored"]["all"] == 4.0
