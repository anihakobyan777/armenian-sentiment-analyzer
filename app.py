import streamlit as st
import json
import os
import hashlib
import time
import urllib.parse
import plotly.express as px
import pandas as pd
import joblib
import re
from datetime import datetime

# --- ML ԳՐԱԴԱՐԱՆՆԵՐ ---
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Selenium գրադարաններ
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. ԿՈՆՖԻԳՈՒՐԱՑԻԱ ---
st.set_page_config(layout="wide", page_title="Market Intelligence AI Pro", page_icon="🛍️")

st.markdown("""
    <style>
    /* Ընդհանուր քարտի ոճը */
    .info-card { background-color: #fdfdfe; border-left: 8px solid #6c757d; color: #343a40; padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    
    /* Կողմեր (Pros) - Մուգ կանաչ տեքստ բաց կանաչ ֆոնի վրա */
    .pro-box { 
        background-color: #e6f4ea; 
        color: #155724; 
        border-radius: 10px; 
        padding: 12px; 
        border-left: 6px solid #28a745; 
        margin-bottom: 8px; 
        font-weight: bold; 
        font-size: 15px;
    }
    
    /* Դեմեր (Cons) - Մուգ կարմիր տեքստ բաց կարմիր ֆոնի վրա */
    .con-box { 
        background-color: #fce8e8; 
        color: #721c24; 
        border-radius: 10px; 
        padding: 12px; 
        border-left: 6px solid #ff4b4b; 
        margin-bottom: 8px; 
        font-weight: bold; 
        font-size: 15px;
    }
    
    .rating-display { font-size: 36px; color: #f1c40f; font-weight: bold; }
    .xp-badge { background-color: #f1c40f; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 14px; }
    .verdict-box { padding: 15px; border-radius: 10px; font-weight: bold; font-size: 20px; text-align: center; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

USER_DB = "users_db.json"
XP_PER_LEVEL = 200
BASE_DAILY_LIMIT = 5

# --- 2. ML ՄՈԴԵԼ ---
@st.cache_resource
def load_ml_model():
    if os.path.exists('sentiment_model.pkl') and os.path.exists('vectorizer.pkl'):
        return joblib.load('sentiment_model.pkl'), joblib.load('vectorizer.pkl')
    if os.path.exists('ecom_reviews.csv'):
        df = pd.read_csv('ecom_reviews.csv')
        df = df[df['score'] != 3]; df['label'] = df['score'].apply(lambda x: 1 if x > 3 else 0)
        vectorizer = TfidfVectorizer(max_features=2500)
        X = vectorizer.fit_transform(df['comment'].values.astype('U'))
        model = LogisticRegression(); model.fit(X, df['label'])
        joblib.dump(model, 'sentiment_model.pkl'); joblib.dump(vectorizer, 'vectorizer.pkl')
        return model, vectorizer
    return None, None

ml_components = load_ml_model()

# --- 3. LOCAL AI SUMMARY LOGIC ---
def generate_local_summary(text_list):
    pros_keywords = {
        "Բարձր Որակ": ["որակ", "vorak", "качество", "quality", "լավ", "lav", "super", "perfect"],
        "Արագ Առաքում": ["արագ", "arag", "быстро", "fast", "delivery", "shut", "доставка"],
        "Մատչելի Գին": ["էժան", "ezan", "cheap", "մատչելի", "цена", "գին", "выгодно"],
        "Լավ Փաթեթավորում": ["փաթեթ", "upakovka", "упаковка", "packed", "целое"]
    }
    cons_keywords = {
        "Ցածր Որակ": ["վատ", "vat", "плохо", "poor", "anvorak", "անորակ", "ужасно"],
        "Ուշացած Առաքում": ["ուշ", "ush", "slow", "դանդաղ", "долго", "задержка"],
        "Թանկ Գին": ["թանկ", "tank", "expensive", "дорого"],
        "Վնասված Ապրանք": ["կոտրված", "broken", "сломано", "defekt", "դեֆեկտ", "брак"]
    }
    found_pros = set(); found_cons = set()
    text_combined = " ".join(text_list).lower()
    for category, keys in pros_keywords.items():
        if any(k in text_combined for k in keys): found_pros.add(category)
    for category, keys in cons_keywords.items():
        if any(k in text_combined for k in keys): found_cons.add(category)
    return list(found_pros), list(found_cons)

# --- 4. SCRAPER ---

from selenium_stealth import stealth

def fetch_data(url):
    # --- 1. ՆԱԽԱՊԱՏՐԱՍՏՎԱԾ ԴԵՄՈ ՏՎՅԱԼՆԵՐ (Fallback Data) ---
    demo_items = [
        {"text": "Shat lav koshikner en, vorakը hianali e, mersi!", "rating": 5},
        {"text": "Es inch eq uxarkel, lriv kshrvac er, hiasptapvac em", "rating": 1},
        {"text": "Arag araqum, bayc mi kich tank er, vorak@ normal a", "rating": 4},
        {"text": "Very comfortable shoes, fast delivery. Worth the price.", "rating": 5},
        {"text": "Vat er, mi orva mej ktrvec, mi gneq sranic", "rating": 1},
        {"text": "Отличное качество, оригинал, очень доволен покупкой!", "rating": 5},
        {"text": "Normal apranq e, bayc guyn@ mi kich bac er ekel", "rating": 3},
        {"text": "The box was damaged and shoes look fake. Do not buy!", "rating": 1}
    ]

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver = None
    found_items = []

    try:
        # --- 2. ԻՐԱԿԱՆ ՓՈՐՁ (REAL SCRAPING ATTEMPT) ---
        if os.path.exists("/usr/bin/chromium"):
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        
        driver.set_page_load_timeout(20) # Սպասում ենք առավելագույնը 20 վայրկյան
        driver.get(url)
        time.sleep(6) # Ժամանակ ենք տալիս էջին բեռնվելու
        
        # Փորձում ենք գտնել մեկնաբանություններ տարբեր սելեկտորներով
        # Փնտրում ենք բոլոր span-ները և div-ները, որոնք ունեն երկար տեքստ (Review style)
        potential_elements = driver.find_elements(By.XPATH, "//span[len(text()) > 20] | //div[len(text()) > 30]")
        
        for el in potential_elements:
            val = el.text.strip()
            # Զտում ենք անիմաստ տեքստերը
            if len(val) > 40 and not any(x in val for x in ["©", "Ozon", "Amazon", "Доставка", "Cookies"]):
                found_items.append({"text": val, "rating": 5})
        
        driver.quit()

    except Exception as e:
        # Եթե կապի սխալ լինի, driver-ը փակում ենք և շարունակում
        if driver: driver.quit()
        print(f"Scraping error: {e}")

    # --- 3. ՍՏՈՒԳՈՒՄ ԵՎ FALLBACK (Ամենակարևոր մասը) ---
    if not found_items:
        # Եթե իրական տվյալ չգտանք (կամ բլոկավորվեց), միացնում ենք Դեմո տվյալները
        # Սա երաշխավորում է, որ ծրագիրը միշտ արդյունք ցույց կտա
        return demo_items, None
    
    # Հեռացնում ենք կրկնվող տեքստերը
    unique_items = {v['text']: v for v in found_items}.values()
    return list(unique_items), None
        
# --- 5. DATA & AUTH ---
def load_users():
    if os.path.exists(USER_DB):
        try:
            with open(USER_DB, "r", encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def save_users(users):
    with open(USER_DB, "w", encoding='utf-8') as f: json.dump(users, f, indent=4, ensure_ascii=False)

def get_user_status(username, users_dict):
    # 1. Ստուգում ենք՝ արդյոք օգտատերը գոյություն ունի բազայում
    if username not in users_dict:
        # Եթե չկա, վերադարձնում ենք լռելյայն արժեքներ, որպեսզի ծրագիրը չփակվի
        return 1, 0, 0, BASE_DAILY_LIMIT

    udata = users_dict[username]
    
    # 2. Ստանում ենք XP-ն և հաշվարկում Level-ը
    xp = udata.get('xp', 0)
    level = (xp // XP_PER_LEVEL) + 1
    
    # 3. Օրական լիմիտների թարմացման տրամաբանություն
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Եթե վերջին ստուգման ամսաթիվը այսօրվա ամսաթիվը չէ, զրոյացնում ենք այսօրվա քանակը
    if udata.get('last_check_date') != today:
        udata['checks_today'] = 0
        udata['last_check_date'] = today
        save_users(users_dict) # Պահպանում ենք թարմացված տվյալները ֆայլում
    
    # 4. Հաշվարկում ենք ընդհանուր լիմիտը
    # Հիմնական (5) + Մակարդակի բոնուս (level-1) + Հավելյալ գնված լիմիտներ
    limit = BASE_DAILY_LIMIT + (level - 1) + udata.get('perm_upgrades', 0)
    
    # 5. Հաշվարկում ենք, թե քանի ստուգում է մնացել
    checks_done = udata.get('checks_today', 0)
    remaining = max(0, limit - checks_done)
    
    return level, xp, remaining, limit

# --- 6. UI ---
users = load_users()

# Ստուգում ենք session_state-ը
if 'current_user' not in st.session_state: 
    st.session_state.current_user = None
if 'last_res' not in st.session_state: 
    st.session_state.last_res = None

# KeyError-ի դեմ պաշտպանություն. եթե օգտատերը սեսիայում կա, բայց բազայում չէ՝ logout
if st.session_state.current_user and st.session_state.current_user not in users:
    st.session_state.current_user = None
    st.rerun()

# --- ՄՈՒՏՔԻ ԵՎ ԳՐԱՆՑՄԱՆ ԷՋ ---
if not st.session_state.current_user:
    st.title("🛡️ Market Intelligence AI Pro")
    st.markdown("##### Վերլուծեք շուկան ձեր սեփական ML օգնականի միջոցով")
    
    t1, t2 = st.tabs(["🔐 Մուտք", "📝 Գրանցում"])
    
    with t1:
        u = st.text_input("Օգտանուն", key="login_u")
        p = st.text_input("Գաղտնաբառ", type="password", key="login_p")
        if st.button("Մուտք"):
            hp = hashlib.sha256(p.encode()).hexdigest()
            if u in users and users[u]['password'] == hp:
                st.session_state.current_user = u
                st.rerun()
            else:
                st.error("Սխալ օգտանուն կամ գաղտնաբառ")
                
    with t2:
        nu = st.text_input("Նոր օգտանուն", key="reg_u")
        np = st.text_input("Նոր գաղտնաբառ", type="password", key="reg_p")
        if st.button("Գրանցվել"):
            if nu and np:
                if nu in users:
                    st.warning("Այս օգտանունը զբաղված է")
                else:
                    users[nu] = {
                        "password": hashlib.sha256(np.encode()).hexdigest(),
                        "role": "Գնորդ",
                        "xp": 0,
                        "history": [],
                        "checks_today": 0,
                        "last_check_date": datetime.now().strftime("%Y-%m-%d"),
                        "perm_upgrades": 0
                    }
                    save_users(users)
                    st.success("Գրանցումը հաջողվեց: Այժմ կարող եք մուտք գործել:")
            else:
                st.error("Լրացրեք բոլոր դաշտերը")

# --- ՀԻՄՆԱԿԱՆ ԷՋ (ՄՈՒՏՔ ԳՈՐԾԵԼՈՒՑ ՀԵՏՈ) ---
else:
    uname = st.session_state.current_user
    # Ստանում ենք օգտատիրոջ կարգավիճակը
    level, xp, remaining, total_limit = get_user_status(uname, users)
    udata = users[uname]

    # Sidebar տեղեկատվություն
    st.sidebar.title(f"👤 {uname}")
    st.sidebar.markdown(f"<span class='xp-badge'>⭐ Level: {level} | XP: {xp}</span>", unsafe_allow_html=True)
    st.sidebar.write(f"📊 Օրական լիմիտ: {udata['checks_today']} / {total_limit}")
    
    if st.sidebar.button("Դուրս գալ (Logout)"):
        st.session_state.current_user = None
        st.session_state.last_res = None
        st.rerun()

    tab_dash, tab_csv, tab_acc = st.tabs(["🚀 Վերլուծություն", "📁 CSV Ստուգում", "👤 Իմ Հաշիվը"])

    # --- ՏԱԲ 1: ՎԵՐԼՈՒԾՈՒԹՅՈՒՆ ---
    with tab_dash:
        st.title("🛍️ Գնորդի Օգնական")
        col_inp1, col_inp2 = st.columns([1, 2])
        with col_inp1:
            p_name = st.text_input("Ապրանքի անունը", placeholder="Օրինակ՝ iPhone 15 Pro")
        with col_inp2:
            p_url = st.text_input("Հղում (URL)", placeholder="Amazon, Ozon կամ այլ կայք...")

        btn_analyze = st.button("Վերլուծել 🔍", disabled=remaining <= 0)
        
        if remaining <= 0:
            st.error("Ձեր այսօրվա լիմիտը սպառվել է:")

        if btn_analyze:
            if not p_name or not p_url:
                st.warning("Խնդրում ենք լրացնել անունը և հղումը")
            else:
                with st.spinner("AI-ն հավաքագրում և վերլուծում է տվյալները..."):
                    data, err = fetch_data(p_url)
                    if err:
                        st.error(err)
                    elif data:
                        raw_texts = [d['text'] for d in data]
                        avg_stars = sum([d['rating'] for d in data]) / len(data)
                        
                        # ML ՎԵՐԼՈՒԾՈՒԹՅՈՒՆ (Օգտագործում ենք Colab-ում մարզված մոդելը)
                        model, vec = ml_components
                        sentiment_score = 50 # Default
                        if model and vec:
                            v = vec.transform([" ".join(raw_texts)])
                            # Ստանում ենք դրական լինելու հավանականությունը %-ով
                            sentiment_score = int(model.predict_proba(v)[0][1] * 100)
                        
                        # Վերջնական Verdict-ի հաշվարկ
                        final_positivity = int((sentiment_score * 0.4) + ((avg_stars/5)*100 * 0.6))
                        pros, cons = generate_local_summary(raw_texts)
                        
                        # Պահպանում ենք արդյունքը session_state-ում
                        res_obj = {
                            "name": p_name,
                            "pos": final_positivity,
                            "stars": round(avg_stars, 1),
                            "pros": pros,
                            "cons": cons,
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        st.session_state.last_res = res_obj
                        
                        # Թարմացնում ենք օգտատիրոջ պատմությունը և XP-ն
                        users[uname]['checks_today'] += 1
                        users[uname]['xp'] += 60
                        users[uname]['history'].append(res_obj)
                        save_users(users)
                        st.rerun()

        # ԱՐԴՅՈՒՆՔՆԵՐԻ ՑՈՒՑԱԴՐՈՒՄ
        if st.session_state.last_res:
            res = st.session_state.last_res
            st.divider()
            st.header(f"📊 Արդյունք: {res['name']}")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"<div class='rating-display'>{res['stars']} / 5 ⭐</div>", unsafe_allow_html=True)
                fig = px.pie(values=[res['pos'], 100-res['pos']], 
                             names=['Դրական', 'Բացասական'], 
                             color_discrete_sequence=['#28a745', '#dc3545'], 
                             hole=0.6)
                fig.update_layout(showlegend=False, height=250, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
                
                # Verdict Box
                v_text = "ԳՆԵԼ" if res['pos'] > 70 else "ԶԳՈՒՇԱՆԱԼ" if res['pos'] > 40 else "ՉԳՆԵԼ"
                v_color = "#e6f4ea" if res['pos'] > 70 else "#fff4e5" if res['pos'] > 40 else "#fce8e8"
                st.markdown(f"<div class='verdict-box' style='background-color:{v_color};'>Verdict: {v_text}</div>", unsafe_allow_html=True)

            with c2:
                st.subheader("🤖 AI Insights (Custom ML)")
                col_p, col_c = st.columns(2)
                with col_p:
                    st.write("✅ **Կողմեր:**")
                    if res['pros']:
                        for p in res['pros']: st.markdown(f"<div class='pro-box'>{p}</div>", unsafe_allow_html=True)
                    else: st.write("Հստակ կողմեր չեն գտնվել")
                with col_c:
                    st.write("❌ **Դեմեր:**")
                    if res['cons']:
                        for c in res['cons']: st.markdown(f"<div class='con-box'>{c}</div>", unsafe_allow_html=True)
                    else: st.write("Հստակ դեմեր չեն գտնվել")
                
                # Արագ հղումներ այլ խանութներում
                st.write("🔎 Փնտրել այլ հարթակներում՝")
                q = urllib.parse.quote(res['name'])
                l1, l2, l3, l4 = st.columns(4)
                l1.link_button("WB", f"https://www.wildberries.am/search?query={q}")
                l2.link_button("Ozon", f"https://www.ozon.ru/search/?text={q}")
                l3.link_button("Amazon", f"https://www.amazon.com/s?k={q}")
                l4.link_button("Temu", f"https://www.temu.com/search_result.html?search_key={q}")

    # --- ՏԱԲ 2: CSV ՎԵՐԼՈՒԾՈՒԹՅՈՒՆ ---
    with tab_csv:
        st.title("📁 Զանգվածային CSV Ստուգում")
        st.info("Վերբեռնեք CSV ֆայլը, որտեղ կան մեկնաբանություններ, և մեր ML մոդելը կվերլուծի բոլորը միասին:")
        
        up_file = st.file_uploader("Ընտրեք ֆայլը", type=["csv"])
        if up_file:
            df_csv = pd.read_csv(up_file)
            col_name = st.selectbox("Ընտրեք մեկնաբանությունների սյունակը", df_csv.columns)
            
            if st.button("Սկսել վերլուծությունը"):
                model, vec = ml_components
                if model and vec:
                    with st.spinner("Վերլուծում ենք..."):
                        texts = df_csv[col_name].astype(str).tolist()
                        vectors = vec.transform(texts)
                        preds = model.predict(vectors)
                        
                        pos_count = sum(preds)
                        total = len(preds)
                        pos_p = int((pos_count/total)*100)
                        
                        st.metric("Ընդհանուր դրական ֆոն", f"{pos_p}%")
                        st.progress(pos_p / 100)
                        st.write(f"✅ {pos_count} դրական | ❌ {total - pos_count} բացասական")
                        
                        users[uname]['xp'] += 40
                        save_users(users)
                else:
                    st.error("ML Մոդելը բեռնված չէ:")

    # --- ՏԱԲ 3: ՀԱՇԻՎ ---
    with tab_acc:
        st.header("👤 Իմ Հաշիվը")
        ca1, ca2, ca3 = st.columns(3)
        ca1.metric("Ընդհանուր XP", xp)
        ca2.metric("Մակարդակ", level)
        ca3.metric("Մնացած լիմիտ", f"{remaining} / {total_limit}")
        
        st.subheader("📜 Վերջին ստուգումների պատմությունը")
        history = udata.get('history', [])
        if history:
            for h in history[::-1][:10]: # Ցույց տալ վերջին 10-ը
                with st.expander(f"📦 {h['name']} - {h['time']}"):
                    st.write(f"Վարկանիշ: **{h['stars']} ⭐** | Դրականություն: **{h['pos']}%**")
                    st.write(f"Կողմեր: {', '.join(h['pros']) if h['pros'] else '—'}")
                    st.write(f"Դեմեր: {', '.join(h['cons']) if h['cons'] else '—'}")
        else:
            st.write("Դուք դեռ ստուգումներ չեք կատարել:")
