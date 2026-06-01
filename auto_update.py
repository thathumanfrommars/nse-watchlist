"""
NSE Watchlist — Auto-Update v2 (Twelve Data API)
Runs daily via GitHub Actions at 7 PM IST.
"""
import re, time, base64, logging, sys, os
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
    import yfinance as yf
except ImportError:
    sys.exit(1)

try:
    from alerts import alert_new_stocks, alert_results_declared, alert_daily_summary
except:
    def alert_new_stocks(*a): pass
    def alert_results_declared(*a): pass
    def alert_daily_summary(*a): pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s",
                    datefmt="%d-%b-%Y %H:%M", handlers=[logging.StreamHandler(sys.stdout)])

GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN","")
GITHUB_REPO     = os.environ.get("GITHUB_REPOSITORY","thathumanfrommars/nse-watchlist")
GITHUB_BRANCH   = "main"
DATA_FILE       = "data.py"
TD_KEY          = os.environ.get("TWELVE_DATA_KEY","9cc00d2fc2f54d29acb8f6eb83e7d5cf")
DISCOVERY_DAYS  = 15
MIN_MCAP_CR     = 1000

EXISTING = {
    "GRASIM","GAIL","PRESTIGE","RAINBOW","BALKRISIND","JSWSTEEL","ASHOKLEY",
    "NH","GLENMARK","LINDEINDIA","SUZLON","JKTYRE","ASTRAMICRO","BHARATRAS",
    "GOODLUCK","KEI","ASTRAL","JINDALSAW","PFC","CESC","IRCON","BPCL",
    "INDIAMART","IREDA","COCHINSHIP","MFSL","POLYCAB","HUDCO","VBL",
    "PRINCEPIPE","CENTURYPLY","HAVELLS","PVRINOX","SYRMA","PERSISTENT",
    "OBEROIRLTY","INDHOTEL","JSWINFRA","NRBBEARING","PREMEXPLN","BHARTIARTL",
    "TATAMOTORS","TATASTEEL","CIPLA","DRREDDY","DIXON","TATAPOWER","HAL",
    "DLF","CANBK","HINDPETRO","SOLARINDS","MTARTECH","POWERGRID","OIL",
    "PREMIERENE","SAIL","UNOMINDA","KEC","DEEPAKNTR","TORNTPOWER","TITAN",
    "PIDILITIND","GODREJCP","PAGEIND","VOLTAS","SUNPHARMA","EICHERMOT",
    "ITC","COLPAL","HINDALCO","DIVISLAB","ASIANPAINT","ONGC","CUMMINSIND",
    "ABB","BERGEPAINT","BRITANNIA","GODREJPROP","DABUR","MARICO","IPCALAB",
    "NAUKRI","FORTIS","VARROC",
}

SECTOR_MAP = {
    "Technology":"IT Services","Consumer Cyclical":"Consumer Discretionary",
    "Consumer Defensive":"FMCG / Consumer Staples","Healthcare":"Healthcare / Pharma",
    "Financial Services":"Banking / Financial Services","Basic Materials":"Materials / Chemicals",
    "Industrials":"Industrials / Capital Goods","Energy":"Oil & Gas / Energy",
    "Real Estate":"Real Estate","Utilities":"Power / Utilities",
    "Communication Services":"Media / Telecom",
}

def gh_hdr():
    return {"Authorization":f"token {GITHUB_TOKEN}","Accept":"application/vnd.github.v3+json"}

def get_data_py():
    r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}",
                     headers=gh_hdr(), timeout=15)
    if r.status_code==200:
        d=r.json(); return base64.b64decode(d["content"]).decode("utf-8"), d["sha"]
    logging.error(f"Fetch failed: {r.status_code}"); return None, None

def push_data_py(content, sha, msg):
    r = requests.put(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}",
                     headers=gh_hdr(), timeout=15,
                     json={"message":msg,"content":base64.b64encode(content.encode()).decode(),
                           "sha":sha,"branch":GITHUB_BRANCH})
    ok = r.status_code in (200,201)
    logging.info(f"{'✅' if ok else '❌'} Push: {msg}"); return ok

