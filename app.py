import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import time
import random

# --- ԿՈՆՖԻԳՈՒՐԱՑԻԱ ---
GEMINI_API_KEY = "AQ.Ab8RN6LDfVT5uKj6lG_4KSaMLy6WhWF0VnbMZRYFpRPI4eebMw"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(layout="wide", page_title="AI Market Intelligence")

# --- SESSION STATE (Տվյալների պահպանում) ---
if 'user' not in st.session_state:
    st.session_state.user = {'logged_in': False, 'xp': 0, 'level': 1, 'history': [], 'limit': 5}

def update_xp(amount):
    st.session_state.user['xp'] += amount
    st.session_state.user['level'] = (st.session_state.user['xp'] // 100) + 1
    st.session_state.user['limit'] = 5 + (st.session_state.user['level'] - 1) * 2

# --- AI ՎԵՐԼՈՒԾՈՒԹՅԱՆ ՖՈՒՆԿՑԻԱ ---
def analyze_with_ai(data, mode="buyer"):
    prompt = f"""
    Վերլուծիր հետևյալ ապրանքի մեկնաբանությունները հայերենով:
    Տվյալներ: {data}
    
    Եթե mode-ը 'buyer' է, տուր կարճ դատավճիռ (Գնել թե ոչ) և Pros/Cons:
    Եթե mode-ը 'seller' է, նշիր Pain Points-ը (ինչից են դժգոհում) և SWOT վերլուծություն:
    Հաշվի առ տրանսլիտը և ռուսերենը:
    """
    response = model.generate_content(prompt)
    return response.text

# --- SIDEBAR (Գրանցում և XP) ---
with st.sidebar:
    st.title("🏆 User Profile")
    if not st.session_state.user['logged_in']:
        with st.expander("Մուտք / Գրանցում"):
            username = st.text_input("Օգտանուն")
            if st.button("Մուտք"):
                st.session_state.user['logged_in'] = True
                st.success(f"Բարի գալուստ, {username}")
                st.rerun()
    else:
        st.info(f"Մակարդակ: {st.session_state.user['level']}")
        st.progress(min(st.session_state.user['xp'] % 100 / 100, 1.0))
        st.write(f"XP: {st.session_state.user['xp']}")
        st.write(f"Օրական լիմիտ: {st.session_state.user['limit']} ստուգում")
        
    st.divider()
    menu = st.radio("Գործիքներ", ["🛒 Գնորդի համար", "💼 Վաճառողի համար", "📜 Պատմություն"])

# --- ՄԱՍ 1: ԳՆՈՐԴԻ ՀԱՄԱՐ ---
if menu == "🛒 Գնորդի համար":
    st.title("🛒 Գնորդի Օգնական")
    url = st.text_input("Տեղադրեք հղումը (WB, Ozon, Temu, Amazon, AliExpress...)")
    
    if st.button("Վերլուծել"):
        if url:
            with st.spinner("AI-ն վերլուծում է քոմենթները..."):
                time.sleep(2) # Սիմուլյացիա (Scraping)
                
                # Սիմուլյացված տվյալներ (հետագայում կփոխարինվի իրական scraping-ով)
                mock_data = "Լավն էր բայց ուշ եկավ. Higly recommended! Shat lavn e, hianali ashxatum e."
                result = analyze_with_ai(mock_data, mode="buyer")
                
                st.subheader("🤖 AI Դատավճիռ")
                st.write(result)
                
                # Cross-platform իմիտացիա
                st.divider()
                st.subheader("💰 Գների համեմատություն այլ հարթակներում")
                col1, col2, col3 = st.columns(3)
                col1.metric("Ozon", "12,500 ֏", "-500 ֏")
                col2.metric("Wildberries", "13,000 ֏", "+200 ֏")
                col3.metric("Temu", "9,800 ֏", "Ամենաէժան", delta_color="normal")
                
                update_xp(15)
                st.session_state.user['history'].append(f"Գնորդի ստուգում: {url}")
                st.balloons()
        else:
            st.warning("Խնդրում ենք հղում տեղադրել")

# --- ՄԱՍ 2: ՎԱՃԱՌՈՂԻ ՀԱՄԱՐ ---
elif menu == "💼 Վաճառողի համար":
    st.title("💼 Seller Analytics Pro")
    tab1, tab2 = st.tabs(["Link Analysis", "CSV Batch"])
    
    with tab1:
        s_url = st.text_input("Մրցակցի կամ Ձեր ապրանքի հղումը")
        if st.button("Ստանալ Business Insights"):
            with st.spinner("Կատարվում է խորը վերլուծություն..."):
                res = analyze_with_ai("Փաթեթավորումը պատռված էր: Товар отличный, но доставка долгая.", mode="seller")
                st.markdown(res)
                update_xp(25)
                st.session_state.user['history'].append(f"Վաճառողի ստուգում: {s_url}")

    with tab2:
        file = st.file_uploader("Բեռնել CSV ֆայլը", type=['csv'])
        if file:
            df = pd.read_csv(file)
            st.write("Ֆայլը բեռնված է: AI-ն պատրաստ է վերլուծել", len(df), "տող:")
            if st.button("Սկսել մասսայական վերլուծություն"):
                update_xp(50)
                st.success("Վերլուծությունը ավարտված է: (XP +50)")

# --- ՄԱՍ 3: ՊԱՏՄՈՒԹՅՈՒՆ ---
elif menu == "📜 Պատմություն":
    st.title("📜 Ձեր ստուգումների պատմությունը")
    if st.session_state.user['history']:
        for item in reversed(st.session_state.user['history']):
            st.write(f"- {item}")
    else:
        st.write("Պատմությունը դատարկ է:")
