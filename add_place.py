# 사용: python3 add_place.py < entry.json  — places.json에 가게를 추가하거나(같은 id면) 교체한다.
import json,sys
A='23456789CFGHJMPQRVWX'
def dec(c):
    c=c.replace('%2B','+').split('+'); c=(c[0]+c[1][:2])
    lat=-90.0;lng=-180.0;res=[20,1,.05,.0025,.000125]
    for i in range(5):
        lat+=A.index(c[2*i])*res[i]; lng+=A.index(c[2*i+1])*res[i]
    return round(lat+.0000625,5), round(lng+.0000625,5)
e=json.load(sys.stdin)
if 'pc' in e: e['lat'],e['lng']=dec(e.pop('pc'))
e.setdefault('country','한국'); e.setdefault('youtubers',[])
P=json.load(open('places.json'))
P=[p for p in P if p['id']!=e['id']]+[e]
json.dump(P,open('places.json','w'),ensure_ascii=False,indent=1)
print(len(P),e['name'],e['lat'],e['lng'])
