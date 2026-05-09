import pandas as pd
import re
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import joblib

df = pd.read_csv('armenian_reviews.csv')

df = df[df['score'] != 3]
df['label'] = df['score'].apply(lambda x: 1 if x > 3 else 0)

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^ա-ֆԱ-Ֆև\s]', '', text)
    return text

df['clean_comment'] = df['comment'].apply(clean_text)

X = df['clean_comment']
y = df['label']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

vectorizer = TfidfVectorizer(max_features=5000)
X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)

model = LogisticRegression()
model.fit(X_train_tfidf, y_train)

y_pred = model.predict(X_test_tfidf)
print(f"Մոդելի ճշգրտությունը: {accuracy_score(y_test, y_pred) * 100:.2f}%")

joblib.dump(model, 'sentiment_model.pkl')
joblib.dump(vectorizer, 'vectorizer.pkl')
print("Մոդելը պահպանվեց 'sentiment_model.pkl' անունով:")