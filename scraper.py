from google_play_scraper import Sort, reviews
import pandas as pd

apps = ['am.idram.app', 'am.ggtaxi.passenger', 'am.telcell.wallet', 'am.arca.mobile', 'com.fnet.viber']

all_reviews = []
print("--- Տվյալների հավաքագրումը սկսված է ---")

for app in apps:
    print(f"Մշակվում է {app}...")
    try:
        result, _ = reviews(
            app,
            country='am',
            sort=Sort.NEWEST,
            count=1000 
        )
        for r in result:
            if r['content']: 
                all_reviews.append({
                    'comment': r['content'],
                    'score': r['score']
                })
    except Exception as e:
        print(f"Սխալ {app}-ի դեպքում: {e}")

if len(all_reviews) > 0:
    df = pd.DataFrame(all_reviews)
    df.to_csv('armenian_reviews.csv', index=False, encoding='utf-8-sig')
    print(f"Հաջողությամբ հավաքվեց {len(df)} մեկնաբանություն:")
else:
    print("Ոչ մի մեկնաբանություն չգտնվեց: Ստուգեք ինտերնետ կապը:")