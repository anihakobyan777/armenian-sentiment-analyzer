import pandas as pd
import random

def generate_ecom_data():
    platforms = ['Wildberries', 'Temu', 'Amazon']
    products = ['iPhone 15', 'AirPods Pro', 'Xiaomi Vacuum', 'Coffee Maker']
    
    pos_reviews = ["Շատ որակյալ ապրանք է", "Արագ հասավ, գոհ եմ", "Լավն է, խորհուրդ եմ տալիս", "Գերազանց է"]
    neg_reviews = ["Որակը շատ վատն է", "Փչացած էր", "Չի համապատասխանում նկարին", "Շատ դանդաղ հասավ"]
    
    data = []
    for _ in range(200):
        platform = random.choice(platforms)
        product = random.choice(products)
        is_positive = random.choice([True, False])
        
        review = random.choice(pos_reviews) if is_positive else random.choice(neg_reviews)
        score = random.randint(4, 5) if is_positive else random.randint(1, 2)
        
        data.append({
            'Platform': platform,
            'Product': product,
            'comment': review,
            'score': score
        })
    
    df = pd.DataFrame(data)
    df.to_csv('ecom_reviews.csv', index=False, encoding='utf-8-sig')
    print("E-commerce տվյալները պատրաստ են (ecom_reviews.csv)")

generate_ecom_data()