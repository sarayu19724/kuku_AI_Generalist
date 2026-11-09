
import re, csv, json, io, zipfile
from pathlib import Path
from collections import Counter

TS = r"\d{2}:\d{2}(?:\.\d{1,2})?"
BLOCK = re.compile(rf"(?P<label>\*\*[^*]+\*\*|[A-Z][A-Z0-9 _()/-]{{1,55}}):\s*\nStart:\s*\((?P<start>{TS})\)\s*\|\s*End:\s*\((?P<end>{TS})\)\s*\n(?P<body>.*?)(?=\n(?:\*\*[^*]+\*\*|[A-Z][A-Z0-9 _()/-]{1,55}):\s*\nStart:|\nSCENE \d+|\Z)", re.S)

def sec(ts):
    m=re.match(r"(\d+):(\d+)(?:\.(\d+))?",ts)
    return int(m.group(1))*60+int(m.group(2))+(float("0."+m.group(3)) if m.group(3) else 0)

def stamp(s):
    return f"{int(s//60):02d}:{s%60:05.2f}"

def parse_episode(name, raw):
    events=[]
    lines=raw.splitlines()
    def is_label(line):
        t=line.strip()
        return (t.startswith("**") and t.endswith("**")) or (re.match(r"^[A-Z][A-Z0-9 _()/-]{1,55}:$",t) is not None)
    i=0
    while i<len(lines):
        if not is_label(lines[i]):
            i+=1; continue
        k=i+1
        while k<len(lines) and not lines[k].strip(): k+=1
        m=re.match(rf"Start:\s*\(({TS})\)\s*\|\s*End:\s*\(({TS})\)",lines[k].strip()) if k<len(lines) else None
        if not m:
            i+=1; continue
        j=k+1
        body=[]
        while j<len(lines):
            if is_label(lines[j]):
                q=j+1
                while q<len(lines) and not lines[q].strip(): q+=1
                if q<len(lines) and re.match(rf"Start:\s*\({TS}\)",lines[q].strip()):
                    break
            if re.match(r"^SCENE \d+",lines[j].strip()) or lines[j].strip()=="--- SCRIPT END ---":
                break
            body.append(lines[j].strip())
            j+=1
        txt=" ".join(x for x in body if x)
        if txt:
            events.append({"start":sec(m.group(1)),"end":sec(m.group(2)),"label":lines[i].strip("*: "),"text":txt})
        i=j if j>i else i+1
    return events

HOOK = ["slap","strik","hit","kill","dead","poison","arsenic","betray","marry","marrying","turn around","guards","remove her","silence","no","why","what","how dare","you planted","fire","blood","scream","betrayal","secret","never","stop"]
CLIFF = ["who","what","why","how","will","door","latch","creak","arriv","emerge","explod","take her","kill","hang","poison","antidote","before","unless","then","prove","tell me","you cannot","i will","coming home","freeze","raised","thrust","stare","gasp","suddenly"]
SOFT = ["smil","laugh","hug","kiss","thank","safe","relief","happily","embrace","tender","gentle"]

def score_window(events, a, b):
    chosen=[e for e in events if e["start"]>=a-0.001 and e["end"]<=b+0.001]
    text=" ".join(e["text"].lower() for e in chosen)
    starttext=" ".join(e["text"].lower() for e in events if a<=e["start"]<a+3.6)
    endtext=" ".join(e["text"].lower() for e in events if e["end"]>b-5.1 and e["end"]<=b+0.001)
    hook=sum(1 for k in HOOK if k in starttext)
    cliff=sum(1 for k in CLIFF if k in endtext)
    soft=sum(1 for k in SOFT if k in endtext)
    speakers=len(set(re.findall(r"^([A-Z][A-Z0-9 _'-]+)(?:\s*\([^)]*\))?:", "\n".join(e["label"] for e in chosen))))
    dialogue=sum(1 for e in chosen if not any(x in e["label"].upper() for x in ["CAMERA","MUSIC","SFX"]))
    action=sum(1 for e in chosen if "ACTION" in e["label"].upper())
    hook_score=min(5, 1+hook*0.9+(1 if len(starttext.split())<18 and starttext else 0))
    cliff_score=min(5, 1+cliff*0.8-soft*0.7)
    standalone=min(5, 2+(1 if len(chosen)>=4 else 0)+(1 if 2<=speakers<=4 else 0)+(1 if dialogue>=2 else 0))
    spoiler=2 if any(k in text for k in ["dead duke","coming home","they are marrying in two days","dead husband"]) else 0
    adrisk=1 if any(k in text for k in ["red-hot iron","burning iron","eye","throat slit","blood pours"]) else 0
    rank=hook_score+1.2*cliff_score+0.8*standalone-1.5*spoiler-adrisk
    return {"hook_score":round(hook_score,2),"cliffhanger_score":round(cliff_score,2),"standalone_score":round(standalone,2),"spoiler_risk":spoiler,"ad_policy_risk":adrisk,"rank_score":round(rank,2),"event_count":len(chosen),"text":text}

