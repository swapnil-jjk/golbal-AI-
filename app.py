from datetime import datetime
from html import escape

import streamlit as st

from answer_verifier import ClaimVerificationError, verify_claim
from bifrost_client import ModelResponseError
from claim_extractor import ClaimExtractionError, extract_claims
from pdf_generator import generate_pdf
from web_research import research_claim


st.set_page_config(page_title="StaleAnswer AI", page_icon="✦", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --bg:#000000; --primary:#2D4F1F; --secondary:#F5E6CC; --accent:#E27D60; --neutral:#4A4A4A; }
html, body, [class*="css"] { font-family:'Manrope',sans-serif; color:var(--secondary); }
.stApp { background:var(--bg); } .block-container { max-width:1240px; padding:2.2rem 2rem 5rem; }
[data-testid="stHeader"] { background:transparent; } [data-testid="stSidebar"] { background:#080808; border-right:1px solid #222; }
.eyebrow,.section-kicker,.metric-label { color:var(--accent); font-family:'DM Mono',monospace; text-transform:uppercase; letter-spacing:.14em; font-size:.7rem; }
h1 { color:var(--secondary)!important; font-size:clamp(2.5rem,6vw,5.4rem)!important; line-height:.98!important; letter-spacing:-.065em; max-width:820px; margin:.8rem 0 1.25rem!important; }
h2,h3 { color:var(--secondary)!important; letter-spacing:-.035em; } .lede { color:#bfb5a5; font-size:1.05rem; line-height:1.65; max-width:650px; }
.hero { border-bottom:1px solid #252525; padding:1rem 0 3.2rem; margin-bottom:2rem; } .hero-mark { color:var(--primary); font-size:4rem; line-height:1; }
.panel,.metric-card { background:#111; border:1px solid #292929; border-radius:18px; padding:1.15rem 1.3rem; transition:all .2s ease; }
.panel:hover,.metric-card:hover { border-color:var(--primary); transform:translateY(-1px); }
.metric-label { color:#9e968a; letter-spacing:.1em; } .metric-value { color:var(--secondary); font-size:2.1rem; font-weight:700; margin-top:.25rem; }
.metric-sub { color:#9e968a; font-size:.8rem; margin-top:.15rem; } .section-kicker { margin:2rem 0 .7rem; }
.status { display:inline-block; border-radius:999px; padding:.35rem .7rem; font-family:'DM Mono',monospace; font-size:.68rem; text-transform:uppercase; letter-spacing:.05em; }
.status-good { color:#b8d5a8; background:#183116; } .status-warn { color:#f2b09d; background:#3b2119; } .status-neutral { color:#c8c1b8; background:#292929; }
.score-ring { border:1px solid #38542e; background:radial-gradient(circle at center,#152312 0,#101010 68%); border-radius:50%; width:118px; height:118px; display:flex; align-items:center; justify-content:center; flex-direction:column; }
.score-number { font-size:2rem; color:var(--secondary); font-weight:800; line-height:1; } .score-caption { color:#9e968a; font-size:.68rem; text-transform:uppercase; letter-spacing:.08em; margin-top:.35rem; }
.source-link { color:#d6a08e!important; text-decoration:none; } .source-link:hover { color:var(--secondary)!important; }
.stTextArea textarea { background:#0f0f0f!important; color:var(--secondary)!important; border:1px solid #333!important; border-radius:14px!important; padding:1rem!important; }
.stTextArea textarea:focus { border-color:var(--primary)!important; box-shadow:0 0 0 1px var(--primary)!important; }
.stButton>button,.stDownloadButton>button { background:var(--primary)!important; color:var(--secondary)!important; border:1px solid #527a3e!important; border-radius:999px!important; padding:.7rem 1.4rem!important; font-weight:700!important; transition:all .2s ease; }
.stButton>button:hover,.stDownloadButton>button:hover { background:#3a6828!important; transform:translateY(-1px); } .stProgress>div>div>div>div { background:var(--primary); }
[data-testid="stExpander"] { background:#111; border:1px solid #292929; border-radius:16px; } .small-muted { color:#9e968a; font-size:.83rem; }
</style>
""", unsafe_allow_html=True)

STATUS_SCORES = {"Verified": 100, "Potentially outdated": 50, "Conflicting": 0, "Unable to verify": 25}


def calculate_freshness_score(results):
    if not results:
        return 0
    return round(sum(STATUS_SCORES.get(item.get("status"), 25) for item in results) / len(results))


def status_class(status):
    if status == "Verified":
        return "status-good"
    if status in {"Potentially outdated", "Conflicting"}:
        return "status-warn"
    return "status-neutral"


def run_analysis(answer):
    claims = extract_claims(answer)
    results = []
    for claim in claims:
        try:
            research = research_claim(claim)
        except Exception as error:
            research = {"claim": claim, "sources": [], "error": str(error)}
        verification = verify_claim(claim, research)
        verification["sources"] = research.get("sources", [])
        verification["research_error"] = research.get("error")
        verification["freshness_score"] = STATUS_SCORES.get(verification.get("status"), 25)
        results.append(verification)
    return results


def render_result(result, index):
    status = result.get("status", "Unable to verify")
    sources = result.get("sources", [])
    freshness_score = result.get("freshness_score", STATUS_SCORES.get(status, 25))
    with st.expander(f"{index:02d}  ·  {result.get('claim', '')}", expanded=index == 1):
        left, right = st.columns([3, 1])
        with left:
            st.markdown(f'<span class="status {status_class(status)}">{escape(status)}</span>', unsafe_allow_html=True)
            st.markdown("**Why this result**")
            st.write(result.get("explanation", ""))
            st.markdown("**Freshness note**")
            st.write(result.get("freshness_note", ""))
        with right:
            st.markdown(f'<div class="score-ring"><div class="score-number">{freshness_score}</div><div class="score-caption">claim score</div></div>', unsafe_allow_html=True)
        if result.get("research_error"):
            st.warning(result["research_error"])
        st.markdown(f"**Evidence · {len(sources)} source{'s' if len(sources) != 1 else ''}**")
        if not sources:
            st.caption("No current source evidence was found for this claim.")
        for source in sources:
            safe_url = escape(source.get("url", ""), quote=True)
            title = escape(source.get("title") or "Open source")
            st.markdown(f'<a class="source-link" href="{safe_url}" target="_blank">↗ {title}</a>', unsafe_allow_html=True)
            if source.get("content"):
                st.caption(source["content"])


if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.markdown('<div class="eyebrow">StaleAnswer AI</div>', unsafe_allow_html=True)
    st.markdown("### A freshness layer for AI")
    st.caption("Turn confident answers into evidence-backed decisions.")
    st.markdown("---")
    st.markdown("**Pipeline**")
    st.caption("01  Extract claims")
    st.caption("02  Research with Tavily")
    st.caption("03  Verify with Bifrost")
    st.caption("04  Score freshness")
    if st.session_state.history:
        st.markdown("---")
        st.markdown("**Recent checks**")
        for item in reversed(st.session_state.history[-5:]):
            st.caption(f"{item['score']}/100 · {item['count']} claims · {item['time']}")

st.markdown('<div class="hero"><div class="hero-mark">✦</div><div class="eyebrow">Problem statement 06 · Live verification</div><h1>Find the claims that time forgot.</h1><p class="lede">Paste an AI-generated answer and turn uncertainty into a clear, source-backed freshness report. StaleAnswer checks time-sensitive facts against live web evidence before you trust them.</p></div>', unsafe_allow_html=True)

input_col, guidance_col = st.columns([2.2, 1])
with input_col:
    st.markdown('<div class="section-kicker">01 · Submit an answer</div>', unsafe_allow_html=True)
    answer = st.text_area("AI-generated answer", height=245, label_visibility="collapsed", placeholder="Paste an AI-generated answer here…\n\nTip: include pricing, API versions, regulations, dates, or leadership claims to see freshness detection in action.")
    check = st.button("Check answer  →", type="primary", use_container_width=True)
with guidance_col:
    st.markdown('<div class="section-kicker">What gets checked</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><strong>Claim identification</strong><br><span class="small-muted">Independent factual statements are extracted and deduplicated.</span><br><br><strong>Freshness detection</strong><br><span class="small-muted">Pricing, APIs, laws, dates, and leadership can change over time.</span><br><br><strong>Live verification</strong><br><span class="small-muted">Tavily retrieves current sources; Bifrost evaluates the evidence.</span></div>', unsafe_allow_html=True)

if check:
    if not answer.strip():
        st.warning("Please enter an answer first.")
    else:
        try:
            with st.status("Running live verification…", expanded=True) as pipeline:
                st.write("Extracting independent factual claims")
                results = run_analysis(answer)
                st.write(f"Researched {len(results)} claims with Tavily")
                st.write("Compared evidence with the configured Bifrost model")
                pipeline.update(label="Verification complete", state="complete", expanded=False)
            score = calculate_freshness_score(results)
            st.session_state.analysis = {"answer": answer, "results": results, "score": score, "time": datetime.now().strftime("%d %b %Y, %H:%M")}
            st.session_state.history.append({"score": score, "count": len(results), "time": st.session_state.analysis["time"]})
        except (ClaimExtractionError, ClaimVerificationError, ModelResponseError, RuntimeError, ValueError) as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"The verification workflow could not be completed ({type(error).__name__}). Check Bifrost and Tavily configuration.")

analysis = st.session_state.analysis
if analysis:
    results = analysis["results"]
    score = analysis["score"]
    st.markdown('<div class="section-kicker">02 · Verification report</div>', unsafe_allow_html=True)
    summary_cols = st.columns([1.1, 1, 1, 1])
    with summary_cols[0]:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Overall freshness</div><div class="metric-value">{score}<span style="font-size:1rem;color:#9e968a"> / 100</span></div><div class="metric-sub">Heuristic evidence score</div></div>', unsafe_allow_html=True)
    with summary_cols[1]:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Claims checked</div><div class="metric-value">{len(results)}</div><div class="metric-sub">Independent factual claims</div></div>', unsafe_allow_html=True)
    with summary_cols[2]:
        verified = sum(item.get("status") == "Verified" for item in results)
        st.markdown(f'<div class="metric-card"><div class="metric-label">Verified</div><div class="metric-value">{verified}</div><div class="metric-sub">Supported by evidence</div></div>', unsafe_allow_html=True)
    with summary_cols[3]:
        flagged = sum(item.get("status") in {"Potentially outdated", "Conflicting"} for item in results)
        st.markdown(f'<div class="metric-card"><div class="metric-label">Needs review</div><div class="metric-value">{flagged}</div><div class="metric-sub">Outdated or conflicting</div></div>', unsafe_allow_html=True)
    st.progress(score / 100)
    st.caption("The freshness score is a transparent heuristic based on claim statuses, not a probability that the answer is true.")
    for index, result in enumerate(results, start=1):
        render_result(result, index)
    st.markdown('<div class="section-kicker">03 · Export</div>', unsafe_allow_html=True)
    st.download_button("Download verification report  ↓", data=generate_pdf(results, freshness_score=score), file_name="Stale_Answer_Report.pdf", mime="application/pdf")

