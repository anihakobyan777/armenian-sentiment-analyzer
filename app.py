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
def fetch_data(url):
    options = Options()
    
    options.add_argument("--headless")  # Աշխատեցնել առանց բրաուզերի պատուհանը բացելու
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Կեղծում ենք բրաուզերի տվյալները, որ կայքը չհասկանա, որ սա ռոբոտ է
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

    driver = None
    try:
        # Սկզբնավորում ենք Driver-ը
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Սահմանում ենք սպասման առավելագույն ժամանակ (30 վայրկյան)
        driver.set_page_load_timeout(30)
        
        driver.get(url)
        
        # Սպասում ենք, որ էջը բեռնվի
        time.sleep(6) 
        
        # Իջնում ենք մի փոքր ներքև, որպեսզի lazy-load տարրերը հայտնվեն
        driver.execute_script("window.scrollTo(0, 2000);")
        time.sleep(3)
        
        found_items = []
        
        # --- AMAZON SCRAPING LOGIC ---
        if "amazon" in url.lower():
            blocks = driver.find_elements(By.CSS_SELECTOR, ".a-section.review")
            for b in blocks:
                try:
                    text_el = b.find_element(By.CSS_SELECTOR, "span[data-hook='review-body']")
                    star_el = b.find_element(By.CSS_SELECTOR, "i[data-hook='review-star-rating']")
                    
                    text = text_el.text.strip()
                    star_text = star_el.get_attribute("innerHTML")
                    # Քաղում ենք թվային արժեքը (օրինակ՝ "4.0 out of 5 stars" -> 4)
                    rating = int(float(re.search(r"(\d+\.?\d?)", star_text).group(1)))
                    
                    if len(text) > 5:
                        found_items.append({"text": text, "rating": rating})
                except:
                    continue

        # --- OZON SCRAPING LOGIC ---
        elif "ozon" in url.lower():
            # Ozon-ի դեպքում սելեկտորները հաճախ փոխվում են, սա ամենաթարմ տարբերակն է
            texts = driver.find_elements(By.CSS_SELECTOR, "span.tsBodyM")
            for t in texts:
                val = t.text.strip()
                if len(val) > 15: # Զտում ենք կարճ կամ անիմաստ տեքստերը
                    found_items.append({"text": val, "rating": 5}) # Ozon-ի համար դնում ենք default 5
        
        # Եթե ոչ մի տվյալ չգտանք
        if not found_items:
            return None, "Մեկնաբանություններ չգտնվեցին: Հնարավոր է էջը պաշտպանված է կամ սելեկտորները փոխվել են:"

        driver.quit()
        return found_items, None

    except Exception as e:
        if driver:
            driver.quit()
        return None, f"Կապի սխալ: {str(e)}"
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
    udata = users_dict[username]; xp = udata.get('xp', 0); level = (xp // XP_PER_LEVEL) + 1
    today = datetime.now().strftime("%Y-%m-%d")
    if udata.get('last_check_date') != today:
        udata['checks_today'] = 0; udata['last_check_date'] = today; save_users(users_dict)
    limit = BASE_DAILY_LIMIT + (level - 1) + udata.get('perm_upgrades', 0)
    remaining = max(0, limit - udata.get('checks_today', 0))
    return level, xp, remaining, limit

# --- 6. UI ---
users = load_users()
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'last_res' not in st.session_state: st.session_state.last_res = None

if not st.session_state.current_user:
    st.title("🛡️ AI Market Intelligence")
    t1, t2 = st.tabs(["🔐 Մուտք", "📝 Գրանցում"])
    with t1:
        u = st.text_input("Օգտանուն"); p = st.text_input("Գաղտնաբառ", type="password")
        if st.button("Մուտք"):
            hp = hashlib.sha256(p.encode()).hexdigest()
            if u in users and users[u]['password'] == hp: st.session_state.current_user = u; st.rerun()
            else: st.error("Սխալ տվյալներ")
    with t2:
        nu = st.text_input("Նոր օգտանուն"); np = st.text_input("Նոր գաղտնաբառ", type="password")
        if st.button("Գրանցվել"):
            if nu and np:
                users[nu] = {"password": hashlib.sha256(np.encode()).hexdigest(), "role": "Գնորդ", "xp": 0, "history": [], "checks_today": 0, "last_check_date": "", "perm_upgrades": 0}
                save_users(users); st.success("Գրանցված է:")
else:
    uname = st.session_state.current_user; level, xp, remaining, total_limit = get_user_status(uname, users); udata = users[uname]
    st.sidebar.title(f"👤 {uname}"); st.sidebar.markdown(f"<span class='xp-badge'>⭐ XP: {xp}</span>", unsafe_allow_html=True)
    if st.sidebar.button("Logout"): st.session_state.current_user = None; st.rerun()

    tab_dash, tab_csv, tab_acc = st.tabs(["🚀 Վերլուծություն", "📁 CSV Ստուգում", "👤 Իմ Հաշիվը"])

    with tab_dash:
        st.title("🛍️ Գնորդի Օգնական")
        p_name = st.text_input("Ապրանքի անունը"); p_url = st.text_input("Հղում")
        if st.button("Վերլուծել 🔍", disabled=remaining <= 0):
            if p_name and p_url:
                with st.spinner("Ստուգում ենք..."):
                    data, err = fetch_data(p_url)
                    if err: st.error(err)
                    elif data:
                        raw_texts = [d['text'] for d in data]
                        avg_s = sum([d['rating'] for d in data]) / len(data)
                        model, vec = ml_components
                        txt_score = 50
                        if model:
                            v = vec.transform([" ".join(raw_texts).lower()])
                            txt_score = int(model.predict_proba(v)[0][1] * 100)
                        
                        final_p = int(((avg_s/5)*100 * 0.7) + (txt_score * 0.3))
                        pros, cons = generate_local_summary(raw_texts)
                        
                        st.session_state.last_res = {"name": p_name, "pos": final_p, "stars": round(avg_s, 1), "pros": pros, "cons": cons}
                        users[uname]['checks_today'] += 1; users[uname]['xp'] += 60; save_users(users); st.rerun()

        # ՈՒՂՂՎԱԾ ԲԱԺԻՆ (Fixed KeyError)
        if st.session_state.last_res:
            res = st.session_state.last_res
            st.divider(); st.header(f"📊 {res.get('name', 'Անհայտ')}")
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"<div class='rating-display'>{res.get('stars', 0)} / 5 ⭐</div>", unsafe_allow_html=True)
                fig = px.pie(values=[res.get('pos', 50), 100-res.get('pos', 50)], names=['Դրական', 'Բացասական'], color_discrete_sequence=['#28a745', '#dc3545'], hole=0.5)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("🤖 AI Insights (Local Summary)")
                c_pro, c_con = st.columns(2)
                with c_pro:
                    st.write("✅ **Կողմեր:**")
                    pros_list = res.get('pros', [])
                    if pros_list:
                        for p in pros_list: st.markdown(f"<div class='pro-box'>{p}</div>", unsafe_allow_html=True)
                    else: st.write("Հստակ կողմեր չկան:")
                with c_con:
                    st.write("❌ **Դեմեր:**")
                    cons_list = res.get('cons', [])
                    if cons_list:
                        for c in cons_list: st.markdown(f"<div class='con-box'>{c}</div>", unsafe_allow_html=True)
                    else: st.write("Հստակ դեմեր չկան:")
                
                st.write("🔎 Փնտրել այլ հարթակներում՝")
                q = urllib.parse.quote(res.get('name', '')); cols = st.columns(4)
                cols[0].link_button("Wildberries", f"https://www.wildberries.am/search?query={q}")
                cols[1].link_button("Ozon", f"https://www.ozon.ru/search/?text={q}")
                cols[2].link_button("Temu", f"https://www.temu.com/search_result.html?search_key={q}")
                cols[3].link_button("Amazon", f"https://www.amazon.com/s?k={q}")

    with tab_csv:
        st.title("📁 CSV Վերլուծություն")
        uploaded_file = st.file_uploader("Վերբեռնեք CSV", type=["csv"])
        if uploaded_file:
            df_up = pd.read_csv(uploaded_file); column = st.selectbox("Սյունակը", df_up.columns)
            if st.button("Սկսել"):
                model, vec = ml_components
                if model:
                    texts = df_up[column].astype(str).tolist(); vectors = vec.transform(texts); preds = model.predict(vectors)
                    pos_perc = int((sum(preds) / len(preds)) * 100)
                    st.metric("Դրական ֆոն", f"{pos_perc}%"); users[uname]['xp'] += 40; save_users(users)

    with tab_acc:
        st.header("👤 Իմ Հաշիվը"); col_a1, col_a2 = st.columns(2)
        with col_a1: st.metric("XP", xp); st.metric("Level", level)
        with col_a2: st.metric("Ստուգումներ", f"{udata['checks_today']} / {total_limit}"); st.progress((xp % XP_PER_LEVEL) / XP_PER_LEVEL)
        st.divider(); st.subheader("📜 Պատմություն")
        h_list = udata.get('history', [])
        for h in h_list[-10:][::-1]:
            st.write(f"📦 **{h.get('name', '—')}** - {h.get('stars', '—')}⭐ ({h.get('pos', 0)}% Pos) - {h.get('time', '')}")
