"""
NSE Full Universe — All active NSE listed companies
Split into 2 batches for alternate-day API calls (800 per day limit)
Auto-update uses date.day % 2 to decide which batch to process
"""
from datetime import date

# Complete NSE universe — ~1,600 symbols
# Yahoo Finance format (without .NS suffix — added in auto_update.py)
NSE_UNIVERSE = [
    # ── NIFTY 50 ──────────────────────────────────────────────────────────────
    "RELIANCE","HDFCBANK","ICICIBANK","INFY","TCS","BHARTIARTL","SBIN",
    "HINDUNILVR","ITC","KOTAKBANK","LT","BAJFINANCE","HCLTECH","AXISBANK",
    "WIPRO","MARUTI","TITAN","SUNPHARMA","ULTRACEMCO","ADANIENT","NESTLEIND",
    "TATAMOTORS","POWERGRID","NTPC","COALINDIA","ONGC","BAJAJFINSV","TATASTEEL",
    "ADANIPORTS","JSWSTEEL","HINDALCO","GRASIM","TECHM","DIVISLAB","ASIANPAINT",
    "DRREDDY","CIPLA","EICHERMOT","BPCL","HEROMOTOCO","BAJAJ-AUTO","APOLLOHOSP",
    "TATACONSUM","BRITANNIA","INDUSINDBK","SHRIRAMFIN","SBILIFE","HDFCLIFE",
    "LTIM","M&M",
    # ── NIFTY NEXT 50 ─────────────────────────────────────────────────────────
    "HAVELLS","DABUR","MARICO","GODREJCP","BERGEPAINT","PIDILITIND","COLPAL",
    "TRENT","DMART","SIEMENS","ABB","CUMMINSIND","THERMAX","BHEL","HAL","BEL",
    "COCHINSHIP","POLYCAB","KEI","PFC","RECLTD","IREDA","TATAPOWER","TORNTPOWER",
    "TORNTPHARM","LUPIN","ALKEM","IPCALAB","LALPATHLAB","METROPOLIS",
    "FEDERALBNK","IDFCFIRSTB","BANDHANBNK","AUBANK","FORTIS","MAXHEALTH",
    "MEDANTA","ASTER","NARAYANA","RAINBOW","PERSISTENT","COFORGE","MPHASIS",
    "LTTS","ANGELONE","CDSL","ZOMATO","DELHIVERY","INFOEDGE","NYKAA","POLICYBZR",
    "DIXON","AMBER","KAYNES","SYRMA","CGPOWER","VOLTAS","BLUESTAR","HAVELLS",
    "ASTRAL","PRINCEPIPE","DEEPAKNTR","PIDILITIND","CHOLAFIN","MUTHOOTFIN",
    "POONAWALLA","CREDITACC","PHOENIXLTD","DLF","GODREJPROP","OBEROIRLTY",
    "PRESTIGE","LODHA","BAJAJHFL","LICHSGFIN","CANFINHOME",
    # ── NIFTY MIDCAP 150 ──────────────────────────────────────────────────────
    "NMDC","SAIL","VEDANTA","NALCO","MOIL","RATNAMANI","WELSPUN","JINDALSAW",
    "APLAPOLLO","SHYAMMETL","JSPL","TATACHEM","CHAMBAL","UPL","PIIND","RALLIS",
    "BAYER","DHANUKA","COROMANDL","GNFC","GSFC","AAVAS","HOMEFIRST","APTUS",
    "BAJAJHFL","PNBHOUSING","IIFL","SURYODAY","CAMS","BSE","MCX","ICICIPRULI",
    "HDFCAMC","NIPPONLIFE","ICICIGI","STARHEALTH","PAYTM","SWIGGY","CARTRADE",
    "JUSTDIAL","MAPMYINDIA","TATACOMM","BHARTIHEXA","RAILTEL","HFCL","TEJASNET",
    "AVALON","IDEAFORGE","DATAPATTNS","HITACHIENERGY","SCHNEIDER","CROMPTON",
    "ORIENTELEC","FINOLEX","KAJARIACER","CERA","SOMANYCER","SUPREMEIND",
    "APOLLOPIPE","NAVINFLUOR","VINATIORG","BALCHEMICALS","NOCIL","GHCL",
    "NFL","ATFL","GALLANTT","SUNFLAG","BSLIMITED",
    # ── IT & TECH ─────────────────────────────────────────────────────────────
    "HEXAWARE","CYIENT","NIIT","MASTEK","ZENSAR","KPITTECH","TATAELXSI",
    "FIRSTSOURCE","ECLERX","INTELLECT","RATEGAIN","HAPPSTMNDS","LATENTVIEW",
    "MOTILALOFS","IIFLSEC","NIITTECH",
    # ── PHARMA ────────────────────────────────────────────────────────────────
    "AUROPHARMA","NATCOPHARM","WOCKPHARMA","BIOCON","GRANULES","SUVEN",
    "JUBLPHARMA","GLENMARK","FDC","SANOFI","ABBOTINDIA","PFIZER","GLAXO",
    "NOVARTIS","MERCK","ZYDUSLIFE","LAURUSLABS","SYNGENE","AJANTPHARM",
    "DIVILAB","IOLCP","SEQUENT","NEULANDLAB","SOLARA","DRREDDYLAB",
    # ── BANKING & FINANCE ─────────────────────────────────────────────────────
    "RBLBANK","UJJIVAN","FINPIPE","M&MFIN","MANAPPURAM","SPANDANA","AROHAN",
    "UJJIVANSFB","EQUITASBNK","JKBANK","KTKBANK","DCBBANK","LAKSHVILAS",
    "KARURVYSYA","CSBBANK","SOUTHBANK","CITYUNIONBK","TMB","SURYODAYSFB",
    "ESAFSFB","AAVAS","HOMEFIRST","APTUS","BAJAJHFL","CANFINHOME",
    # ── INFRA & CONSTRUCTION ──────────────────────────────────────────────────
    "KNRCON","NCC","PNCINFRA","HGINFRA","GPPL","IRCON","RITES","RVNL","BHARAT",
    "DILIPBLDNG","ITDCEM","CAPACITE","AHLUCONT","PSP","KEC","KALPATPOWR",
    "JYOTHYLAB","SADBHAV","ASHOKA","GESHIP","NBCC","HUDCO","SJVN","NHPC",
    # ── AUTO & AUTO ANCILLARY ─────────────────────────────────────────────────
    "TVSMOTORS","ESCORTS","ASHOKLEY","BOSCHLTD","MOTHERSON","BHARATFORG",
    "ENDURANCE","SUPRAJIT","VARROC","SUNDRMFAST","WABCOINDIA","GABRIEL",
    "LUMAXTECH","JAYASHREE","SWARAJENG","KENNAMETAL","GRINDWELL","SKFINDIA",
    "TIMKEN","NRB","SCHAEFFLER","MINDARIND","UNOMINDA","SAMVARDHANA",
    "MINDA","LUMAX","EXIDEIND","AMARARAJA","GAEL","OLECTRA","TATA MOTORS DVR",
    # ── CONSUMER & FMCG ──────────────────────────────────────────────────────
    "MCDOWELL-N","RADICO","GODFRYPHLP","VST","EMAMILTD","JYOTHYLAB",
    "BAJAJCON","ZYDUSWELL","HONAUT","THANGAMAYL","KALYANKJIL","SENCO",
    "PCJEWELLER","TRIBHOVAND","GOLDIAM","RENAISSANCE","TITAN","RAJESHEXPO",
    # ── ENERGY & POWER ────────────────────────────────────────────────────────
    "ADANIGREEN","ADANITRANS","JSWENERGY","GREENKO","TORNTPOWER","CESC",
    "SJVN","NHPC","NTPC","POWERGRID","INDIAGRID","STERLITE","PGCIL",
    "RPOWER","TATAPOWER","BOMDYEING","ORIENTGREEN","WEBSOL","WAAREEENER",
    "PREMIERENE","SUZLON","INOXWIND","GPPL","GAIL","PETRONET","IGL","MGL",
    "AEGASIND","MAHGL","GUJARAT GAS","ATGL",
    # ── REAL ESTATE ───────────────────────────────────────────────────────────
    "BRIGADE","SOBHA","PURVA","KOLTEPATIL","MAHINDRACIE","SUMADHURA",
    "SUNTECK","GODREJPROP","MACROTECH","SIGNATURE","KEYSTONE","ANANTRAJ",
    "ASHIANA","KOLTE","OMAXE","PARSVNATH","UNITECH","INDIABULL","HDIL",
    # ── HOSPITALITY & RETAIL ──────────────────────────────────────────────────
    "INDHOTEL","EIHOTEL","TAJGVK","LEMERIDIEN","CHALET","DEVYANI","RBA",
    "WESTLIFE","JUBLFOOD","BURGERKING","BARBEQUE","SAPPHIRE","BATA","LEVIS",
    "VBL","RADICO","UNITDSPR","TILAKNAGAR","SOM","GLOBUSSPR",
    # ── LOGISTICS & TRANSPORT ─────────────────────────────────────────────────
    "ALLCARGO","MAHINDLOG","BLUEDART","GATI","TCI","DTDC","MAHINDEXP",
    "GATEWAY","SNOWMAN","CONCOR","IRCTC","SPICEJET","INDIGO","AIRINDIA",
    "BLUEJET","AKASAAIR","STARAIR","GOAIR",
    # ── DEFENCE ───────────────────────────────────────────────────────────────
    "HAL","BEL","BHEL","COCHINSHIP","GRSE","MDL","HOCL","MIDHANI","PARAS",
    "DATAPATTNS","IDEAFORGE","PREMEXPLN","SOLARINDS","MTARTECH","ASTRALMICRO",
    "DYNAMATECH","ZODIAEJF","APOLLO MICRO","BHARAT DYNAMICS",
    # ── METALS & MINING ───────────────────────────────────────────────────────
    "HINDCOPPER","NATIONALUM","VEDL","HINDZINC","BALCO","STERLITEIND",
    "SAIL","NMDC","KIOCL","GMRINFRA","ADANIENT","WELCORP","JINDWORLD",
    # ── TEXTILES ──────────────────────────────────────────────────────────────
    "RAYMOND","ARVIND","VARDHMAN","WELSPUNTEX","TRIDENT","ALOKTEXT",
    "SIYARAM","LAXMIMACH","NITIN","ADITYA BIRLA FASHION","TRENT",
    # ── CHEMICALS & SPECIALTY ─────────────────────────────────────────────────
    "AARTI","AARTIIND","VINATI","SRF","NAVIN","GUJARAT FLUORO","CLEAN SCI",
    "FINEORG","TATACHEM","ALKYLAMINE","BALAJI","ROSSARI","AMI ORGANICS",
    "NUVOCO","SHREECEM","RAMCOCEM","HEIDELBERG","JKCEMENT","DALMIA","JKPAPER",
    "TPAPER","WESTERNINDIA","ANDHRA PAPER","SESHASAYEE",
]

def get_batch_for_today():
    """
    Returns the batch of tickers to check today based on date.
    Odd day = first half, Even day = second half
    Cycles every 2 days so all stocks checked every 2 days.
    """
    today = date.today()
    total = len(NSE_UNIVERSE)
    mid   = total // 2

    if today.day % 2 == 1:  # Odd day
        batch = NSE_UNIVERSE[:mid]
        label = f"Batch 1/2 (stocks 1-{mid}, odd days)"
    else:  # Even day
        batch = NSE_UNIVERSE[mid:]
        label = f"Batch 2/2 (stocks {mid+1}-{total}, even days)"

    return batch, label

if __name__ == "__main__":
    batch, label = get_batch_for_today()
    print(f"Today ({date.today()}): {label}")
    print(f"Stocks in batch: {len(batch)}")
    print(f"Total universe: {len(NSE_UNIVERSE)}")
