"""
NSE Results Watchlist — Streamlit Dashboard v3
Features: Results Today, Score Ranking, News, Portfolio Sim,
Peer Compare, PDF Export, Dark Mode, Progress Bar,
Track Record, Instagram Export
"""

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, date
from collections import Counter
import time, math, io, urllib.parse, re
from data import STOCKS, TICKER_MAP, RATING_COLORS, RATING_BG, RISK_BG

# ── Dark mode toggle (persisted in session) ───────────────────────────────────
if "dark" not in st.session_state:
    st.session_state.dark = False

st.set_page_config(
    page_title="NSE Watchlist | Q4 FY26",
    page_icon="📊", layout="wide",
    initial_sidebar_state="collapsed",
)

# ── PASSWORD PROTECTION ───────────────────────────────────────────────────────


D = st.session_state.dark
BG   = "#0D1B2A"   if D else "#F8FAFC"
CARD = "#1A3A5C"   if D else "#FFFFFF"
TEXT = "#F0F0F0"   if D else "#111827"
SUB  = "#94A3B8"   if D else "#6B7280"
BDR  = "#2E5F8A"   if D else "#E5E7EB"

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html,body,[class*="css"]{{font-family:'Inter',sans-serif;}}
  .main{{background:{BG}!important;}}
  .stMetric{{background:{CARD};border-radius:12px;padding:16px;
             box-shadow:0 1px 4px rgba(0,0,0,0.12);color:{TEXT}}}
  .stMetric label{{font-size:12px!important;color:{SUB}}}
  h1,h2,h3{{color:{TEXT}}}
  h2{{border-bottom:2px solid {BDR};padding-bottom:6px}}
  .commentary-box{{background:{'#1E3A5C' if D else '#F0F9FF'};
    border-left:3px solid #0EA5E9;padding:12px 16px;border-radius:0 8px 8px 0;
    font-size:13px;color:{TEXT};line-height:1.6}}
  .action-card{{background:{'#2D2010' if D else '#FFF9F0'};
    border-left:4px solid #F59E0B;padding:14px 18px;border-radius:0 10px 10px 0;margin-bottom:10px}}
  .today-banner{{background:linear-gradient(135deg,#1B4332,#40916C);
    border-radius:12px;padding:16px 20px;margin-bottom:16px;color:white}}
  .score-badge{{display:inline-block;width:36px;height:36px;border-radius:50%;
    text-align:center;line-height:36px;font-weight:700;font-size:15px}}
  .progress-season{{background:{'#1A3A5C' if D else '#EEF4FB'};
    border-radius:8px;padding:12px 16px;margin-bottom:12px}}
  .insta-card{{background:linear-gradient(135deg,#833AB4,#FD1D1D,#F77737);
    border-radius:16px;padding:20px;color:white;margin-bottom:12px}}
  div[data-testid="stExpander"]{{border:1px solid {BDR};border-radius:8px}}
  footer{{visibility:hidden}}
  @media(max-width:768px){{
    section[data-testid="stSidebar"]{{width:85vw!important}}
    .stMetric{{padding:10px}}
  }}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 NSE Watchlist\n**Q4 FY26**")
    st.caption(f"that_human_from_mars | {datetime.now().strftime('%d %b %Y')}")
    if st.toggle("🌙 Dark Mode", value=st.session_state.dark):
        st.session_state.dark = True; st.rerun()
    else:
        st.session_state.dark = False
    st.divider()
    page = st.radio("Navigate",[
        "🏠 Dashboard","🗓 Results Calendar","📈 Pre-Result Setup",
        "🎯 Post-Result Tracker","💰 Returns Tracker","🏆 Track Record",
        "🔬 Stock Deep Dive","📸 Instagram Export","⚙️ Live Prices",
    ])
    st.divider()
    st.markdown("**Filters**")
    status_filter = st.multiselect("Status",["Declared","Pending"],
                                    default=["Declared","Pending"])
    rating_filter = st.multiselect("My Rating",
        ["STRONG BUY","BUY","ACCUMULATE","HOLD","HOLD / BOOK","REDUCE","AVOID"],
        default=["STRONG BUY","BUY","ACCUMULATE","HOLD","HOLD / BOOK","REDUCE","AVOID"])
    st.divider()
    st.caption("⚠️ Personal tracking tool. Not SEBI-registered investment advice.")

# ── Helpers ───────────────────────────────────────────────────────────────────
def fs():
    return [s for s in STOCKS
            if s["status"] in status_filter and s["ind_rating"] in rating_filter]

def rb(r,sz=12):
    bg=RATING_BG.get(r,"#F3F4F6"); col=RATING_COLORS.get(r,"#374151")
    return f'<span style="background:{bg};color:{col};font-weight:700;padding:2px 10px;border-radius:999px;font-size:{sz}px">{r}</span>'

def parse_date(ds):
    if not ds: return None
    clean=str(ds).replace(" ✅","").replace(" ⏳","").strip()
    for fmt in ["%d-%b-%y","%d-%b-%Y","%d-%m-%Y"]:
        try: return datetime.strptime(clean,fmt).date()
        except: pass
    return None

def watchlist_score(s):
    """Composite score 1-10 for each stock."""
    score = 0
    # Rating (0-4)
    score += {"STRONG BUY":4,"BUY":3,"ACCUMULATE":2,"HOLD":1,"REDUCE":0,"AVOID":0}.get(s["ind_rating"],1)
    # Risk (0-2)
    score += {"LOW":2,"LOW-MEDIUM":1.5,"MEDIUM":1,"HIGH":0}.get(s["risk"],1)
    # Beat history (0-2)
    if s.get("act_eps") and s.get("est_eps") and s["est_eps"]!=0:
        beat=(s["act_eps"]-s["est_eps"])/abs(s["est_eps"])*100
        score += 2 if beat>10 else (1 if beat>0 else 0)
    elif s["status"]=="Pending":
        score += 1  # neutral for pending
    # Upside captured (0-2)
    score += {"YES":2,"PARTIAL":1,"NO":0}.get(s.get("upside_captured",""),0)
    return min(round(score,1), 10)

def share_text(s):
    eps_line=""
    if s.get("act_eps") and s.get("est_eps"):
        b=(s["act_eps"]-s["est_eps"])/abs(s["est_eps"])*100
        eps_line=f"EPS: ₹{s['act_eps']} ({b:+.1f}% {'✅ BEAT' if b>0 else '❌ MISS'})\n"
    return (f"📊 *{s['name']}* | {s.get('quarter','Q4 FY26')}\n"
            f"Sector: {s['sector']}\n"
            f"Result: {s['result_date']} | {s['status']}\n"
            f"{eps_line}"
            f"My Rating: *{s['ind_rating']}* | Risk: {s['risk']}\n"
            f"{s['ind_rationale'][:120]}...\n\n"
            f"📌 {s.get('catalyst','')[:100]}\n\n"
            f"🔗 https://nse-watchlist-thathumanfrommars.streamlit.app")

def pe_warning(pe):
    try: pe = int(pe) if pe else None
    except: pe = None
    if pe is None: return "", ""
    if pe > 55:   return "🔴", f"{pe}x — Very expensive. Any miss = sharp fall."
    if pe > 35:   return "⚠️", f"{pe}x — Expensive. Needs strong growth delivery."
    if pe > 20:   return "🟡", f"{pe}x — Fairly valued."
    return "✅", f"{pe}x — Reasonable valuation."

def pe_badge(pe):
    try: pe = int(pe) if pe else None
    except: pe = None
    if pe is None: return ""
    if pe > 55:   bg,col,label = "FDDCDC","C0392B",f"🔴 {pe}x VERY EXP"
    elif pe > 35: bg,col,label = "FFF3E0","E65100",f"⚠️ {pe}x EXPENSIVE"
    elif pe > 20: bg,col,label = "FFF3CD","856404",f"🟡 {pe}x FAIR"
    else:         bg,col,label = "D8F3DC","1B4332",f"✅ {pe}x CHEAP"
    return f'<span style="background:#{bg};color:#{col};padding:2px 10px;border-radius:999px;font-size:11px;font-weight:700">{label}</span>'

def upside_pct(ss_target, cmp=None):
    """Calculate remaining upside from ss_target vs CMP or last known price."""
    if not ss_target: return None, ""
    # Use a stored CMP map (approximate last known prices as of May 2026)
    CMP_MAP = {
        "GRASIM":3103,"GAIL":192,"PRESTIGE":1620,"RAINBOW CHILDCARE":1250,
        "BALKRISNA IND":2208,"JSW STEEL":980,"ASHOK LEYLAND":186,
        "NARAYANA HRUDAY":1250,"GLENMARK PHARMA":1320,"LINDE INDIA":8200,
        "SUZLON":58,"JK TYRE":318,"ASTRA MICROWAVE":715,"BHARAT RASAYAN":8200,
        "GOODLUCK INDIA":798,"KEI INDUSTRIES":4548,"ASTRAL":1850,
        "JINDAL SAW":320,"PFC":412,"CESC":145,"IRCON INTL":185,
        "BPCL":308,"INDIAMART":7200,"IREDA":188,"COCHIN SHIPYARD":1548,
        "MFSL":900,"POLYCAB":9465,"HUDCO":185,"VBL":485,
        "PRINCE PIPES":265,"CENTURY PLY":720,"HAVELLS":1510,"PVR INOX":1290,
        "SYRMA SGS":1188,"PERSISTENT":5600,"OBEROI REALTY":1850,
        "INDIAN HOTELS":675,"JSW INFRA":380,"NRB BEARING":390,
        "PREMIER EXPLOSIVES":714,"BHARTI AIRTEL":1902,"TATA MOTORS":730,
        "TATA STEEL":158,"CIPLA":1590,"DR REDDY'S":1380,
        "DIXON TECHNOLOGIES":11200,"TATA POWER":415,"HAL":5100,
        "DLF":875,"CANARA BANK":110,"HPCL":318,"SOLAR INDUSTRIES":17900,
        "MTAR TECHNOLOGIES":2100,"POWER GRID":318,"OIL INDIA":490,
        "PREMIER ENERGIES":820,"SAIL":110,"UNO MINDA":950,
        "KEC INTERNATIONAL":1020,"DEEPAK NITRITE":2050,"TORRENT POWER":1780,
        "TITAN":4600,"PIDILITE":3050,"GODREJ CONSUMER":1390,
        "PAGE INDUSTRIES":46000,"VOLTAS":1400,"SUN PHARMA":1890,
        "EICHER MOTORS":5050,"ITC":430,"COLGATE":2800,"HINDALCO":680,
        "DIVI'S LABS":5200,"ASIAN PAINTS":2200,"ONGC":245,
        "CUMMINS INDIA":3350,"ABB INDIA":5200,"BERGER PAINTS":495,
        "BRITANNIA":5450,"GODREJ PROPERTIES":2620,"DABUR":575,
        "MARICO":668,"IPCA LABS":1580,"INFO EDGE":7650,
        "FORTIS HEALTHCARE":610,"VARROC ENGINEERING":580,
        "SIEMENS":6600,"BAJAJ FINANCE":9200,"BAJAJ FINSERV":2000,
        "AXIS BANK":1180,"TECH MAHINDRA":1620,"HCL TECHNOLOGIES":1750,
        "SBI LIFE":1680,"HDFC LIFE":720,"BHARAT ELECTRONICS":320,
        "MAX HEALTHCARE":1080,"INTERGLOBE AVIATION":5200,
        "SHRIRAM FINANCE":680,"MACROTECH DEV":1500,"ULTRATECH CEMENT":11800,
        "TRENT":6800,"MARUTI SUZUKI":12800,"ULTRATECH CEMENT":11800,
    }
    if cmp:
        price = cmp
    else:
        # Try to get from stock name passed in
        price = CMP_MAP.get(ss_target, None)
        return None, ""
    upside = (ss_target - price) / price * 100
    if upside > 20:   color, icon = "#1B4332", "🟢"
    elif upside > 5:  color, icon = "#2D6A4F", "🟡"
    elif upside > -5: color, icon = "#856404", "⚪"
    else:             color, icon = "#C0392B", "🔴"
    return upside, f'<span style="color:{color};font-weight:700">{icon} {upside:+.1f}%</span>'

def stock_upside(s):
    """Get upside % for a stock using stored CMP map."""
    CMP_MAP = {
        "GRASIM":3103,"GAIL":192,"PRESTIGE":1620,"RAINBOW CHILDCARE":1250,
        "BALKRISNA IND":2208,"JSW STEEL":980,"ASHOK LEYLAND":186,
        "NARAYANA HRUDAY":1250,"GLENMARK PHARMA":1320,"LINDE INDIA":8200,
        "SUZLON":58,"JK TYRE":318,"ASTRA MICROWAVE":715,
        "GOODLUCK INDIA":798,"KEI INDUSTRIES":4548,"ASTRAL":1850,
        "JINDAL SAW":320,"PFC":412,"CESC":145,"IRCON INTL":185,
        "BPCL":308,"INDIAMART":7200,"IREDA":188,"COCHIN SHIPYARD":1548,
        "MFSL":900,"POLYCAB":9465,"HUDCO":185,"VBL":485,
        "PRINCE PIPES":265,"CENTURY PLY":720,"HAVELLS":1510,"PVR INOX":1290,
        "SYRMA SGS":1188,"PERSISTENT":5600,"OBEROI REALTY":1850,
        "INDIAN HOTELS":675,"JSW INFRA":380,"NRB BEARING":390,
        "PREMIER EXPLOSIVES":714,"BHARTI AIRTEL":1902,"TATA MOTORS":730,
        "TATA STEEL":158,"CIPLA":1590,"DR REDDY'S":1380,
        "DIXON TECHNOLOGIES":11200,"TATA POWER":415,"HAL":5100,
        "DLF":875,"CANARA BANK":110,"HPCL":318,"SOLAR INDUSTRIES":17900,
        "MTAR TECHNOLOGIES":2100,"POWER GRID":318,"OIL INDIA":490,
        "PREMIER ENERGIES":820,"SAIL":110,"UNO MINDA":950,
        "KEC INTERNATIONAL":1020,"DEEPAK NITRITE":2050,"TORRENT POWER":1780,
        "TITAN":4600,"PIDILITE":3050,"GODREJ CONSUMER":1390,
        "PAGE INDUSTRIES":46000,"VOLTAS":1400,"SUN PHARMA":1890,
        "EICHER MOTORS":5050,"ITC":430,"COLGATE":2800,"HINDALCO":680,
        "DIVI'S LABS":5200,"ASIAN PAINTS":2200,"ONGC":245,
        "CUMMINS INDIA":3350,"ABB INDIA":5200,"BERGER PAINTS":495,
        "BRITANNIA":5450,"GODREJ PROPERTIES":2620,"DABUR":575,
        "MARICO":668,"IPCA LABS":1580,"INFO EDGE":7650,
        "FORTIS HEALTHCARE":610,"VARROC ENGINEERING":580,
        "SIEMENS":6600,"BAJAJ FINANCE":9200,"BAJAJ FINSERV":2000,
        "AXIS BANK":1180,"TECH MAHINDRA":1620,"HCL TECHNOLOGIES":1750,
        "SBI LIFE":1680,"HDFC LIFE":720,"BHARAT ELECTRONICS":320,
        "MAX HEALTHCARE":1080,"INTERGLOBE AVIATION":5200,
        "SHRIRAM FINANCE":680,"MACROTECH DEV":1500,
        "TRENT":6800,"MARUTI SUZUKI":12800,"ULTRATECH CEMENT":11800,
    }
    target = s.get("ss_target")
    cmp    = CMP_MAP.get(s["name"])
    if not target or not cmp: return None, "—"
    upside = (target - cmp) / cmp * 100
    if upside > 20:   icon = "🟢"
    elif upside > 5:  icon = "🟡"
    elif upside > -5: icon = "⚪"
    else:             icon = "🔴"
    return upside, f"{icon} {upside:+.1f}%"


def is_market_open():
    """Check if NSE market is currently open."""
    now = datetime.now()
    if now.weekday() >= 5: return False  # Weekend
    market_open  = now.replace(hour=9,  minute=15, second=0)
    market_close = now.replace(hour=15, minute=30, second=0)
    return market_open <= now <= market_close

def market_status_badge():
    if is_market_open():
        return '<span style="background:#D8F3DC;color:#1B4332;padding:3px 12px;border-radius:999px;font-size:12px;font-weight:700">🟢 Market Open</span>'
    return '<span style="background:#FDDCDC;color:#C0392B;padding:3px 12px;border-radius:999px;font-size:12px;font-weight:700">🔴 Market Closed</span>'

def contrarian_flag(s):
    """Flag stocks where my rating diverges from sell-side consensus."""
    ss = s.get("ss_rating","")
    me = s.get("ind_rating","")
    if ss in ("BUY","STRONG BUY") and me in ("REDUCE","AVOID"):
        return "🔴 Contrarian BEAR"
    if ss in ("SELL","REDUCE") and me in ("BUY","STRONG BUY","ACCUMULATE"):
        return "🟢 Contrarian BULL"
    return ""


TODAY = date.today()

# Returns data
RETURNS_DATA = [
    ("PERSISTENT","STRONG BUY","23-Apr-26",5300,5600),
    ("KEI INDUSTRIES","STRONG BUY","04-May-26",4250,4548),
    ("POLYCAB","STRONG BUY","06-May-26",8800,9465),
    ("BHARTI AIRTEL","BUY","13-May-26",1720,1902),
    ("CIPLA","BUY","13-May-26",1480,1590),
    ("INDIAN HOTELS","BUY","11-May-26",630,675),
    ("TATA POWER","BUY","12-May-26",385,415),
    ("SOLAR INDUSTRIES","BUY","15-May-26",10200,17900),
    ("SYRMA SGS","BUY","11-May-26",1100,1188),
    ("COCHIN SHIPYARD","BUY","21-May-26",1532,1548),
    ("PREMIER ENERGIES","BUY","15-May-26",740,820),
    ("UNO MINDA","BUY","16-May-26",860,950),
    ("PREMIER EXPLOSIVES","BUY","25-May-26",595,714),
    ("PIDILITE","BUY","07-May-26",2800,3050),
    ("SUN PHARMA","BUY","22-May-26",1750,1890),
    ("MARICO","BUY","07-May-26",620,668),
    ("DIVI'S LABS","BUY","23-May-26",4800,5200),
    ("CUMMINS INDIA","BUY","22-May-26",3100,3350),
    ("GAIL","ACCUMULATE","21-May-26",175,192),
    ("PRESTIGE","ACCUMULATE","21-May-26",1420,1620),
    ("NARAYANA HRUDAY","ACCUMULATE","22-May-26",1180,1250),
    ("BALKRISNA IND","ACCUMULATE","23-May-26",2200,2208),
    ("PFC","ACCUMULATE","21-May-26",370,412),
    ("IREDA","ACCUMULATE","21-May-26",168,188),
    ("VBL","ACCUMULATE","27-Apr-26",460,485),
    ("CENTURY PLY","ACCUMULATE","22-May-26",640,720),
    ("HAVELLS","ACCUMULATE","22-Apr-26",1350,1510),
    ("OBEROI REALTY","ACCUMULATE","08-May-26",1700,1850),
    ("NRB BEARING","ACCUMULATE","07-May-26",360,390),
    ("TATA MOTORS","ACCUMULATE","13-May-26",680,730),
    ("DR REDDY'S","ACCUMULATE","12-May-26",1260,1380),
    ("DIXON TECHNOLOGIES","ACCUMULATE","12-May-26",10200,11200),
    ("HAL","ACCUMULATE","14-May-26",4700,5100),
    ("DLF","ACCUMULATE","13-May-26",790,875),
    ("POWER GRID","ACCUMULATE","15-May-26",295,318),
    ("KEC INTERNATIONAL","ACCUMULATE","16-May-26",940,1020),
    ("TORRENT POWER","ACCUMULATE","13-May-26",1640,1780),
    ("MTAR TECHNOLOGIES","ACCUMULATE","12-May-26",1800,2100),
    ("TITAN","ACCUMULATE","08-May-26",4219,4600),
    ("GODREJ CONSUMER","ACCUMULATE","06-May-26",1300,1390),
    ("BERGER PAINTS","ACCUMULATE","06-May-26",460,495),
    ("BRITANNIA","ACCUMULATE","07-May-26",5200,5450),
    ("GODREJ PROPERTIES","ACCUMULATE","06-May-26",2400,2620),
    ("DABUR","ACCUMULATE","07-May-26",540,575),
    ("INFO EDGE","ACCUMULATE","22-May-26",7200,7650),
    ("FORTIS HEALTHCARE","ACCUMULATE","22-May-26",580,610),
    ("PAGE INDUSTRIES","ACCUMULATE","21-May-26",43000,46000),
    ("EICHER MOTORS","ACCUMULATE","22-May-26",4700,5050),
    ("GLENMARK PHARMA","REDUCE","21-May-26",1350,1320),
    ("JSW STEEL","REDUCE","21-May-26",950,980),
    ("BPCL","REDUCE","21-May-26",295,308),
    ("JK TYRE","AVOID","21-May-26",330,318),
    ("GOODLUCK INDIA","AVOID","21-May-26",820,798),
    ("PRINCE PIPES","HOLD","20-May-26",280,265),
    ("HPCL","REDUCE","13-May-26",340,318),
    ("PVR INOX","HOLD","11-May-26",1380,1290),
]

# Dedup returns data
seen_r=set(); RD=[]
for row in RETURNS_DATA:
    if row[0] not in seen_r:
        seen_r.add(row[0]); RD.append(row)

def get_returns():
    rows=[]
    for name,rating,rec_str,rec_p,today_p in RD:
        try: rec_d=datetime.strptime(rec_str,"%d-%b-%y").date()
        except: rec_d=datetime.strptime(rec_str,"%d-%b-%Y").date()
        days=max((TODAY-rec_d).days,1)
        ret=(today_p-rec_p)/rec_p
        rows.append({"name":name,"rating":rating,"rec_date":rec_str,
                     "rec_price":rec_p,"today_price":today_p,
                     "ret_pct":ret,"curr_val":100000*(1+ret),
                     "pnl":100000*ret,"days":days})
    return rows

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
if page == "🏠 Dashboard":
    st.markdown("# 📊 NSE Results Watchlist — Q4 FY26")
    st.caption(f"that_human_from_mars's personal tracker | {len(STOCKS)} stocks | {datetime.now().strftime('%d %b %Y %H:%M')}")

    declared=[s for s in STOCKS if s["status"]=="Declared"]
    pending =[s for s in STOCKS if s["status"]=="Pending"]
    beats   =[s for s in declared if s.get("act_eps") and s.get("est_eps") and s["act_eps"]>s["est_eps"]]
    misses  =[s for s in declared if s.get("act_eps") and s.get("est_eps") and s["act_eps"]<s["est_eps"]]
    captured=[s for s in declared if s.get("upside_captured")=="YES"]
    strong  =[s for s in STOCKS if s["ind_rating"] in ("STRONG BUY","BUY")]

    # ── #8 Season progress bar ────────────────────────────────────────────────
    prog=len(declared)/len(STOCKS)
    st.markdown(f"""
    <div class="progress-season">
      <b>Q4 FY26 Season Progress</b> — {len(declared)} of {len(STOCKS)} results declared ({prog*100:.0f}%)
      <div style="background:#ddd;border-radius:999px;height:10px;margin-top:8px">
        <div style="background:linear-gradient(90deg,#40916C,#1B4332);width:{prog*100:.0f}%;
                    height:10px;border-radius:999px"></div>
      </div>
      <small style="color:{SUB}">{len(pending)} results still pending | Beat rate: {len(beats)}/{len(declared)} = {len(beats)/max(len(declared),1)*100:.0f}%</small>
    </div>""", unsafe_allow_html=True)

    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric("Total Tracked",f"{len(STOCKS)}")
    c2.metric("Declared",f"{len(declared)}")
    c3.metric("Pending",f"{len(pending)}")
    c4.metric("Beats / Misses",f"{len(beats)} / {len(misses)}")
    c5.metric("Upside Captured",f"{len(captured)}")
    c6.metric("BUY / STRONG BUY",f"{len(strong)}")

    st.markdown("---")

    # ── #1 Results Today / Tomorrow ───────────────────────────────────────────
    results_today=[]; results_tmrw=[]
    for s in STOCKS:
        d=parse_date(s.get("result_date",""))
        if not d: continue
        if d==TODAY: results_today.append(s)
        elif (d-TODAY).days==1: results_tmrw.append(s)

    if results_today:
        st.markdown(f"""
        <div class="today-banner">
          <b>🔔 RESULTS TODAY — {TODAY.strftime('%d %b %Y')}</b><br>
          {"  |  ".join(f"<b>{s['name']}</b> (Est. EPS ₹{s.get('est_eps',0):.2f})" for s in results_today)}
        </div>""", unsafe_allow_html=True)

    if results_tmrw:
        st.info(f"📅 **Tomorrow's Results:** " +
                " | ".join(f"**{s['name']}** (Est. ₹{s.get('est_eps',0):.2f})" for s in results_tmrw))

    # ── #2 Action Required ────────────────────────────────────────────────────
    needs_action=[]
    for s in declared:
        d=parse_date(s.get("result_date",""))
        if d and (TODAY-d).days<=3 and (
            "Auto-added" in str(s.get("earnings_commentary","")) or
            "Results pending" in str(s.get("earnings_commentary","")) or
            s.get("upside_captured") is None
        ):
            needs_action.append(s)

    if needs_action:
        st.markdown("### 🚨 Action Required")
        for s in needs_action:
            col=RATING_COLORS.get(s["ind_rating"],"#856404")
            bg_=RATING_BG.get(s["ind_rating"],"#FFF3CD")
            eps_str=""
            if s.get("act_eps") and s.get("est_eps") and s["est_eps"]!=0:
                b=(s["act_eps"]-s["est_eps"])/abs(s["est_eps"])*100
                eps_str=f"  |  EPS {'✅ +' if b>0 else '❌ '}{abs(b):.1f}%"
            st.markdown(f"""
            <div class="action-card">
              <b>{s['name']}</b> — {s['result_date']}{eps_str}<br>
              <span style="background:{bg_};color:{col};padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700">{s['ind_rating']}</span>
              <span style="font-size:12px;color:{SUB};margin-left:8px">⚠ Update commentary + upside_captured on GitHub</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("---")
    else:
        st.success("✅ All recent declarations updated.")

    col_a,col_b=st.columns([1,1])
    with col_a:
        st.markdown("### ⚖️ Rating Distribution")
        dist=Counter(s["ind_rating"] for s in STOCKS)
        order=["STRONG BUY","BUY","ACCUMULATE","HOLD","HOLD / BOOK","REDUCE","AVOID"]
        rows=[{"Rating":r,"Count":dist[r],
               "Stocks":", ".join(s["name"] for s in STOCKS if s["ind_rating"]==r)}
              for r in order if r in dist]
        df_d=pd.DataFrame(rows)
        def cr_(v): return f"background-color:{RATING_BG.get(v,'#F3F4F6')};color:{RATING_COLORS.get(v,'#374151')};font-weight:600"
        st.dataframe(df_d.style.map(cr_,subset=["Rating"]),
                     use_container_width=True, hide_index=True, height=280)

    with col_b:
        # ── #3 Beat rate by sector ────────────────────────────────────────────
        st.markdown("### 📊 Sector Beat Rate")
        sb={}
        for s in declared:
            if s.get("act_eps") and s.get("est_eps"):
                sec=s["sector"].split("(")[0].strip().split("/")[0].strip()[:22]
                sb.setdefault(sec,{"beats":0,"total":0})
                sb[sec]["total"]+=1
                if s["act_eps"]>s["est_eps"]: sb[sec]["beats"]+=1
        sec_rows=[{"Sector":k,"Stocks":v["total"],"Beats":v["beats"],
                   "Beat Rate":f"{v['beats']/v['total']*100:.0f}%"}
                  for k,v in sorted(sb.items(),key=lambda x:-x[1]["beats"]/max(x[1]["total"],1))]
        if sec_rows:
            df_sb=pd.DataFrame(sec_rows)
            def cbr(v):
                try:
                    n=float(v.replace("%",""))
                    if n>=80: return "background-color:#D8F3DC;color:#1B4332;font-weight:700"
                    elif n>=50: return "background-color:#FFF3CD;color:#856404;font-weight:700"
                    else: return "background-color:#FDDCDC;color:#C0392B;font-weight:700"
                except: return ""
            st.dataframe(df_sb.style.map(cbr,subset=["Beat Rate"]),
                         use_container_width=True, hide_index=True, height=280)

    st.info("⚠️ Independent ratings are personal assessments — not SEBI-registered research.")

# ─────────────────────────────────────────────────────────────────────────────
# RESULTS CALENDAR
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🗓 Results Calendar":
    st.markdown("## 🗓 Results Calendar — Q4 FY26")
    fstocks=fs()

    # #2 Watchlist score column
    rows=[]
    for s in fstocks:
        eps_beat=None
        if s.get("act_eps") and s.get("est_eps") and s["est_eps"]!=0:
            eps_beat=(s["act_eps"]-s["est_eps"])/abs(s["est_eps"])*100
        target = s.get("ss_target")
        upside_pct = None  # Will be fetched live — shown as target for now
        rows.append({
            "Score":f"{watchlist_score(s):.1f}/10",
            "Company":s["name"],"Sector":s["sector"][:22],
            "Result Date":s["result_date"],"Status":s["status"],
            "Est. EPS":s.get("est_eps"),"Act. EPS":s.get("act_eps") or "Pending",
            "Beat %":f"{eps_beat:+.1f}%" if eps_beat is not None else "—",
            "SS Target":f"₹{target:,}" if target else "—",
            "My Rating":s["ind_rating"],"Risk":s["risk"],
            "PE":pe_badge(s.get("pe_ratio")),
        })
    df=pd.DataFrame(rows)
    def cs(v):
        return "background-color:#D8F3DC;color:#1B4332;font-weight:600" if v=="Declared" else "background-color:#FFF3CD;color:#856404;font-weight:600"
    def cr(v): return f"background-color:{RATING_BG.get(v,'#F3F4F6')};color:{RATING_COLORS.get(v,'#374151')};font-weight:600"
    def cb(v):
        if v=="—": return ""
        try:
            n=float(v.replace("%","").replace("+",""))
            return "background-color:#D8F3DC;color:#1B4332" if n>0 else "background-color:#FDDCDC;color:#C0392B"
        except: return ""
    def csc(v):
        try:
            n=float(v.split("/")[0])
            if n>=7: return "background-color:#D8F3DC;color:#1B4332;font-weight:700"
            elif n>=5: return "background-color:#FFF3CD;color:#856404;font-weight:700"
            else: return "background-color:#FDDCDC;color:#C0392B;font-weight:700"
        except: return ""
    def cup(v):
        if "🟢" in str(v): return "color:#1B4332;font-weight:700"
        elif "🟡" in str(v): return "color:#856404;font-weight:700"
        elif "🔴" in str(v): return "color:#C0392B;font-weight:700"
        return ""
    st.dataframe(df.style.map(cs,subset=["Status"]).map(cr,subset=["My Rating"])
                 .map(cb,subset=["Beat %"]).map(csc,subset=["Score"]),
                 use_container_width=True, hide_index=True, height=700)
    st.caption(f"Showing {len(fstocks)} stocks | Score = composite conviction (1-10)")

# ─────────────────────────────────────────────────────────────────────────────
# PRE-RESULT SETUP
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📈 Pre-Result Setup":
    st.markdown("## 📈 Pre-Result Setup")
    pending_s=sorted([s for s in fs() if s["status"]=="Pending"],
                     key=lambda x: parse_date(x.get("result_date","")) or date(2099,1,1))
    st.caption(f"{len(pending_s)} pending | sorted by result date")
    for s in pending_s:
        rat_bg=RATING_BG.get(s["ind_rating"],"#F3F4F6")
        rat_col=RATING_COLORS.get(s["ind_rating"],"#374151")
        d=parse_date(s.get("result_date",""))
        days_str=f" — 🔔 {(d-TODAY).days}d away" if d and d>=TODAY else ""
        score=watchlist_score(s)
        with st.expander(f"**{s['name']}** | 📅 {s['result_date']}{days_str} | Score: {score}/10"):
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Est. EPS",(f"₹{s['est_eps']:.2f}" if isinstance(s.get('est_eps'),(int,float)) else '₹—'))
            c2.metric("Est. Rev",f"₹{s.get('est_rev','—'):,}Cr" if s.get('est_rev') else "—")
            c3.metric("SS Target",f"₹{s.get('ss_target','—')}")
            c4.metric("Score",f"{score}/10")
            rat_bg  = RATING_BG.get(s["ind_rating"],"#F3F4F6")
            rat_col = RATING_COLORS.get(s["ind_rating"],"#374151")
            st.markdown(f'<span style="background:{rat_bg};color:{rat_col};font-weight:700;padding:4px 14px;border-radius:999px;font-size:13px">MY RATING: {s["ind_rating"]}</span> ' + pe_badge(s.get("pe_ratio")), unsafe_allow_html=True)
            st.markdown("**📌 Catalyst**")
            st.markdown(f'<div class="commentary-box">{s.get("catalyst","—")}</div>', unsafe_allow_html=True)
            st.markdown("**🔍 Rationale**")
            st.markdown(f'<div class="commentary-box" style="background:{"#1E2D10" if D else "#FFF9F0"};border-color:#F59E0B">{s.get("ind_rationale","—")}</div>', unsafe_allow_html=True)
            st.markdown("**📋 What to Watch**")
            st.markdown(f'<div class="commentary-box" style="background:{"#1A1040" if D else "#F8F0FF"};border-color:#8B5CF6">{s.get("earnings_commentary","—")}</div>', unsafe_allow_html=True)
            wa_url="https://wa.me/?text="+urllib.parse.quote(share_text(s))
            st.markdown(f'<a href="{wa_url}" target="_blank" style="background:#25D366;color:white;padding:7px 18px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:600;display:inline-block;margin-top:8px">📲 Share on WhatsApp</a>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# POST-RESULT TRACKER
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🎯 Post-Result Tracker":
    st.markdown("## 🎯 Post-Result Tracker")
    dec=sorted([s for s in fs() if s["status"]=="Declared"],
               key=lambda x: parse_date(x.get("result_date","")) or date(2020,1,1), reverse=True)
    st.caption(f"{len(dec)} results declared | latest first")
    for s in dec:
        eps_b=None
        if s.get("act_eps") and s.get("est_eps") and s["est_eps"]!=0:
            eps_b=(s["act_eps"]-s["est_eps"])/abs(s["est_eps"])*100
        rev_b=None
        if s.get("act_rev") and s.get("est_rev") and s["est_rev"]!=0:
            rev_b=(s["act_rev"]-s["est_rev"])/abs(s["est_rev"])*100
        eps_str = f"₹{s['act_eps']:.2f}" if isinstance(s.get('act_eps'),(int,float)) else "₹—"
        label=(f"**{s['name']}** | {s['result_date']} | "
               f"EPS {eps_str} "
               f"({'✅ BEAT' if eps_b and eps_b>0 else '❌ MISS'} {f'{eps_b:+.1f}%' if eps_b else ''})")
        with st.expander(label):
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("Est. EPS",(f"₹{s['est_eps']:.2f}" if isinstance(s.get('est_eps'),(int,float)) else '₹—'))
            c2.metric("Act. EPS",(f"₹{s['act_eps']:.2f}" if isinstance(s.get('act_eps'),(int,float)) else '₹—'),f"{eps_b:+.1f}%" if eps_b else None)
            c3.metric("Est. Rev",f"₹{s.get('est_rev','—'):,}Cr" if s.get('est_rev') else "—")
            c4.metric("Act. Rev",f"₹{s.get('act_rev','—'):,}Cr" if s.get('act_rev') else "—",f"{rev_b:+.1f}%" if rev_b else None)
            c5.metric("Upside",s.get("upside_captured") or "—")
            st.markdown(rb(s["ind_rating"],13) + "  " + pe_badge(s.get("pe_ratio")), unsafe_allow_html=True)
            # Before vs After card
            if eps_b is not None:
                beat_icon = "✅ BEAT" if eps_b > 0 else "❌ MISS"
                beat_color = "#1B4332" if eps_b > 0 else "#C0392B"
                beat_bg    = "#D8F3DC" if eps_b > 0 else "#FDDCDC"
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0">
                  <div style="background:#F0F9FF;border-radius:10px;padding:14px;border:1px solid #BAE6FD">
                    <div style="font-size:11px;color:#0369A1;font-weight:600;margin-bottom:6px">📌 PRE-RESULT VIEW</div>
                    <div style="font-weight:700">{s["ind_rating"]}</div>
                    <div style="font-size:12px;color:#555;margin-top:4px">Est. EPS: {"₹"+f"{s['est_eps']:.2f}" if isinstance(s.get("est_eps"),(int,float)) else "—"}</div>
                    <div style="font-size:12px;color:#555">Target: {"₹"+f"{s['ss_target']:,}" if s.get("ss_target") else "—"}</div>
                  </div>
                  <div style="background:{beat_bg};border-radius:10px;padding:14px;border:1px solid {beat_color}40">
                    <div style="font-size:11px;color:{beat_color};font-weight:600;margin-bottom:6px">📊 ACTUAL RESULT</div>
                    <div style="font-weight:700;color:{beat_color}">{beat_icon} {eps_b:+.1f}%</div>
                    <div style="font-size:12px;color:#555;margin-top:4px">Act. EPS: {"₹"+f"{s['act_eps']:.2f}" if isinstance(s.get("act_eps"),(int,float)) else "—"}</div>
                    <div style="font-size:12px;color:#555">Upside: {stock_upside(s)[1]}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

            st.markdown("**📢 Earnings Commentary**")
            st.markdown(f'<div class="commentary-box">{s.get("earnings_commentary","—")}</div>', unsafe_allow_html=True)
            st.markdown("**⚖️ Independent View**")
            st.markdown(f'<div class="commentary-box" style="background:{"#1E2D10" if D else "#FFF9F0"};border-color:#F59E0B">{s.get("ind_rationale","—")}</div>', unsafe_allow_html=True)
            wa_url="https://wa.me/?text="+urllib.parse.quote(share_text(s))
            st.markdown(f'<a href="{wa_url}" target="_blank" style="background:#25D366;color:white;padding:7px 18px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:600;display:inline-block;margin-top:8px">📲 Share on WhatsApp</a>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# RETURNS TRACKER
# ─────────────────────────────────────────────────────────────────────────────
elif page == "💰 Returns Tracker":
    st.markdown("## 💰 Returns Tracker — ₹1 Lakh per BUY Call")
    st.caption("Rec price = approx CMP on recommendation date. Today = 28-May-2026.")

    # #4 Portfolio Simulator
    st.markdown("### ⚙️ Portfolio Simulator")
    sim_col1,sim_col2=st.columns(2)
    with sim_col1:
        portfolio_size=st.number_input("Your portfolio size (₹)",min_value=10000,
                                        max_value=10000000,value=500000,step=50000)
    with sim_col2:
        allocation_mode=st.selectbox("Allocation mode",
            ["Equal weight (same ₹ each)","Top 5 BUY only","Top 10 by score"])

    inv_per_stock=portfolio_size/5 if allocation_mode=="Top 5 BUY only" else \
                  portfolio_size/10 if allocation_mode=="Top 10 by score" else \
                  portfolio_size/len(RD)

    rows_ret=get_returns()
    if allocation_mode=="Top 5 BUY only":
        rows_ret=sorted([r for r in rows_ret if r["rating"] in ("STRONG BUY","BUY")],
                         key=lambda x:-x["ret_pct"])[:5]
    elif allocation_mode=="Top 10 by score":
        rows_ret=sorted(rows_ret,key=lambda x:-x["ret_pct"])[:10]

    total_inv=len(rows_ret)*inv_per_stock
    total_val=sum(r["curr_val"]/100000*inv_per_stock for r in rows_ret)
    total_ret=(total_val-total_inv)/total_inv

    buy_rows=[r for r in rows_ret if r["rating"] in ("STRONG BUY","BUY","ACCUMULATE")]
    winners=sum(1 for r in buy_rows if r["ret_pct"]>=0)
    hit_rate=winners/max(len(buy_rows),1)*100

    k1,k2,k3,k4,k5=st.columns(5)
    k1.metric("Deployed",f"₹{total_inv/100000:.1f}L")
    k2.metric("Value Today",f"₹{total_val/100000:.1f}L")
    k3.metric("P&L",f"₹{(total_val-total_inv)/100000:.1f}L",f"{total_ret*100:+.1f}%")
    k4.metric("Hit Rate",f"{hit_rate:.0f}%")
    k5.metric("Stocks",f"{len(rows_ret)}")

    st.markdown("---")
    rows_r_disp=sorted(rows_ret,key=lambda x:-x["ret_pct"])
    df_disp=pd.DataFrame([{
        "Stock":r["name"],"Rating":r["rating"],"Rec. Date":r["rec_date"],
        "Rec. Price":f"₹{r['rec_price']:,}","Today":f"₹{r['today_price']:,}",
        "Return %":f"{r['ret_pct']*100:+.1f}%",
        "P&L":f"₹{r['pnl']/100000*inv_per_stock:+,.0f}",
        "Days":r["days"],
    } for r in rows_r_disp])
    def cret(v):
        if "+" in str(v): return "background-color:#D8F3DC;color:#1B4332;font-weight:700"
        elif "-" in str(v): return "background-color:#FDDCDC;color:#C0392B;font-weight:700"
        return ""
    def crat(v): return f"background-color:{RATING_BG.get(v,'#F3F4F6')};color:{RATING_COLORS.get(v,'#374151')};font-weight:600"
    st.dataframe(df_disp.style.map(cret,subset=["Return %","P&L"]).map(crat,subset=["Rating"]),
                 use_container_width=True, hide_index=True, height=600)

# ─────────────────────────────────────────────────────────────────────────────
# #9 TRACK RECORD
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🏆 Track Record":
    st.markdown("## 🏆 Track Record — Q4 FY26 Results Season")
    st.caption("Performance summary of all calls made this season.")

    rows_ret=get_returns()
    buy_rows=[r for r in rows_ret if r["rating"] in ("STRONG BUY","BUY","ACCUMULATE")]
    reduce_rows=[r for r in rows_ret if r["rating"] in ("REDUCE","AVOID")]

    total_buy_inv=len(buy_rows)*100000
    total_buy_val=sum(r["curr_val"] for r in buy_rows)
    buy_ret=(total_buy_val-total_buy_inv)/total_buy_inv
    winners=sum(1 for r in buy_rows if r["ret_pct"]>=0)
    losers=sum(1 for r in buy_rows if r["ret_pct"]<0)

    # Reduce/Avoid saved money (negative return = good for reduce calls)
    avoid_saved=sum(abs(r["pnl"]) for r in reduce_rows if r["ret_pct"]<0)

    # Season stats
    best=max(buy_rows,key=lambda x:x["ret_pct"]) if buy_rows else None
    worst=min(buy_rows,key=lambda x:x["ret_pct"]) if buy_rows else None
    avg_days=sum(r["days"] for r in buy_rows)/max(len(buy_rows),1)

    st.markdown("### 📊 Season Summary — Q4 FY26 (Apr–May 2026)")
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric("BUY Calls Made",f"{len(buy_rows)}")
    c2.metric("Winners",f"{winners}",f"{winners/max(len(buy_rows),1)*100:.0f}% hit rate")
    c3.metric("Losers",f"{losers}")
    c4.metric("Portfolio Return",f"{buy_ret*100:+.1f}%")
    c5.metric("Avg Hold Period",f"{avg_days:.0f} days")
    c6.metric("Avoid Calls Saved",f"₹{avoid_saved/100000:.1f}L")

    st.markdown("---")

    col_a,col_b=st.columns(2)
    with col_a:
        st.markdown("### 🏅 Top 5 Calls")
        top5=sorted(buy_rows,key=lambda x:-x["ret_pct"])[:5]
        for i,r in enumerate(top5,1):
            medal=["🥇","🥈","🥉","4️⃣","5️⃣"][i-1]
            st.markdown(f"""
            <div style="background:{CARD};border-radius:8px;padding:10px 14px;
                        margin-bottom:8px;border-left:4px solid #40916C">
              {medal} <b>{r['name']}</b>
              <span style="background:#D8F3DC;color:#1B4332;padding:2px 8px;
                           border-radius:4px;font-weight:700;font-size:12px;margin-left:8px">
                {r['ret_pct']*100:+.1f}%
              </span>
              <span style="color:{SUB};font-size:12px;margin-left:8px">{r['rating']} | {r['days']}d</span>
            </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown("### ⚠️ Calls to Review")
        bottom=sorted(buy_rows,key=lambda x:x["ret_pct"])[:5]
        for r in bottom:
            color="#C0392B" if r["ret_pct"]<0 else "#856404"
            bg_="#FDDCDC" if r["ret_pct"]<0 else "#FFF3CD"
            st.markdown(f"""
            <div style="background:{CARD};border-radius:8px;padding:10px 14px;
                        margin-bottom:8px;border-left:4px solid {color}">
              <b>{r['name']}</b>
              <span style="background:{bg_};color:{color};padding:2px 8px;
                           border-radius:4px;font-weight:700;font-size:12px;margin-left:8px">
                {r['ret_pct']*100:+.1f}%
              </span>
              <span style="color:{SUB};font-size:12px;margin-left:8px">{r['rating']} | {r['days']}d</span>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📈 Rating Performance Breakdown")
    rat_perf={}
    for r in rows_ret:
        rat=r["rating"]
        rat_perf.setdefault(rat,{"count":0,"wins":0,"total_ret":0})
        rat_perf[rat]["count"]+=1
        rat_perf[rat]["total_ret"]+=r["ret_pct"]
        if r["ret_pct"]>=0: rat_perf[rat]["wins"]+=1

    perf_rows=[]
    for rat in ["STRONG BUY","BUY","ACCUMULATE","HOLD","REDUCE","AVOID"]:
        if rat in rat_perf:
            d=rat_perf[rat]
            avg_r=d["total_ret"]/d["count"]*100
            hit=d["wins"]/d["count"]*100
            perf_rows.append({"Rating":rat,"Calls":d["count"],
                               "Avg Return":f"{avg_r:+.1f}%","Hit Rate":f"{hit:.0f}%"})
    if perf_rows:
        df_p=pd.DataFrame(perf_rows)
        def cpr(v): return f"background-color:{RATING_BG.get(v,'#F3F4F6')};color:{RATING_COLORS.get(v,'#374151')};font-weight:600"
        def cav(v):
            if "+" in str(v): return "background-color:#D8F3DC;color:#1B4332;font-weight:700"
            elif "-" in str(v): return "background-color:#FDDCDC;color:#C0392B;font-weight:700"
            return ""
        st.dataframe(df_p.style.map(cpr,subset=["Rating"]).map(cav,subset=["Avg Return"]),
                     use_container_width=True, hide_index=True)


    st.markdown("---")
    st.markdown("### 🔄 Sector Rotation Tracker")
    st.caption("Which sectors beat estimates — builds across seasons for pattern recognition")

    from collections import defaultdict
    sector_data = defaultdict(lambda: {"beats":0,"total":0})
    declared_all = [s for s in STOCKS if s["status"]=="Declared"]
    for s in declared_all:
        if s.get("act_eps") and s.get("est_eps"):
            sec = s["sector"].split("(")[0].strip().split("/")[0].strip()[:20]
            sector_data[sec]["total"] += 1
            if s["act_eps"] > s["est_eps"]: sector_data[sec]["beats"] += 1

    sec_sorted = sorted(sector_data.items(),
                        key=lambda x: x[1]["beats"]/max(x[1]["total"],1), reverse=True)

    for sec, d in sec_sorted:
        rate  = d["beats"]/d["total"]*100
        color = "#1B4332" if rate>=75 else "#856404" if rate>=50 else "#C0392B"
        bg    = "#D8F3DC" if rate>=75 else "#FFF3CD" if rate>=50 else "#FDDCDC"
        bar   = int(rate)
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
          <div style="width:160px;font-size:12px;font-weight:500;flex-shrink:0">{sec}</div>
          <div style="flex:1;background:#E5E7EB;border-radius:999px;height:10px">
            <div style="background:{color};width:{bar}%;height:10px;border-radius:999px"></div>
          </div>
          <div style="width:80px;text-align:right">
            <span style="background:{bg};color:{color};padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700">{rate:.0f}%</span>
          </div>
          <div style="width:60px;font-size:11px;color:#6B7280">{d["beats"]}/{d["total"]}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔍 Contrarian Calls")
    st.caption("Stocks where my rating diverges significantly from sell-side consensus")
    contrarians = [(s, contrarian_flag(s)) for s in STOCKS if contrarian_flag(s)]
    if contrarians:
        for s, flag in contrarians:
            rat_bg_ = RATING_BG.get(s["ind_rating"],"#F3F4F6")
            rat_col_= RATING_COLORS.get(s["ind_rating"],"#374151")
            color_  = "#C0392B" if "BEAR" in flag else "#1B4332"
            st.markdown(f"""
            <div style="background:white;border-radius:8px;padding:10px 16px;margin-bottom:6px;
                        border-left:4px solid {color_};box-shadow:0 1px 3px rgba(0,0,0,0.06)">
              <b>{s["name"]}</b> &nbsp;
              <span style="background:{rat_bg_};color:{rat_col_};padding:1px 8px;border-radius:999px;font-size:11px;font-weight:700">{s["ind_rating"]}</span>
              &nbsp;vs SS: <b>{s.get("ss_rating","—")}</b> &nbsp;
              <span style="float:right;font-weight:700;color:{color_}">{flag}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No strong contrarian divergences currently.")

    st.markdown("---")
    st.markdown("""
    > **Note:** This is Q4 FY26 season data only (Apr–May 2026).
    > Track record builds automatically as you use this across Q1 FY27, Q2 FY27, Q3 FY27 seasons.
    > Over 4+ seasons this becomes a genuine edge — hit rate and avg return per season become meaningful.
    """)

# ─────────────────────────────────────────────────────────────────────────────
# STOCK DEEP DIVE  (with #5 Peer Comparison + #3 News)
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🔬 Stock Deep Dive":
    st.markdown("## 🔬 Stock Deep Dive")
    selected=st.selectbox("Select Stock",[s["name"] for s in STOCKS])
    s=next(x for x in STOCKS if x["name"]==selected)
    rat_bg=RATING_BG.get(s["ind_rating"],"#F3F4F6")
    rat_col=RATING_COLORS.get(s["ind_rating"],"#374151")

    col1,col2=st.columns([2,1])
    with col1:
        st.markdown(f"### {s['name']}")
        st.caption(f"{s['sector']}  |  📅 {s['result_date']}  |  Score: {watchlist_score(s)}/10")
        st.markdown(f"""
        <div style="margin:8px 0">
          <span style="background:{'#D8F3DC' if s['status']=='Declared' else '#FFF3CD'};
                color:{'#1B4332' if s['status']=='Declared' else '#856404'};
                font-weight:700;padding:3px 12px;border-radius:999px;font-size:12px">
            {'✅ Declared' if s['status']=='Declared' else '⏳ Pending'}
          </span>
          <span style="background:{rat_bg};color:{rat_col};font-weight:700;
                padding:3px 14px;border-radius:999px;font-size:13px;margin-left:8px">
            {s['ind_rating']}
          </span>
        </div>""", unsafe_allow_html=True)

    with col2:
        ticker=TICKER_MAP.get(s["name"])
        if ticker and st.button("🔄 Fetch Live Price",type="primary"):
            with st.spinner("Fetching..."):
                try:
                    info=yf.Ticker(ticker).info
                    price=info.get("currentPrice") or info.get("regularMarketPrice")
                    chg=info.get("regularMarketChangePercent",0)
                    w52h=info.get("fiftyTwoWeekHigh"); w52l=info.get("fiftyTwoWeekLow")
                    pe=info.get("trailingPE")
                    st.metric("Live CMP",f"₹{price:,.2f}" if price else "N/A",
                              f"{chg:+.2f}%" if chg else None)
                    if w52h and w52l and price and w52h!=w52l:
                        pct=(price-w52l)/(w52h-w52l)
                        st.progress(pct,text=f"52W: ₹{w52l:,} ◄ ₹{price:,.0f} ► ₹{w52h:,}")
                    if pe: st.caption(f"P/E: {pe:.1f}x")
                except Exception as e:
                    st.error(f"Failed: {e}")

    st.divider()
    col_a,col_b=st.columns(2)
    with col_a:
        st.markdown("#### 📊 Estimates vs Actuals")
        dr=[("Est. EPS",(f"₹{s['est_eps']:.2f}" if isinstance(s.get('est_eps'),(int,float)) else '₹—')),
            ("Actual EPS",(f"₹{s['act_eps']:.2f}" if isinstance(s.get('act_eps'),(int,float)) else '₹—') if s.get('act_eps') else "Pending"),
            ("Est. Rev",f"₹{s.get('est_rev','—'):,}Cr" if s.get('est_rev') else "—"),
            ("Actual Rev",f"₹{s.get('act_rev','—'):,}Cr" if s.get('act_rev') else "Pending"),
            ("Sell-Side Target",f"₹{s.get('ss_target','—')}"),
            ("Sell-Side",s.get("ss_rating","—"))]
        if s.get("act_eps") and s.get("est_eps"):
            b=(s["act_eps"]-s["est_eps"])/abs(s["est_eps"])*100
            dr.insert(2,("EPS Beat/Miss",f"{b:+.1f}%"))
        st.dataframe(pd.DataFrame(dr,columns=["Metric","Value"]),
                     use_container_width=True, hide_index=True)

    with col_b:
        st.markdown("#### 🎯 My Assessment")
        pe_val  = s.get("pe_ratio", "—")
        pe_flag = pe_warning(s.get("pe_ratio"))[0] if s.get("pe_ratio") else ""
        st.markdown(f"""| | |
|--|--|
| Rating | **{s['ind_rating']}** |
| Risk | **{s['risk']}** |
| Score | **{watchlist_score(s)}/10** |
| P/E | **{pe_val}x** {pe_flag} |
| Upside Captured | **{s.get('upside_captured') or '—'}** |""")
    # PE warning box
    pe = s.get("pe_ratio")
    if pe and pe > 35:
        flag, msg = pe_warning(pe)
        warn_color = "#C0392B" if pe > 55 else "#E65100"
        warn_bg    = "#FDDCDC" if pe > 55 else "#FFF3E0"
        st.markdown(
            f'<div style="background:{warn_bg};border-left:4px solid {warn_color};'
            f'padding:10px 14px;border-radius:0 8px 8px 0;margin-top:8px">'
            f'<b>{flag} PE Warning:</b> {msg}<br>'
            f'<small style="color:#666">High PE stocks need perfect execution. '
            f'Any earnings miss causes sharp corrections.</small>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("#### 📢 Earnings Commentary")
    st.markdown(f'<div class="commentary-box">{s.get("earnings_commentary","—")}</div>', unsafe_allow_html=True)
    st.markdown("#### 🔍 Rationale")
    st.markdown(f'<div class="commentary-box" style="background:{"#1E2D10" if D else "#FFF9F0"};border-color:#F59E0B">{s.get("ind_rationale","—")}</div>', unsafe_allow_html=True)
    st.markdown("#### 💡 Catalyst")
    st.markdown(f'<div class="commentary-box" style="background:{"#0D2010" if D else "#F0FDF4"};border-color:#22C55E">{s.get("catalyst","—")}</div>', unsafe_allow_html=True)

    # ── #3 Live News ──────────────────────────────────────────────────────────
    ticker=TICKER_MAP.get(s["name"])
    if ticker and st.button("📰 Load Latest News"):
        with st.spinner("Fetching news..."):
            try:
                t=yf.Ticker(ticker)
                news=t.news or []
                if news:
                    st.markdown("#### 📰 Latest News")
                    for n in news[:5]:
                        title=n.get("title","")
                        link=n.get("link","#")
                        publisher=n.get("publisher","")
                        pub_time=datetime.fromtimestamp(n.get("providerPublishTime",0)).strftime("%d-%b %H:%M") if n.get("providerPublishTime") else ""
                        st.markdown(f"• [{title}]({link}) — *{publisher}* {pub_time}")
                else:
                    st.info("No recent news found.")
            except Exception as e:
                st.warning(f"News fetch failed: {e}")

    # ── #5 Peer Comparison ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔍 Peer Comparison")
    sector_peers=[x for x in STOCKS
                  if x["sector"].split("(")[0].strip().split("/")[0].strip()[:15] ==
                     s["sector"].split("(")[0].strip().split("/")[0].strip()[:15]
                  and x["name"]!=s["name"]][:3]
    if sector_peers:
        cols=st.columns(len(sector_peers))
        for i,peer in enumerate(sector_peers):
            with cols[i]:
                beat=""
                if peer.get("act_eps") and peer.get("est_eps") and peer["est_eps"]!=0:
                    b=(peer["act_eps"]-peer["est_eps"])/peer["est_eps"]*100
                    beat=f"EPS {b:+.1f}%"
                bg_=RATING_BG.get(peer["ind_rating"],"#F3F4F6")
                col_=RATING_COLORS.get(peer["ind_rating"],"#374151")
                st.markdown(f"""
                <div style="background:{CARD};border-radius:8px;padding:12px;text-align:center;border:1px solid {BDR}">
                  <b>{peer['name']}</b><br>
                  <span style="background:{bg_};color:{col_};padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700">{peer['ind_rating']}</span><br>
                  <small style="color:{SUB}">{beat or peer['status']}</small>
                </div>""", unsafe_allow_html=True)
    else:
        st.caption("No sector peers found in watchlist.")

    st.markdown("---")
    st.markdown("#### 🧮 Position Sizing Calculator")
    ps_col1, ps_col2 = st.columns(2)
    with ps_col1:
        invest_amt = st.number_input("Amount to invest (₹)", min_value=1000,
                                      max_value=10000000, value=100000, step=10000,
                                      key=f"ps_{s['name']}")
    with ps_col2:
        cmp_input = st.number_input("CMP (₹)", min_value=1.0, value=float(
            next((v for k,v in [
                ("PERSISTENT",5600),("POLYCAB",9465),("KEI INDUSTRIES",4548),
                ("BHARTI AIRTEL",1902),("CIPLA",1590),("INDIAN HOTELS",675),
                ("TATA POWER",415),("SOLAR INDUSTRIES",17900),("SYRMA SGS",1188),
            ] if k==s["name"]), 1000)), step=1.0, key=f"cmp_{s['name']}")

    target = s.get("ss_target")
    if target and cmp_input > 0:
        shares    = int(invest_amt / cmp_input)
        cost      = shares * cmp_input
        target_val= shares * target
        upside_val= target_val - cost
        stop_loss = cmp_input * 0.90
        sl_val    = shares * stop_loss
        sl_loss   = sl_val - cost
        rr_ratio  = upside_val / abs(sl_loss) if sl_loss != 0 else 0

        k1,k2,k3,k4 = st.columns(4)
        k1.metric("Shares",      f"{shares:,}")
        k2.metric("Total Cost",  f"₹{cost:,.0f}")
        k3.metric("At Target",   f"₹{target_val:,.0f}", f"₹{upside_val:+,.0f}")
        k4.metric("At -10% SL",  f"₹{sl_val:,.0f}",    f"₹{sl_loss:+,.0f}")

        rr_color = "#1B4332" if rr_ratio >= 2 else "#856404" if rr_ratio >= 1 else "#C0392B"
        st.markdown(f"""
        <div style="background:#F8FAFC;border-radius:8px;padding:12px 16px;margin-top:8px;
                    border-left:4px solid {rr_color}">
          <b>Risk:Reward = 1:{rr_ratio:.1f}</b>
          {'✅ Good setup (>1:2)' if rr_ratio>=2 else '⚠️ Acceptable (1:1 to 1:2)' if rr_ratio>=1 else '❌ Poor risk-reward (<1:1)'}
          &nbsp;|&nbsp; Stop Loss at ₹{stop_loss:,.2f} (10% below CMP)
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    wa_url="https://wa.me/?text="+urllib.parse.quote(share_text(s))
    st.markdown(f'<a href="{wa_url}" target="_blank" style="background:#25D366;color:white;padding:9px 22px;border-radius:6px;text-decoration:none;font-size:14px;font-weight:600">📲 Share on WhatsApp</a>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 📸 INSTAGRAM EXPORT
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📸 Instagram Export":
    st.markdown("## 📸 Instagram Export")
    st.caption("One-click cards for @that_human_from_mars")

    import streamlit.components.v1 as components

    declared=[s for s in STOCKS if s["status"]=="Declared"]
    beats=[s for s in declared if s.get("act_eps") and s.get("est_eps") and s["act_eps"]>s["est_eps"]]
    rows_ret=get_returns()
    buy_rows=[r for r in rows_ret if r["rating"] in ("STRONG BUY","BUY","ACCUMULATE")]
    top5=sorted(buy_rows,key=lambda x:-x["ret_pct"])[:5]
    portfolio_ret=sum(r["ret_pct"] for r in buy_rows)/max(len(buy_rows),1)*100
    hit_rate=sum(1 for r in buy_rows if r["ret_pct"]>=0)/max(len(buy_rows),1)*100

    # ── Card 1: Season Scorecard ─────────────────────────────────────────────
    st.markdown("### 🏆 Season Scorecard")
    components.html(f"""
    <div style="background:linear-gradient(135deg,#0D1B2A 0%,#1A3A5C 100%);
                border-radius:20px;padding:32px;color:white;max-width:480px;font-family:Arial,sans-serif">
      <div style="font-size:12px;color:#94A3B8;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">
        @that_human_from_mars | Q4 FY26
      </div>
      <div style="font-size:24px;font-weight:700;margin-bottom:20px">My Results Season Report 📊</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px">
        <div style="background:rgba(255,255,255,0.08);border-radius:12px;padding:14px;text-align:center">
          <div style="font-size:30px;font-weight:700;color:#4ADE80">{portfolio_ret:+.1f}%</div>
          <div style="font-size:11px;color:#94A3B8">Avg Portfolio Return</div>
        </div>
        <div style="background:rgba(255,255,255,0.08);border-radius:12px;padding:14px;text-align:center">
          <div style="font-size:30px;font-weight:700;color:#60A5FA">{hit_rate:.0f}%</div>
          <div style="font-size:11px;color:#94A3B8">Hit Rate</div>
        </div>
        <div style="background:rgba(255,255,255,0.08);border-radius:12px;padding:14px;text-align:center">
          <div style="font-size:30px;font-weight:700;color:#F472B6">{len(declared)}</div>
          <div style="font-size:11px;color:#94A3B8">Results Tracked</div>
        </div>
        <div style="background:rgba(255,255,255,0.08);border-radius:12px;padding:14px;text-align:center">
          <div style="font-size:30px;font-weight:700;color:#FBBF24">{len(beats)}/{len(declared)}</div>
          <div style="font-size:11px;color:#94A3B8">Beat Estimates</div>
        </div>
      </div>
      <div style="background:rgba(64,145,108,0.25);border-radius:10px;padding:14px;margin-bottom:14px">
        <div style="font-size:11px;color:#4ADE80;font-weight:600;margin-bottom:4px">🏆 BEST CALL THIS SEASON</div>
        <div style="font-size:18px;font-weight:700">{top5[0]["name"] if top5 else "—"}</div>
        <div style="font-size:22px;font-weight:700;color:#4ADE80">{top5[0]["ret_pct"]*100:+.1f}%</div>
      </div>
      <div style="font-size:10px;color:#64748B;text-align:center">⚠️ Not SEBI-registered advice. Educational only.</div>
    </div>
    """, height=420, scrolling=False)

    best_name = top5[0]['name'].replace(' ','') if top5 else '—'
    best_ret  = f"{top5[0]['ret_pct']*100:+.1f}%" if top5 else '—'
    caption1 = (f"📊 Q4 FY26 Season Report\n\n"
                f"✅ {len(declared)} results tracked\n"
                f"📈 Avg return: {portfolio_ret:+.1f}% in ~4 weeks\n"
                f"🎯 Hit rate: {hit_rate:.0f}%\n"
                f"🏆 Best call: #{(top5[0]['name'] if top5 else '').replace(' ','')} {best_ret}\n\n"
                f"Full analysis 👇 nse-watchlist-thathumanfrommars.streamlit.app\n\n"
                f"#StockMarket #NSE #Q4Results #PersonalFinance #IndianStocks #thathumanfrommars")
    st.code(caption1, language=None)
    st.markdown("👆 Copy caption above | Screenshot the card | Post on Instagram")

    st.markdown("---")

    # ── Card 2: Top BUY Calls ─────────────────────────────────────────────────
    st.markdown("### 🚀 Top BUY Calls")
    top8 = sorted(buy_rows, key=lambda x: -x["ret_pct"])[:8]
    rows_html = "".join(f"""
      <div style="display:flex;justify-content:space-between;align-items:center;
                  padding:9px 0;border-bottom:1px solid rgba(255,255,255,0.08)">
        <div><span style="font-weight:600;font-size:13px">{r["name"]}</span>
             <span style="font-size:10px;color:#94A3B8;margin-left:6px">{r["rating"]}</span></div>
        <span style="font-weight:700;font-size:16px;color:{"#4ADE80" if r["ret_pct"]>=0 else "#F87171"}">{r["ret_pct"]*100:+.1f}%</span>
      </div>""" for r in top8)

    components.html(f"""
    <div style="background:linear-gradient(135deg,#0D1B2A,#1A3A5C);
                border-radius:20px;padding:26px;color:white;max-width:480px;font-family:Arial,sans-serif">
      <div style="font-size:12px;color:#94A3B8;margin-bottom:6px">@that_human_from_mars | Q4 FY26</div>
      <div style="font-size:22px;font-weight:700;margin-bottom:4px">Top BUY Calls 🚀</div>
      <div style="font-size:12px;color:#94A3B8;margin-bottom:16px">Returns since recommendation</div>
      {rows_html}
      <div style="font-size:10px;color:#64748B;margin-top:14px;text-align:center">⚠️ Past returns ≠ future performance</div>
    </div>
    """, height=480, scrolling=False)

    caption2 = ("🚀 My Top BUY Calls — Q4 FY26\n\n"
                + "\n".join(f"{'✅' if r['ret_pct']>=0 else '❌'} #{r['name'].replace(' ','')}: {r['ret_pct']*100:+.1f}%" for r in top8)
                + f"\n\nHit rate: {hit_rate:.0f}% | ~4 week hold\n"
                f"nse-watchlist-thathumanfrommars.streamlit.app\n\n"
                f"#NSEIndia #StockMarket #ResultsSeason #IndianStocks #thathumanfrommars")
    st.code(caption2, language=None)
    st.markdown("👆 Copy caption above | Screenshot the card | Post on Instagram")

    st.markdown("---")

    # ── Card 3: Sector Beat Rate ──────────────────────────────────────────────
    st.markdown("### 📊 Sector Beat Rate")
    sb={}
    for s in declared:
        if s.get("act_eps") and s.get("est_eps"):
            sec=s["sector"].split("(")[0].strip().split("/")[0].strip()[:20]
            sb.setdefault(sec,{"beats":0,"total":0})
            sb[sec]["total"]+=1
            if s["act_eps"]>s["est_eps"]: sb[sec]["beats"]+=1
    top_s=sorted(sb.items(),key=lambda x:-x[1]["beats"]/max(x[1]["total"],1))[:6]
    sec_html="".join(f"""
      <div style="margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;margin-bottom:3px">
          <span style="font-size:12px;font-weight:500">{sec}</span>
          <span style="font-size:12px;font-weight:700;color:{"#4ADE80" if d["beats"]/d["total"]>=0.7 else "#FBBF24" if d["beats"]/d["total"]>=0.5 else "#F87171"}">{d["beats"]/d["total"]*100:.0f}%</span>
        </div>
        <div style="background:rgba(255,255,255,0.1);border-radius:999px;height:7px">
          <div style="background:{"#4ADE80" if d["beats"]/d["total"]>=0.7 else "#FBBF24" if d["beats"]/d["total"]>=0.5 else "#F87171"};width:{d["beats"]/d["total"]*100:.0f}%;height:7px;border-radius:999px"></div>
        </div>
        <span style="font-size:10px;color:#94A3B8">{d["beats"]}/{d["total"]} beat</span>
      </div>""" for sec,d in top_s)

    components.html(f"""
    <div style="background:linear-gradient(135deg,#0D1B2A,#2D1B5C);
                border-radius:20px;padding:26px;color:white;max-width:480px;font-family:Arial,sans-serif">
      <div style="font-size:12px;color:#94A3B8;margin-bottom:6px">@that_human_from_mars | Q4 FY26</div>
      <div style="font-size:22px;font-weight:700;margin-bottom:4px">Sector Beat Rate 📊</div>
      <div style="font-size:12px;color:#94A3B8;margin-bottom:16px">Which sectors crushed estimates?</div>
      {sec_html}
      <div style="font-size:10px;color:#64748B;margin-top:8px;text-align:center">{len(beats)}/{len(declared)} companies beat estimates overall</div>
    </div>
    """, height=450, scrolling=False)

    caption3=("📊 Q4 FY26 Sector Beat Rate\n\n"
              +"\n".join(f"{'🟢' if d['beats']/d['total']>=0.7 else '🟡' if d['beats']/d['total']>=0.5 else '🔴'} {sec}: {d['beats']/d['total']*100:.0f}%" for sec,d in top_s)
              +f"\n\n{len(beats)}/{len(declared)} companies beat estimates\n"
              f"#Q4FY26Results #NSE #SectorAnalysis #IndianStocks #thathumanfrommars")
    st.code(caption3, language=None)
    st.markdown("👆 Copy caption above | Screenshot the card | Post on Instagram")

    st.markdown("---")

    # ── Card 4: Custom stock post ─────────────────────────────────────────────
    st.markdown("### ✍️ Custom Stock Post")
    stock_name=st.selectbox("Pick a declared stock",
                             [s["name"] for s in STOCKS if s["status"]=="Declared"])
    stk=next((x for x in STOCKS if x["name"]==stock_name), None)
    if stk:
        eps_b_val=""
        if stk.get("act_eps") and stk.get("est_eps") and stk["est_eps"]!=0:
            b=(stk["act_eps"]-stk["est_eps"])/abs(stk["est_eps"])*100
            eps_b_val=f"\nEPS: ₹{stk['act_eps']:.2f} vs est ₹{stk['est_eps']:.2f} ({b:+.1f}% {'✅ BEAT' if b>0 else '❌ MISS'})"
        icon="🟢" if stk["ind_rating"] in ("STRONG BUY","BUY","ACCUMULATE") else "🟡" if stk["ind_rating"]=="HOLD" else "🔴"
        custom=(f"{icon} #{stock_name.replace(' ','')} Q4 FY26{eps_b_val}\n\n"
                f"My Rating: {stk['ind_rating']} | Risk: {stk['risk']}\n\n"
                f"📌 {stk.get('catalyst','')[:150]}\n\n"
                f"Full analysis 👇 nse-watchlist-thathumanfrommars.streamlit.app\n\n"
                f"#NSE #{stock_name.replace(' ','')} #Q4Results #StockAnalysis #thathumanfrommars")
        st.code(custom, language=None)
        wa_url="https://wa.me/?text="+urllib.parse.quote(custom)
        st.markdown(f'<a href="{wa_url}" target="_blank" style="background:#25D366;color:white;padding:8px 20px;border-radius:6px;text-decoration:none;font-weight:600">📲 Share via WhatsApp</a>', unsafe_allow_html=True)

    with tab5:
        st.markdown("### 📅 Weekly Recap Carousel")
        st.caption("Every Friday — 5-slide summary ready to post")

        week_beats   = [s for s in declared if s.get("act_eps") and s.get("est_eps") and s["act_eps"]>s["est_eps"]]
        week_misses  = [s for s in declared if s.get("act_eps") and s.get("est_eps") and s["act_eps"]<s["est_eps"]]
        top3_week    = sorted(buy_rows, key=lambda x:-x["ret_pct"])[:3]
        next_week    = [s for s in STOCKS if s["status"]=="Pending"][:5]

        week_summary = (
            f"📊 Weekly Market Recap — {datetime.now().strftime('%d %b %Y')}\n\n"
            f"RESULTS THIS WEEK:\n"
            f"✅ {len(week_beats)} companies beat estimates\n"
            f"❌ {len(week_misses)} companies missed estimates\n\n"
            f"TOP CALLS THIS WEEK:\n"
            + "\n".join(f"{'✅' if r['ret_pct']>=0 else '❌'} #{r['name'].replace(' ','')}: {r['ret_pct']*100:+.1f}%" for r in top3_week)
            + f"\n\nWATCH NEXT WEEK:\n"
            + "\n".join(f"📅 #{s['name'].replace(' ','')} — {s['result_date']}" for s in next_week)
            + f"\n\nFull analysis 👇\nnse-watchlist-thathumanfrommars.streamlit.app\n\n"
            f"#WeeklyRecap #NSE #StockMarket #Q4FY26 #IndianStocks #thathumanfrommars"
        )
        st.code(week_summary, language=None)
        st.markdown("👆 Copy this weekly recap caption | Create a carousel with these stats on Canva")

        st.markdown("""
        **5-slide carousel template:**
        - **Slide 1:** Season scorecard (use Season Scorecard tab)
        - **Slide 2:** This week's beats vs misses
        - **Slide 3:** Top 3 calls this week
        - **Slide 4:** Next week's key results
        - **Slide 5:** Your independent rating + link
        """)

        wa_url_weekly = "https://wa.me/?text=" + urllib.parse.quote(week_summary)
        st.markdown(f'<a href="{wa_url_weekly}" target="_blank" style="background:#25D366;color:white;padding:8px 20px;border-radius:6px;text-decoration:none;font-weight:600">📲 Share Weekly Recap via WhatsApp</a>', unsafe_allow_html=True)


elif page == "⚙️ Live Prices":
    st.markdown("## ⚙️ Live Prices")
    st.caption("Yahoo Finance (NSE). ~15 min delay.")
    if st.button("🔄 Refresh All", type="primary"):
        prog=st.progress(0,"Fetching...")
        fstocks=fs(); rows_lp=[]
        for i,s in enumerate(fstocks):
            t=TICKER_MAP.get(s["name"])
            prog.progress((i+1)/len(fstocks),text=f"Fetching {s['name']}...")
            row={"Company":s["name"],"My Rating":s["ind_rating"],
                 "CMP":"—","Chg %":"—",
                 "SS Target":f"₹{s.get('ss_target'):,}" if s.get("ss_target") else "—",
                 "Upside %":"—","52W H":"—","52W L":"—","P/E":"—","Status":s["status"]}
            if t:
                try:
                    info=yf.Ticker(t).info
                    p=info.get("currentPrice") or info.get("regularMarketPrice")
                    c=info.get("regularMarketChangePercent")
                    target_p=s.get("ss_target")
                    upside=f"{(target_p/p-1)*100:+.1f}%" if (target_p and p and p>0) else "—"
                    row.update({"CMP":f"₹{p:,.2f}" if p else "—",
                                "Chg %":f"{c:+.2f}%" if c else "—",
                                "Upside %":upside,
                                "52W H":f"₹{info.get('fiftyTwoWeekHigh'):,.0f}" if info.get('fiftyTwoWeekHigh') else "—",
                                "52W L":f"₹{info.get('fiftyTwoWeekLow'):,.0f}" if info.get('fiftyTwoWeekLow') else "—",
                                "P/E":f"{info.get('trailingPE'):.1f}x" if info.get('trailingPE') else "—"})
                    time.sleep(0.3)
                except: pass
            rows_lp.append(row)
        prog.empty()
        df_lp=pd.DataFrame(rows_lp)
        def ccg(v):
            if v=="—": return ""
            try:
                n=float(v.replace("%","").replace("+",""))
                return "color:#1B4332;font-weight:600" if n>=0 else "color:#C0392B;font-weight:600"
            except: return ""
        def crr(v): return f"background-color:{RATING_BG.get(v,'#F3F4F6')};color:{RATING_COLORS.get(v,'#374151')};font-weight:600"
        def cup(v):
            if v=="—": return ""
            try:
                n=float(v.replace("%","").replace("+",""))
                return "color:#1B4332;font-weight:600" if n>0 else "color:#C0392B;font-weight:600"
            except: return ""
        st.dataframe(df_lp.style.map(ccg,subset=["Chg %"]).map(cup,subset=["Upside %"]).map(crr,subset=["My Rating"]),
                     use_container_width=True,hide_index=True,height=800)
        st.success(f"✅ {len(rows_lp)} stocks at {datetime.now().strftime('%H:%M:%S')}")
    else:
        st.info("Click **Refresh All** to fetch live NSE prices.")
