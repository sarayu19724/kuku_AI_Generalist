
import streamlit as st
import pandas as pd
import json, zipfile, io
from engine import extract_zip, run_pack, outputs, stamp

st.set_page_config(page_title="Promo Finder", page_icon="🎬", layout="wide")
st.markdown("""
<style>
.block-container{padding-top:2rem;max-width:1250px}
.hero{padding:1.4rem 1.6rem;border-radius:16px;background:linear-gradient(120deg,#171b31,#343b61);color:white;margin-bottom:1rem}
.hero h1{font-size:2.25rem;margin:0 0 .35rem 0}
.hero p{color:#d8dced;margin:0}
.metric{border:1px solid #e5e7eb;border-radius:12px;padding:14px}
.small{color:#777;font-size:.85rem}
</style>
""",unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🎬 Promo Finder</h1><p>Turn timestamped microdrama screenplays into an editor-ready shortlist of 20–60 second promo moments.</p></div>',unsafe_allow_html=True)
st.write("Upload a ZIP containing files named `episode-*.txt`. The prototype parses screenplay events, scores candidate windows, ranks them, and exports the shortlist. No API key required.")
with st.sidebar:
    st.header("How scoring works")
    st.caption("A transparent, rule-based baseline — not a trained model.")
    st.markdown("- **Hook:** first 3.5 seconds")
    st.markdown("- **Cliffhanger:** final 5 seconds")
    st.markdown("- **Standalone:** dialogue density and scene size")
    st.markdown("- **Risk flags:** spoiler and graphic-violence terms")
    st.divider()
    st.caption("Human review is required before publishing. The app suggests timestamps; it does not edit or publish video.")

uploaded=st.file_uploader("Upload screenplay pack (.zip)",type=["zip"])
if uploaded:
    try:
        episodes=extract_zip(uploaded.getvalue())
        if not episodes:
            st.error("No episode-*.txt files found. Check the ZIP structure and filenames.")
        else:
            st.success(f"Found {len(episodes)} episode screenplay files.")
            if st.button("Find promo moments",type="primary",use_container_width=True):
                with st.spinner("Parsing episodes and scoring candidate windows…"):
                    candidates,stats=run_pack(episodes)
                st.session_state["results"]=(candidates,stats)
    except zipfile.BadZipFile:
        st.error("This file is not a valid ZIP archive.")
if "results" in st.session_state:
    candidates,stats=st.session_state["results"]
    if candidates:
        c1,c2,c3=st.columns(3)
        c1.metric("Episodes parsed",len(stats))
        c2.metric("Candidates ranked",len(candidates))
        c3.metric("Top score",candidates[0]["rank_score"])
        st.subheader("Ranked promo shortlist")
        df=pd.DataFrame([{"Rank":c["rank"],"Episode":c["episode"],"Start":stamp(c["start"]),"End":stamp(c["end"]),"Duration (s)":c["duration"],"Hook":c["hook_score"],"Cliffhanger":c["cliffhanger_score"],"Standalone":c["standalone_score"],"Score":c["rank_score"],"Spoiler":c["spoiler_risk"],"Ad review":c["ad_policy_risk"]} for c in candidates])
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.subheader("Inspect a candidate")
        choice=st.selectbox("Choose ranked promo",options=list(range(len(candidates))),format_func=lambda i:f'#{candidates[i]["rank"]} · Episode {candidates[i]["episode"]} · {candidates[i]["duration"]:.1f}s · score {candidates[i]["rank_score"]}')
        c=candidates[choice]
        st.markdown(f"**Episode {c['episode']} · {stamp(c['start'])} → {stamp(c['end'])} · {c['duration']:.1f} seconds**")
        a,b,d=st.columns(3)
        a.metric("Hook",c["hook_score"])
        b.metric("Cliffhanger",c["cliffhanger_score"])
        d.metric("Standalone",c["standalone_score"])
        if c["spoiler_risk"]: st.warning("Potential spoiler: review before using for cold-audience acquisition.")
        if c["ad_policy_risk"]: st.warning("Potential graphic-violence/ad-policy risk: manual review required.")
        st.text_area("Screenplay transcript in this window",c["text"],height=220)
        md,rows=outputs(candidates,stats)
        st.download_button("Download ranked promos (.md)",md,file_name="promos.md",mime="text/markdown")
        st.download_button("Download ranked promos (.csv)",pd.DataFrame(rows).to_csv(index=False),file_name="promos.csv",mime="text/csv")
        st.download_button("Download ranked promos (.json)",json.dumps({"episodes":stats,"promos":candidates},indent=2),file_name="promos.json",mime="application/json")
        with st.expander("Parsing diagnostics"):
            st.dataframe(pd.DataFrame(stats),use_container_width=True,hide_index=True)
            st.caption("A low event count can indicate a screenplay format the parser does not yet recognize.")
    else:
        st.warning("No valid 20–60 second windows were found. Check whether the screenplay timestamps match the expected format.")

st.divider()
st.caption("Prototype v1 · Deterministic baseline · No screenplay content is sent to an external API.")
