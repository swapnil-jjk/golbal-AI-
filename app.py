import streamlit as st

from answer_verifier import ClaimVerificationError, verify_claim
from bifrost_client import ModelResponseError
from claim_extractor import ClaimExtractionError, extract_claims
from pdf_generator import generate_pdf
from web_research import research_claim

st.set_page_config(page_title="StaleAnswer AI", page_icon="✦", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --bg:#000000; --primary:#2D4F1F; --secondary:#F5E6CC; --accent:#E27D60; --neutral:#4A4A4A; }
html, body, [class*="css"] { font-family:'Manrope',sans-serif; color:var(--secondary); }
.stApp { background:var(--bg); } .block-container { max-width:1180px; padding:3rem 2rem 5rem; }
[data-testid="stHeader"] { background:transparent; } .eyebrow,.section-kicker,.metric-label { color:var(--accent); font-family:'DM Mono',monospace; text-transform:uppercase; letter-spacing:.14em; font-size:.7rem; }
h1 { color:var(--secondary)!important; font-size:clamp(2.4rem,6vw,5.4rem)!important; line-height:.98!important; letter-spacing:-.06em; max-width:760px; margin-bottom:1.25rem!important; } h2,h3 { color:var(--secondary)!important; }
.lede { color:#bfb5a5; font-size:1.08rem; line-height:1.65; max-width:630px; } .hero { border-bottom:1px solid #252525; padding:2rem 0 3.5rem; margin-bottom:2.5rem; } .hero-mark { color:var(--primary); font-size:4rem; line-height:1; margin-bottom:1.1rem; }
.metric-card { background:#111; border:1px solid #292929; border-radius:18px; padding:1.2rem 1.35rem; transition:all .2s ease; } .metric-card:hover { border-color:var(--primary); transform:translateY(-2px); } .metric-label { color:#9e968a; letter-spacing:.1em; } .metric-value { color:var(--secondary); font-size:2.15rem; font-weight:700; margin-top:.3rem; }
.status { display:inline-block; border-radius:999px; padding:.35rem .7rem; font-family:'DM Mono',monospace; font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; } .status-good { color:#b8d5a8; background:#183116; } .status-warn { color:#f2b09d; background:#3b2119; } .status-neutral { color:#c8c1b8; background:#292929; }
.section-kicker { margin:2rem 0 .7rem; } .stTextArea textarea { background:#0f0f0f!important; color:var(--secondary)!important; border:1px solid #333!important; border-radius:14px!important; padding:1rem!important; } .stTextArea textarea:focus { border-color:var(--primary)!important; box-shadow:0 0 0 1px var(--primary)!important; }
.stButton>button,.stDownloadButton>button { background:var(--primary)!important; color:var(--secondary)!important; border:1px solid #527a3e!important; border-radius:999px!important; padding:.7rem 1.4rem!important; font-weight:700!important; transition:all .2s ease; } .stButton>button:hover,.stDownloadButton>button:hover { background:#3a6828!important; transform:translateY(-1px); }
.stProgress>div>div>div>div { background:var(--primary); } [data-testid="stExpander"] { background:#111; border:1px solid #292929; border-radius:16px; } .source-link { color:#d6a08e; text-decoration:none; } .source-link:hover { color:var(--secondary); }
</style>
""", unsafe_allow_html=True)


def calculate_freshness_score(results):
    weights = {"Verified":100, "Potentially outdated":50, "Conflicting":0, "Unable to verify":25}
    return round(sum(weights.get(item.get("status"),25) for item in results)/len(results)) if results else 0


def status_class(status):
    if status == "Verified": return "status-good"
    if status in {"Potentially outdated", "Conflicting"}: return "status-warn"
    return "status-neutral"


st.markdown('<div class="hero"><div class="hero-mark">✦</div><div class="eyebrow">StaleAnswer AI · Evidence, not assumptions</div><h1>Find the claims that time forgot.</h1><p class="lede">Paste an AI-generated answer and turn uncertainty into a clear, source-backed freshness report.</p></div>', unsafe_allow_html=True)
answer = st.text_area("Your answer", height=230, label_visibility="collapsed", placeholder="Paste an AI-generated answer here…")
st.caption("Your answer is analyzed for factual claims, researched against the live web, and verified with your configured model.")

if st.button("Check answer  →", type="primary"):
    if not answer.strip():
        st.warning("Please enter an answer first.")
    else:
        results = []
        try:
            with st.spinner("Extracting factual claims…"): claims = extract_claims(answer)
            if not claims: st.warning("No factual claims were identified."); st.stop()
            st.markdown(f'<div class="section-kicker">Analysis in progress · {len(claims)} claims found</div>', unsafe_allow_html=True)
            for index, claim in enumerate(claims, start=1):
                with st.spinner(f"Researching claim {index} of {len(claims)}…"):
                    try: research = research_claim(claim)
                    except Exception as error: research = {"claim":claim, "sources":[], "error":str(error)}
                with st.spinner("Comparing evidence…"): verification = verify_claim(claim, research)
                verification["sources"] = research.get("sources", []); results.append(verification)
                status = verification.get("status", "Unable to verify")
                with st.expander(f"{index:02d}  ·  {claim}", expanded=True):
                    st.markdown(f'<span class="status {status_class(status)}">{status}</span>', unsafe_allow_html=True)
                    st.markdown("**Why this result**"); st.write(verification.get("explanation", "")); st.markdown("**Freshness note**"); st.write(verification.get("freshness_note", ""))
                    sources = research.get("sources", [])
                    if sources:
                        st.markdown("**Evidence**")
                        for source in sources:
                            st.markdown(f'<a class="source-link" href="{source.get("url", "#")}" target="_blank">↗ {source.get("title") or "Open source"}</a>', unsafe_allow_html=True)
                            if source.get("content"): st.caption(source["content"])
                    else: st.caption("No source evidence found.")
            score = calculate_freshness_score(results)
            st.markdown('<div class="section-kicker">Signal summary</div>', unsafe_allow_html=True)
            cols = st.columns(3)
            with cols[0]: st.markdown(f'<div class="metric-card"><div class="metric-label">Freshness score</div><div class="metric-value">{score}<span style="font-size:1rem;color:#9e968a"> / 100</span></div></div>', unsafe_allow_html=True)
            with cols[1]: st.markdown(f'<div class="metric-card"><div class="metric-label">Claims checked</div><div class="metric-value">{len(results)}</div></div>', unsafe_allow_html=True)
            with cols[2]: st.markdown(f'<div class="metric-card"><div class="metric-label">Verified</div><div class="metric-value">{sum(item.get("status")=="Verified" for item in results)}</div></div>', unsafe_allow_html=True)
            st.progress(score/100); st.caption("A heuristic based on verification statuses — not a probability that the answer is true.")
            st.download_button("Download verification report  ↓", data=generate_pdf(results, freshness_score=score), file_name="Stale_Answer_Report.pdf", mime="application/pdf")
            st.success("Verification completed.")
        except (ClaimExtractionError, ClaimVerificationError, ModelResponseError, RuntimeError, ValueError) as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"The verification workflow could not be completed ({type(error).__name__}). Check Bifrost and Tavily configuration.")

