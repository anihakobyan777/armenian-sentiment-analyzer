import pandas as pd
import random

pos_templates = ["Շատ լավ հավելված է", "Հիանալի աշխատում է", "Շատ գոհ եմ", "Ապրեք շատ լավն է", "Գերազանց որակ"]
neg_templates = ["Շատ վատ է աշխատում", "Խնդիրներ կան", "Դուրս չեկավ", "Սխալ է աշխատում", "Վատ ծառայություն"]

data = []
for _ in range(500):
    data.append({'comment': random.choice(pos_templates), 'score': 5})
    data.append({'comment': random.choice(neg_templates), 'score': 1})

pd.DataFrame(data).to_csv('armenian_reviews.csv', index=False, encoding='utf-8-sig')

ecom_data = []
platforms = ['Wildberries', 'Temu', 'Amazon']
products = ['iPhone', 'Vacuum', 'Watch', 'Coffee Maker']
for _ in range(100):
    is_pos = random.choice([True, False])
    ecom_data.append({
        'Platform': random.choice(platforms),
        'Product': random.choice(products),
        'comment': random.choice(pos_templates) if is_pos else random.choice(neg_templates),
        'score': 5 if is_pos else 1
    })
pd.DataFrame(ecom_data).to_csv('ecom_reviews.csv', index=False, encoding='utf-8-sig')

print("Բոլոր անհրաժեշտ ֆայլերը ստեղծվեցին հաջողությամբ:")