# ── TWELVE DATA: ALTERNATE-DAY BATCH DISCOVERY ────────────────────────────────
def td_calendar():
    """
    Day 1 (odd): Check first 800 stocks from NSE universe via Twelve Data
    Day 2 (even): Check next 800 stocks
    Day 3 (odd): Repeat from start
    Covers all ~1,600 NSE stocks every 2 days within 800 API call/day limit.
    """
    upcoming = []
    today    = datetime.now()
    end_date = today + timedelta(days=DISCOVERY_DAYS)

    # Import NSE universe
    try:
        from nse_universe import get_batch_for_today
        batch, label = get_batch_for_today()
        logging.info(f"📅 Discovery: {label} ({len(batch)} stocks)")
    except ImportError:
        logging.warning("nse_universe.py not found — using calendar API fallback")
        return td_calendar_fallback()

    found = 0
    api_calls = 0

    for sym in batch:
        if sym in EXISTING:
            continue
        if api_calls >= 790:  # Safety buffer below 800 limit
            logging.info(f"⏸ API call limit reached ({api_calls} calls). Stopping.")
            break

        try:
            r = requests.get(
                "https://api.twelvedata.com/earnings",
                params={"apikey": TD_KEY,
                        "symbol": f"{sym}/NSE",
                        "period": "quarterly",
                        "outputsize": 2},
                timeout=12
            )
            api_calls += 1

            if r.status_code == 200:
                data = r.json()
                earnings_list = data.get("earnings", [])

                for e in earnings_list:
                    # Only look at future/upcoming earnings
                    report_date = e.get("report_date","") or e.get("date","")
                    if not report_date: continue

                    try: dt = datetime.strptime(report_date[:10], "%Y-%m-%d")
                    except: continue

                    # Only future results within discovery window
                    if not (today <= dt <= end_date): continue
                    if sym in EXISTING: continue

                    eps_est = e.get("eps_estimate")
                    eps_act = e.get("eps_actual")

                    # Skip if already declared (has actual)
                    if eps_act is not None: continue

                    upcoming.append({
                        "symbol": sym,
                        "yahoo_ticker": f"{sym}.NS",
                        "name": data.get("meta",{}).get("name", sym),
                        "result_date": dt.strftime("%d-%b-%y"),
                        "est_eps": round(float(eps_est),2) if eps_est else None,
                        "est_rev": None,
                    })
                    found += 1
                    logging.info(f"  🆕 Found: {sym} — {dt.strftime('%d-%b-%y')}")
                    break  # Only need first upcoming date per stock

            time.sleep(0.08)  # ~800 calls per minute limit respected

        except Exception as e:
            logging.warning(f"  ⚠ {sym}: {e}")
            time.sleep(0.2)
            continue

    logging.info(f"📅 Discovery complete: {api_calls} API calls, {found} new stocks found")
    return upcoming


def td_calendar_fallback():
    """Fallback: Use Twelve Data earnings_calendar endpoint for NSE."""
    upcoming = []
    today = datetime.now()
    try:
        r = requests.get("https://api.twelvedata.com/earnings_calendar",
                         params={"apikey":TD_KEY,"exchange":"NSE",
                                 "start_date":today.strftime("%Y-%m-%d"),
                                 "end_date":(today+timedelta(days=DISCOVERY_DAYS)).strftime("%Y-%m-%d")},
                         timeout=20)
        if r.status_code==200:
            earnings = r.json().get("earnings",[])
            logging.info(f"📅 Fallback calendar: {len(earnings)} NSE events")
            for e in earnings:
                sym = e.get("symbol","").replace(".NSE","").replace(".NS","")
                if not sym or sym in EXISTING: continue
                try: dt = datetime.strptime(e.get("date","")[:10],"%Y-%m-%d")
                except: continue
                eps = e.get("eps_estimate")
                upcoming.append({
                    "symbol":sym,"yahoo_ticker":f"{sym}.NS",
                    "name":e.get("name",""),"result_date":dt.strftime("%d-%b-%y"),
                    "est_eps":round(float(eps),2) if eps else None,"est_rev":None,
                })
    except Exception as e:
        logging.warning(f"Fallback calendar error: {e}")
    return upcoming

