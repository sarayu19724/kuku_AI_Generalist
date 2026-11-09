
import argparse, json, zipfile
from pathlib import Path
from engine import extract_zip, run_pack, outputs

def main():
    ap=argparse.ArgumentParser(description="Rank promo moments from a ZIP of timestamped episode scripts.")
    ap.add_argument("--pack",required=True,help="ZIP containing episode-*.txt files")
    ap.add_argument("--out",default="outputs",help="Output directory")
    args=ap.parse_args()
    episodes=extract_zip(Path(args.pack).read_bytes())
    if not episodes: raise SystemExit("No episode-*.txt files found in ZIP.")
    candidates,stats=run_pack(episodes)
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    md,rows=outputs(candidates,stats)
    (out/"promos.md").write_text(md,encoding="utf-8")
    (out/"promos.csv").write_text(__import__("pandas").DataFrame(rows).to_csv(index=False),encoding="utf-8")
    (out/"promos.json").write_text(json.dumps({"episodes":stats,"promos":candidates},indent=2),encoding="utf-8")
    (out/"quality_report.json").write_text(json.dumps({"episodes":len(stats),"events_parsed":sum(x["events_parsed"] for x in stats),"candidate_count":len(candidates),"episodes_with_zero_events":[x["episode"] for x in stats if x["events_parsed"]==0],"duration_valid":all(20<=c["duration"]<=60 for c in candidates)},indent=2),encoding="utf-8")
    print(f"Parsed {len(stats)} episodes / {sum(x['events_parsed'] for x in stats)} events; wrote {len(candidates)} ranked promos to {out}/")
if __name__=="__main__": main()
