"""
Public Track Record — @that_human_from_mars
============================================
Shareable on Instagram bio. No sensitive data.
Deploy at: track-record-thathumanfrommars.streamlit.app
"""
import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Track Record | @that_human_from_mars",
    page_icon="🏆",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  html,body,[class*="css"]{font-family:'Inter',sans-serif;}
  .main{background:#F8FAFC}
  .hero{background:linear-gradient(135deg,#0D1B2A 0%,#1A3A5C 100%);
        border-radius:20px;padding:36px 32px;color:white;text-align:center;margin-bottom:28px}
  .stat-card{background:white;border-radius:14px;padding:22px 16px;text-align:center;
             box-shadow:0 2px 8px rgba(0,0,0,0.08);height:100%}
  .stat-num{font-size:38px;font-weight:800;margin:6px 0}
  .stat-lbl{font-size:12px;color:#6B7280;font-weight:500;text-transform:uppercase;
            letter-spacing:0.5px}
  .call-row{background:white;border-radius:10px;padding:12px 16px;margin-bottom:8px;
            box-shadow:0 1px 4px rgba(0,0,0,0.06)}
  .section-title{font-size:20px;font-weight:700;color:#0D1B2A;margin:28px 0 16px}
  .pill{display:inline-block;padding:3px 12px;border-radius:999px;font-size:12px;font-weight:700}
  .avoid-box{background:#FFF3E0;border-left:4px solid #E65100;border-radius:0 8px 8px 0;
             padding:12px 16px;margin-bottom:8px}
  .methodology-box{background:#F0F9FF;border-left:3px solid #0EA5E9;border-radius:0 8px 8px 0;
                   padding:14px 18px;font-size:13px;line-height:1.7;color:#1E3A5F}
  .cta-box{background:linear-gradient(135deg,#833AB4,#FD1D1D,#F77737);
           border-radius:16px;padding:28px;color:white;text-align:center;margin-top:32px}
  footer{visibility:hidden}
  div[data-testid="stDecoration"]{display:none}
</style>
""", unsafe_allow_html=True)

# ── SEASON DATA ───────────────────────────────────────────────────────────────
SEASON = {
    "label":           "Q4 FY26 (Apr – May 2026)",
    "stocks_tracked":  292,
    "declared":        266,
    "buy_calls":       219,
    "winners":         219,
    "losers":          0,
    "avg_return_pct":  10.1,
    "beat_rate_pct":   82,
    "holding_days":    14,
}

TOP_CALLS = [
    ("SOLAR INDUSTRIES",   "BUY",        "+75.5%", "Defence explosives + Nagastra-1 drone"),
    ("PREMIER EXPLOSIVES", "BUY",        "+20.0%", "Ind-Ra upgrade + ₹1,271Cr order book"),
    ("MTAR TECHNOLOGIES",  "ACCUMULATE", "+16.7%", "ISRO/DRDO precision + Bloom Energy"),
    ("PRESTIGE ESTATES",   "ACCUMULATE", "+14.1%", "Pre-sales record ₹28,000Cr FY26"),
    ("BHARTI AIRTEL",      "STRONG BUY", "+10.6%", "5G subs 100M+, ARPU ₹245, Africa recovery"),
    ("CIPLA",              "BUY",        "+7.4%",  "US inhaler franchise, India branded +14%"),
    ("INDIAN HOTELS",      "BUY",        "+7.1%",  "Hospitality upcycle, Taj brand moat"),
    ("HCL TECHNOLOGIES",   "BUY",        "+6.5%",  "FY27 guidance best among Tier-1 IT"),
    ("CENTURY PLY",        "ACCUMULATE", "+12.5%", "All 3 segments firing simultaneously"),
]

AVOID_CALLS = [
    ("HPCL",         "REDUCE", "-6.5%",  "Govt-controlled pricing, GRM weak"),
    ("PVR INOX",     "HOLD",   "-6.5%",  "Content-driven beat, not structural"),
    ("JK TYRE",      "AVOID",  "-3.6%",  "High debt D/E ~1.5x, China tyre risk"),
    ("GOODLUCK INDIA","AVOID", "-2.7%",  "Complex promoter structure, 45 entities"),
    ("PRINCE PIPES",  "HOLD",  "-5.3%",  "EPS miss -82% vs estimate, margin credibility gone"),
]

SECTOR_BEATS = [
    ("Defence / Aerospace",    92, "11/12"),
    ("IT Services",            85, "6/7"),
    ("Healthcare / Pharma",    83, "10/12"),
    ("FMCG / Consumer Staples",80, "8/10"),
    ("Real Estate",            78, "7/9"),
    ("Industrials",            75, "6/8"),
    ("Auto Ancillary",         70, "7/10"),
    ("Metals & Steel",         40, "2/5"),
    ("Oil & Gas (PSU)",        30, "3/10"),
]

# ── HERO ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <div style="font-size:13px;color:#94A3B8;letter-spacing:3px;margin-bottom:12px">
    @THAT_HUMAN_FROM_MARS
  </div>
  <div style="font-size:34px;font-weight:800;margin-bottom:8px">
    My NSE Stock Call Track Record
  </div>
  <div style="font-size:15px;color:#94A3B8;margin-bottom:20px">
    CA | Independent Stock Research | Personal Finance Creator
  </div>
  <div style="display:inline-flex;gap:16px;flex-wrap:wrap;justify-content:center">
    <div style="background:rgba(255,255,255,0.1);border-radius:8px;padding:8px 20px">
      <b style="font-size:22px">{SEASON["buy_calls"]}</b>
      <div style="font-size:11px;color:#94A3B8">BUY Calls</div>
    </div>
    <div style="background:rgba(74,222,128,0.2);border-radius:8px;padding:8px 20px">
      <b style="font-size:22px;color:#4ADE80">100%</b>
      <div style="font-size:11px;color:#94A3B8">Hit Rate</div>
    </div>
    <div style="background:rgba(96,165,250,0.2);border-radius:8px;padding:8px 20px">
      <b style="font-size:22px;color:#60A5FA">+10.1%</b>
      <div style="font-size:11px;color:#94A3B8">Avg Return</div>
    </div>
    <div style="background:rgba(251,191,36,0.2);border-radius:8px;padding:8px 20px">
      <b style="font-size:22px;color:#FBBF24">14d</b>
      <div style="font-size:11px;color:#94A3B8">Avg Hold</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── SEASON STATS ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Season Overview — Q4 FY26</div>',
            unsafe_allow_html=True)

st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:24px">
  <div class="stat-card">
    <div class="stat-num" style="color:#2E5F8A">{SEASON['stocks_tracked']}</div>
    <div class="stat-lbl">STOCKS TRACKED</div>
  </div>
  <div class="stat-card">
    <div class="stat-num" style="color:#0D1B2A">{SEASON['declared']}</div>
    <div class="stat-lbl">RESULTS DECLARED</div>
  </div>
  <div class="stat-card">
    <div class="stat-num" style="color:#1B4332">+{SEASON['avg_return_pct']:.1f}%</div>
    <div class="stat-lbl">AVG RETURN</div>
  </div>
  <div class="stat-card">
    <div class="stat-num" style="color:#856404">{SEASON['beat_rate_pct']}%</div>
    <div class="stat-lbl">EPS BEAT RATE</div>
  </div>
  <div class="stat-card">
    <div class="stat-num" style="color:#7C3AED">{SEASON['holding_days']}d</div>
    <div class="stat-lbl">AVG HOLD PERIOD</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── TOP BUY CALLS ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🚀 Top BUY Calls — Q4 FY26</div>',
            unsafe_allow_html=True)
st.caption("Returns from recommendation date to results declaration (~14 day avg hold)")

for i, (name, rating, ret, thesis) in enumerate(TOP_CALLS, 1):
    color  = "#1B4332" if "+" in ret else "#C0392B"
    bg     = "#D8F3DC" if "+" in ret else "#FDDCDC"
    rat_bg = {"STRONG BUY":"#D8F3DC","BUY":"#D1FAE5","ACCUMULATE":"#E9F5EE"}.get(rating,"#F3F4F6")
    rat_col= {"STRONG BUY":"#1B4332","BUY":"#40916C","ACCUMULATE":"#2D6A4F"}.get(rating,"#374151")
    medal  = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"][i-1] if i<=9 else f"{i}."
    st.markdown(f"""
    <div class="call-row" style="border-left:4px solid {color}">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <span style="font-size:16px">{medal}</span>
          <b style="margin-left:8px;font-size:15px">{name}</b>
          <span style="background:{rat_bg};color:{rat_col};padding:2px 8px;
                       border-radius:999px;font-size:11px;font-weight:700;margin-left:8px">{rating}</span>
        </div>
        <span style="background:{bg};color:{color};padding:4px 14px;border-radius:999px;
                     font-size:16px;font-weight:800">{ret}</span>
      </div>
      <div style="font-size:12px;color:#6B7280;margin-top:4px;margin-left:24px">{thesis}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── REDUCE/AVOID CALLS ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">✅ REDUCE / AVOID Calls Vindicated</div>',
            unsafe_allow_html=True)
st.caption("Stocks I flagged as REDUCE or AVOID — all moved lower, protecting capital")

for name, rating, move, reason in AVOID_CALLS:
    rat_bg  = {"REDUCE":"#FFF3E0","AVOID":"#FDDCDC","HOLD":"#FFF3CD"}.get(rating,"#F3F4F6")
    rat_col = {"REDUCE":"#E65100","AVOID":"#C0392B","HOLD":"#856404"}.get(rating,"#374151")
    st.markdown(f"""
    <div class="avoid-box">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <b>{name}</b>
          <span style="background:{rat_bg};color:{rat_col};padding:2px 8px;
                       border-radius:999px;font-size:11px;font-weight:700;margin-left:8px">{rating}</span>
        </div>
        <span style="font-weight:800;color:#C0392B">{move} ✅</span>
      </div>
      <div style="font-size:12px;color:#6B7280;margin-top:4px">{reason}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── SECTOR BEAT RATE ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Sector Beat Rate — Q4 FY26</div>',
            unsafe_allow_html=True)
st.caption("% of companies in each sector that beat EPS estimates this quarter")

for sec, rate, fraction in SECTOR_BEATS:
    color = "#1B4332" if rate>=75 else "#856404" if rate>=50 else "#C0392B"
    bg    = "#D8F3DC" if rate>=75 else "#FFF3CD" if rate>=50 else "#FDDCDC"
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
      <div style="width:180px;font-size:13px;font-weight:500;flex-shrink:0">{sec}</div>
      <div style="flex:1;background:#E5E7EB;border-radius:999px;height:12px">
        <div style="background:{color};width:{rate}%;height:12px;border-radius:999px"></div>
      </div>
      <div style="width:90px;text-align:right">
        <span style="background:{bg};color:{color};padding:3px 10px;border-radius:4px;
                     font-size:12px;font-weight:700">{rate}% ({fraction})</span>
      </div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── METHODOLOGY ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📋 How I Pick Stocks</div>', unsafe_allow_html=True)
st.markdown("""
<div class="methodology-box">
  <b>My background:</b> Chartered Accountant with credit and due diligence experience at a major Indian bank.
  I analyse 292+ NSE-listed companies every results season (4x per year).<br><br>

  <b>What I rate:</b> STRONG BUY → BUY → ACCUMULATE → HOLD → REDUCE → AVOID<br><br>

  <b>What I look for:</b><br>
  ✅ EPS beat vs street estimates — by how much and why<br>
  ✅ Management guidance credibility — do they deliver what they promise<br>
  ✅ PE vs growth rate — am I paying fair value<br>
  ✅ Balance sheet quality — debt levels, cash flow, ROCE<br>
  ✅ Sector tailwinds — structural vs cyclical growth<br>
  ✅ Contrarian calls — where my view differs from sell-side consensus<br><br>

  <b>Returns shown:</b> From recommendation date to results declaration (~14 day avg).
  Not compounded annual returns — short-term results-season momentum tracking.<br><br>

  ⚠️ <b>Important:</b> This is educational content. I am not a SEBI-registered investment advisor.
  Past returns do not guarantee future performance. Always consult a registered advisor before investing.
</div>
""", unsafe_allow_html=True)

# ── DISCLAIMER ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="background:#FFF3CD;border-left:4px solid #F59E0B;border-radius:0 8px 8px 0;
            padding:12px 16px;font-size:12px;color:#856404;margin-bottom:24px">
  ⚠️ <b>Disclaimer:</b> All content is for educational purposes only. I am not a SEBI-registered
  investment advisor. Returns shown are hypothetical based on recommendation date prices and may not
  reflect actual returns. Invest at your own risk after conducting your own research.
</div>
""", unsafe_allow_html=True)

# ── CTA ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="cta-box">
  <div style="font-size:22px;font-weight:800;margin-bottom:8px">
    Follow for Weekly Stock Analysis
  </div>
  <div style="font-size:15px;opacity:0.9;margin-bottom:16px">
    @that_human_from_mars on Instagram<br>
    Every results season — 292+ stocks tracked, independent ratings, no fluff
  </div>
  <div style="font-size:13px;opacity:0.7">
    Updated: {datetime.now().strftime("%d %b %Y")} &nbsp;|&nbsp; Q4 FY26 Season
  </div>
</div>
""", unsafe_allow_html=True)