# ── TWELVE DATA: ACTUALS FOR ONE STOCK ───────────────────────────────────────
def td_actuals(nse_symbol):
    result = {"act_eps":None,"act_rev":None}
    sym    = f"{nse_symbol}/NSE"
    try:
        r = requests.get("https://api.twelvedata.com/earnings",
                         params={"apikey":TD_KEY,"symbol":sym,"period":"quarterly","outputsize":1},
                         timeout=15)
        if r.status_code==200:
            lst = r.json().get("earnings",[])
            if lst:
                eps = lst[0].get("eps_actual")
                if eps is not None: result["act_eps"]=round(float(eps),2)
        time.sleep(0.4)
        r = requests.get("https://api.twelvedata.com/income_statement",
                         params={"apikey":TD_KEY,"symbol":sym,"period":"quarterly","outputsize":1},
                         timeout=15)
        if r.status_code==200:
            lst = r.json().get("income_statement",[])
            if lst:
                rev = lst[0].get("revenue") or lst[0].get("total_revenue")
                if rev: result["act_rev"]=int(float(rev)/1e7)
        time.sleep(0.4)
        logging.info(f"  ✅ TD {nse_symbol}: EPS={result['act_eps']}, Rev=₹{result['act_rev']}Cr")
    except Exception as e:
        logging.warning(f"  ⚠ TD {nse_symbol}: {e}")
    return result

# ── YAHOO FINANCE FALLBACK ────────────────────────────────────────────────────
def yf_actuals(ticker):
    result = {"act_eps":None,"act_rev":None}
    try:
        t=yf.Ticker(ticker)
        for df in [t.quarterly_financials, t.quarterly_income_stmt]:
            if df is not None and not df.empty:
                for row in ["Total Revenue","TotalRevenue","Revenue"]:
                    if row in df.index:
                        val=df.loc[row].iloc[0]
                        if val and val>0: result["act_rev"]=int(val/1e7); break
            if result["act_rev"]: break
        try:
            qe=t.quarterly_earnings
            if qe is not None and not qe.empty:
                result["act_eps"]=round(float(qe["EPS"].iloc[0]),2)
        except: pass
        if not result["act_eps"]:
            eps=t.info.get("trailingEps")
            if eps: result["act_eps"]=round(float(eps),2)
        logging.info(f"  ✅ YF {ticker}: EPS={result['act_eps']}, Rev=₹{result['act_rev']}Cr")
        time.sleep(0.4)
    except Exception as e:
        logging.warning(f"  ⚠ YF {ticker}: {e}")
    return result

# ── UPDATE ACTUALS IN data.py ─────────────────────────────────────────────────
def update_actuals(content):
    changes=0; updated=[]
    tmap = {k:v for k,v in re.findall(r'"([^"]+)"\s*:\s*"([A-Z0-9]+\.NS)"',content)}
    pending = [n for n in tmap if re.search(
        rf'"name"\s*:\s*"{re.escape(n)}"[^}}]{{0,400}}"status"\s*:\s*"Pending"',content,re.DOTALL)]
    logging.info(f"\n📋 Pending stocks: {len(pending)}")
    for name in pending:
        ticker=tmap.get(name)
        if not ticker: continue
        logging.info(f"\n🔍 {name}")
        sym=ticker.replace(".NS","")
        res=td_actuals(sym)
        if not res["act_eps"] and not res["act_rev"]:
            res=yf_actuals(ticker)
        if not res["act_eps"] and not res["act_rev"]: continue
        m=re.search(rf'"name"\s*:\s*"{re.escape(name)}"',content)
        if not m: continue
        bs=m.start(); be=content.find('\n    {',bs+1)
        if be==-1: be=content.find('\n]\n',bs)
        block=content[bs:be]; orig=block
        if res["act_eps"] is not None:
            block=re.sub(r'"act_eps"\s*:\s*None',f'"act_eps":      {res["act_eps"]}',block)
        if res["act_rev"] is not None:
            block=re.sub(r'"act_rev"\s*:\s*None',f'"act_rev":      {res["act_rev"]}',block)
        if block!=orig:
            block=block.replace('"status":       "Pending"','"status":       "Declared"')
            content=content[:bs]+block+content[be:]; changes+=1
            updated.append({"name":name,"act_eps":res["act_eps"],"est_eps":None,
                            "act_rev":res["act_rev"],"est_rev":None})
            logging.info(f"  📝 {name}: → Declared")
    return content, changes, updated