def build_candidates(events, episode):
    if not events: return []
    # Candidate starts and ends on screenplay event boundaries.
    boundaries=sorted(set([e["start"] for e in events]+[e["end"] for e in events]))
    out=[]
    for a in boundaries:
        for b in boundaries:
            d=b-a
            if d<20 or d>60: continue
            chosen=[e for e in events if e["start"]>=a-1e-3 and e["end"]<=b+1e-3]
            if len(chosen)<3: continue
            s=score_window(events,a,b)
            if s["event_count"]<3: continue
            out.append({"episode":episode,"start":round(a,2),"end":round(b,2),"duration":round(d,2),**s})
    out.sort(key=lambda x:x["rank_score"],reverse=True)
    # Limit near-duplicate windows: keep at most 2 per episode, with overlap penalty.
    picked=[]
    for c in out:
        if all(not (c["start"] < p["end"] and p["start"] < c["end"] and min(c["end"],p["end"])-max(c["start"],p["start"]) > .65*min(c["duration"],p["duration"])) for p in picked):
            picked.append(c)
        if len(picked)>=2: break
    return picked

def extract_zip(data):
    episodes={}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            p=Path(n)
            if p.name.lower().startswith("episode-") and p.suffix.lower()==".txt":
                try:
                    raw=z.read(n).decode("utf-8-sig",errors="replace")
                    m=re.search(r"episode-(\d+)",p.name,re.I)
                    ep=int(m.group(1)) if m else len(episodes)+1
                    episodes[ep]=(p.name,raw)
                except Exception: pass
    return episodes

def run_pack(episodes):
    all_candidates=[]
    stats=[]
    for ep,(name,raw) in sorted(episodes.items()):
        events=parse_episode(name,raw)
        stats.append({"episode":ep,"events_parsed":len(events),"file":name})
        all_candidates.extend(build_candidates(events,ep))
    all_candidates.sort(key=lambda x:x["rank_score"],reverse=True)
    # Cross-episode ranking; preserve best per episode among candidates.
    for i,c in enumerate(all_candidates,1): c["rank"]=i
    return all_candidates,stats

def outputs(candidates,stats):
    rows=[]
    for c in candidates:
        rows.append({k:c[k] for k in ["rank","episode","start","end","duration","hook_score","cliffhanger_score","standalone_score","spoiler_risk","ad_policy_risk","rank_score"]})
    md=["# Promo Finder — ranked candidates","",f"Parsed {len(stats)} episodes; generated {len(candidates)} candidate promos.","","| Rank | Episode | Start–End | Duration | Score | Hook / cliff / standalone | Flags |","|---:|---:|---:|---:|---:|---|---|"]
    for c in candidates:
        flags=[]
        if c["spoiler_risk"]: flags.append("spoiler")
        if c["ad_policy_risk"]: flags.append("ad-policy review")
        md.append(f'| {c["rank"]} | {c["episode"]} | {stamp(c["start"])}–{stamp(c["end"])} | {c["duration"]:.1f}s | {c["rank_score"]} | {c["hook_score"]}/{c["cliffhanger_score"]}/{c["standalone_score"]} | {", ".join(flags) or "—"} |')
    md += ["","## Candidate transcripts",""]
    for c in candidates:
        md += [f'### #{c["rank"]} — Episode {c["episode"]} ({stamp(c["start"])}–{stamp(c["end"])}, {c["duration"]:.1f}s)',"",c["text"],""]
    return "\n".join(md), rows
