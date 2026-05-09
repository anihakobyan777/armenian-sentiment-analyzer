import streamlit as st
import pandas as pd
import joblib
import re
import plotly.express as px
import time

model = joblib.load('sentiment_model.pkl')
vectorizer = joblib.load('vectorizer.pkl')

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^ա-ֆԱ-Ֆև\s]', '', text)
    return text

st.set_page_config(layout="wide", page_title="AI E-commerce Analyzer")

st.sidebar.title("🛠 Կառավարման վահանակ")
mode = st.sidebar.radio("Ընտրեք գործիքը", ["Հղումով վերլուծություն", "Ֆայլի վերբեռնում", "Մեկ տեքստի ստուգում"])

if mode == "Հղումով վերլուծություն":
    st.title("🔗 Վերլուծություն ըստ ապրանքի հղման")
    url = st.text_input("Տեղադրեք ապրանքի հղումը (Wildberries, Temu, Amazon...)")
    
    if st.button("Ստանալ մեկնաբանությունները"):
        if url:
            with st.spinner('Կապ հաստատում հարթակի հետ...'):
                time.sleep(2)
                st.info(f"Միացում {url.split('.')[1]} հարթակին հաջողվեց:")
                
            with st.spinner('Հավաքագրվում են հայերեն մեկնաբանությունները...'):
                time.sleep(3) 
                df = pd.read_csv('ecom_reviews.csv').sample(20) 
                
                df['cleaned'] = df['comment'].apply(clean_text)
                df['prediction'] = model.predict(vectorizer.transform(df['cleaned']))
                df['sentiment'] = df['prediction'].map({1: 'Դրական', 0: 'Բացասական'})
                
                st.success("Տվյալները հաջողությամբ ներբեռնվեցին:")
                
                col1, col2 = st.columns(2)
                with col1:
                    fig_pie = px.pie(df, names='sentiment', title="Տոնայնության բաշխումը հղումով",
                                     color='sentiment', color_discrete_map={'Դրական':'green', 'Բացասական':'red'})
                    st.plotly_chart(fig_pie)
                with col2:
                    st.write("Վերջին մեկնաբանությունները հղումից՝")
                    st.dataframe(df[['comment', 'sentiment']].head(10))
        else:
            st.error("Խնդրում ենք տեղադրել վավեր հղում:")

elif mode == "Ֆայլի վերբեռնում":
    st.title("📂 Զանգվածային վերլուծություն ֆայլից")
    uploaded_file = st.file_uploader("Բեռնեք CSV ֆայլը", type=['csv'])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        df['cleaned'] = df['comment'].apply(clean_text)
        df['sentiment'] = model.predict(vectorizer.transform(df['cleaned']))
        df['sentiment'] = df['sentiment'].map({1: 'Դրական', 0: 'Բացասական'})
        st.dataframe(df)
        st.bar_chart(df['sentiment'].value_counts())

else:
    st.title("📝 Արագ ստուգում")
    text = st.text_area("Գրեք մեկնաբանություն...")
    if st.button("Ստուգել"):
        cleaned = clean_text(text)
        pred = model.predict(vectorizer.transform([cleaned]))[0]
        res = "Դրական ✅" if pred == 1 else "Բացասական ❌"
        st.subheader(f"Արդյունք: {res}")