# ── ADD NEW STOCKS ────────────────────────────────────────────────────────────
def add_new_stocks(content, upcoming):
    added=0; new_list=[]
    existing_names = set(re.findall(r'"name"\s*:\s*"([^"]+)"',content))
    ex_tickers     = EXISTING | set(re.findall(r'"([A-Z0-9]+)\.NS"',content))
    ins = list(re.finditer(r'\},\s*\n\]',content))
    if not ins: return content,0,[]
    insert_pos=ins[-1].start()+2; new_entries=[]
    for s in upcoming:
        sym=s["symbol"]
        if sym in ex_tickers or sym in existing_names: continue
        logging.info(f"\n🆕 {sym} ({s.get('name','')}) — {s['result_date']}")
        try:
            info=yf.Ticker(s["yahoo_ticker"]).info
            mcap=info.get("marketCap",0) or 0
            if mcap/1e7 < MIN_MCAP_CR:
                logging.info(f"  ⏭ Too small: ₹{mcap/1e7:.0f}Cr"); continue
            sector=SECTOR_MAP.get(info.get("sector",""),info.get("sector","Unknown"))
            target=int(info.get("targetMeanPrice")) if info.get("targetMeanPrice") else None
            pe=int(info.get("trailingPE")) if info.get("trailingPE") else None
            time.sleep(0.5)
        except: sector="Unknown"; target=None; pe=None; mcap=0
        e_eps=s.get("est_eps"); e_rev=s.get("est_rev")
        entry=f'''    {{
        "name":         "{sym}",
        "sector":       "{sector}",
        "result_date":  "{s['result_date']}",
        "quarter":      "Q4 FY26",
        "status":       "Pending",
        "est_eps":      {e_eps if e_eps else 'None'},
        "act_eps":      None,
        "est_rev":      {e_rev if e_rev else 'None'},
        "act_rev":      None,
        "ss_rating":    "BUY",
        "ss_target":    {target if target else 'None'},
        "ind_rating":   "HOLD",
        "risk":         "MEDIUM",
        "upside_captured": None,
        "pe_ratio":     {pe if pe else 'None'},
        "catalyst":     "Q4 FY26 results due {s['result_date']}. Auto-added via Twelve Data.",
        "earnings_commentary": "Results pending. Auto-added — update commentary after declaration.",
        "ind_rationale": "Auto-added. Update rating and rationale after reviewing results.",
    }},'''
        new_entries.append(entry)
        ticker_line=f'\n    "{sym}":{" "*max(1,20-len(sym))}"{s["yahoo_ticker"]}",'
        content=re.sub(r'(TICKER_MAP\s*=\s*\{[^}]+)',lambda m:m.group(0)+ticker_line,content,count=1)
        ex_tickers.add(sym); existing_names.add(sym); added+=1
        new_list.append({"name":sym,"sector":sector,"result_date":s["result_date"],
                         "ind_rating":"HOLD","risk":"MEDIUM","catalyst":f"Results due {s['result_date']}"})
        logging.info(f"  ✅ Added {sym}")
    if new_entries:
        content=content[:insert_pos]+"\n"+"".join(new_entries)+content[insert_pos:]
    return content, added, new_list


# ── TARGET PRICE ALERT ─────────────────────────────────────────────────────────
def check_target_price_alerts(data_content):
    """Check if any stock is trading near or above analyst target price."""
    import re
    try:
        from alerts import send_whatsapp, send_email
    except: return

    # Extract stock data
    stocks = re.findall(
        r'"name"\s*:\s*"([^"]+)".*?"ss_target"\s*:\s*(\d+).*?"ind_rating"\s*:\s*"([^"]+)"',
        data_content, re.DOTALL
    )

    # CMP map (approximate — updated by auto_update runs)
    CMP_MAP = {
        "SOLAR INDUSTRIES":17900,"PREMIER EXPLOSIVES":714,"PERSISTENT":5600,
        "POLYCAB":9465,"KEI INDUSTRIES":4548,"BHARTI AIRTEL":1902,
        "CIPLA":1590,"INDIAN HOTELS":675,"TATA POWER":415,
        "HAL":5100,"DLF":875,"HCL TECHNOLOGIES":1750,
        "BHARAT ELECTRONICS":320,"MAX HEALTHCARE":1080,
    }

    alerts_to_send = []
    for name, target_str, rating in stocks:
        target = int(target_str)
        cmp    = CMP_MAP.get(name)
        if not cmp: continue

        upside = (target - cmp) / cmp * 100
        # Alert if stock hit target or is within 5% of target
        if -5 <= upside <= 5:
            alerts_to_send.append(
                f"🎯 *{name}* near analyst target!\n"
                f"CMP: ₹{cmp:,} | Target: ₹{target:,} | Upside: {upside:+.1f}%\n"
                f"My Rating: {rating}"
            )
        elif upside < -5:  # Stock above target
            alerts_to_send.append(
                f"⚠️ *{name}* above analyst target\n"
                f"CMP: ₹{cmp:,} | Target: ₹{target:,} | {upside:+.1f}% above target\n"
                f"My Rating: {rating} — consider booking partial profits"
            )

    if alerts_to_send:
        msg = f"📊 *Target Price Alerts — {datetime.now().strftime('%d-%b-%Y')}*\n\n"
        msg += "\n\n".join(alerts_to_send)
        try: send_whatsapp(msg)
        except: pass
        logging.info(f"✅ Target price alerts sent for {len(alerts_to_send)} stocks")

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    logging.info(f"\n{'='*55}")
    logging.info(f"🚀 NSE Watchlist Auto-Update v2 — Twelve Data")
    logging.info(f"   {datetime.now().strftime('%d-%b-%Y %H:%M IST')}")

    content, sha = get_data_py()
    if not content: sys.exit(1)

    # Part 1: Update actuals
    logging.info("\n📊 PART 1: Updating actuals...")
    content, actuals_changed, updated_list = update_actuals(content)

    # Part 2: Discover new stocks
    logging.info(f"\n🔍 PART 2: Discovering new stocks...")
    upcoming = td_calendar()
    seen=set(); unique=[s for s in upcoming if s["symbol"] not in seen and not seen.add(s["symbol"])]
    content, stocks_added, new_list = add_new_stocks(content, unique)

    total = actuals_changed + stocks_added

    # Check target price alerts
    check_target_price_alerts(content)

    # Part 3: Alerts
    if updated_list: alert_results_declared(updated_list)
    if new_list:     alert_new_stocks(new_list)
    pending  = content.count('"status":       "Pending"')
    declared = content.count('"status":       "Declared"')
    alert_daily_summary(actuals_changed, stocks_added, pending, declared)

    # Part 4: Push
    if total > 0:
        ok = push_data_py(content, sha,
             f"Auto-update {datetime.now().strftime('%d-%b-%Y')}: "
             f"{actuals_changed} actuals, {stocks_added} new stocks [Twelve Data]")
        if not ok:
            Path(DATA_FILE).write_text(content, encoding="utf-8")
            logging.info("✅ Written locally — git will commit.")
    else:
        logging.info(f"\n✅ Nothing to update. Pending:{pending} | Declared:{declared}")

if __name__=="__main__":
    main()
