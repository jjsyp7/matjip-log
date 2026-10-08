# 사용: python3 mk.py < spec.json — 정해진 기준대로 맛·서비스·가성비·분위기 점수를 계산해 places.json에 넣는다.
import json,sys,subprocess
A='23456789CFGHJMPQRVWX'
def dec(c):
    c=c.replace('%2B','+').split('+'); c=c[0]+c[1][:2]; lat=-90.0;lng=-180.0;res=[20,1,.05,.0025,.000125]
    for i in range(5): lat+=A.index(c[2*i])*res[i]; lng+=A.index(c[2*i+1])*res[i]
    return round(lat+.0000625,5),round(lng+.0000625,5)
def kw(pos,neg):
    m=pos+neg
    if m<8: return None
    return max(1,min(5,round((3+2*(pos-neg)/m*(m/(m+5)))*2)/2))
e=json.load(sys.stdin); P=json.load(open('places.json'))
lat,lng=dec(e['pc']); old=e.get('old',False); cut=2021 if old else 2023
g=e['google']; hist=g['hist']; tot=sum(hist); ratings=[]
k=e.get('kakao') or {}
if k.get('hidden'): ratings.append({"src":"카카오맵","rating":None,"hidden":True,"note":"가게가 후기를 비공개(후기 미제공)로 설정."})
elif k: ratings.append({"src":"카카오맵","rating":k['r'],"count":k['n'],"note":k.get('note','')})
G_IDX=len(ratings); ratings.append({"src":"구글","rating":g['r'],"count":tot,"lowPct":round((hist[3]+hist[4])/tot*100,1),"distrust":bool(e.get('event')),"note":f"5점 {hist[0]:,} · 4점 {hist[1]:,} · 3점 {hist[2]:,} · 2점 {hist[3]:,} · 1점 {hist[4]:,}. "+g.get('note','')})
kr=e['kr']; n=sum(kr)
# 5점 쏠림: 최근 한국어 구글 30건 이상에서 5점이 85% 이상이면서 카카오보다 1점 이상 높으면 구글을 믿지 않음
if n>=30 and kr[4]/n>=0.85 and k.get('r') and g['r']-k['r']>=1: e['event']=True
if n>=30 and kr[4]/n>=0.9 and not k.get('r'): e['event']=True  # 카카오가 없어 비교할 수 없으면 90% 이상에서 의심
if e.get('tr',0)+n>=30 and e.get('tr',0)/(e.get('tr',0)+n)>=0.7: e['tourist']=f"구글 최신 리뷰 {e['tr']+n}건 중 {e['tr']}건이 외국어"
ratings[G_IDX]['distrust']=bool(e.get('event'))
n=sum(kr); gk=round(sum((i+1)*c for i,c in enumerate(kr))/n,1) if n else None
if n: ratings.append({"src":"구글(한국어·최근)","rating":gk,"count":n,"distrust":bool(e.get('event')),"note":f"최신순 리뷰에서 번역된 외국어 {e.get('tr',0)}건과 기간 밖 리뷰를 빼고 한국어 {n}건만 집계: 5점 {kr[4]} · 4점 {kr[3]} · 3점 {kr[2]} · 2점 {kr[1]} · 1점 {kr[0]}."})
d=e.get('dc')
if d: ratings.append({"src":"다이닝코드","rating":d[0],"count":d[1],"note":"다이닝코드 이용자 평점. 대부분 가게가 3.9~4.5에 몰려 있어 변별력은 낮음."+(" 평가 수가 20건 미만이라 맛 점수 계산에는 쓰지 않음." if d[1]<20 else "")})
ys=e.get('youtubers',[]); recs=len({y['who'] for y in ys if y['grade']=='추천'}); negs=len({y['who'] for y in ys if y['grade']=='비추천'})
bonus=min(1.0,0.5+0.25*(recs-1)) if recs else 0
num=den=0; parts=[]
if k and not k.get('hidden'): num+=2*k['r'];den+=2;parts.append(f"카카오 {k['r']}(×2)")
if gk is not None and not e.get('event'): num+=gk;den+=1;parts.append(f"한국어 구글 {gk}(×1)")
if d and d[1]>=20: num+=d[0];den+=1;parts.append(f"다이닝코드 {d[0]}(×1)")
ax=e['axes']
if den:
    L=num/den; v=L+bonus-(0.5 if negs else 0); basis=" + ".join(parts)+f" → {L:.1f}"
    if e.get('event'): basis+=" (구글은 리뷰 이벤트 의심으로 제외)"
    if bonus: basis+=f", 믿는 유튜버 추천 {recs}명 +{bonus:g}"
    if negs: basis+=", 믿는 유튜버 비추천 −0.5"
    if k.get('hidden'):
        e['noKakao']="예외 · 카카오 미확인"; basis+=" (카카오로 확인할 수 없는 곳이지만 감점하지 않음)"
        if den==1:
            if v-bonus>3.5: v=3.5+bonus
            basis+=", 평점이 한 곳만 남아 맛 점수 상한 3.5"; e['noKakao']="예외 · 카카오 미확인 (평점 한 곳뿐, 맛 상한 3.5)"
    if e.get('luke'): v-=0.5; basis+=f", 후기 내용이 미지근한 쪽이 많아 −0.5 ({e['luke']})"
    ax['taste']['s']=max(1,min(5,int(v*2+0.5)/2))
else: basis="현지인 평점을 쓸 수 없어 구체적인 맛 후기를 읽고 매긴 값"; e['unranked']=bool(k.get('hidden') or not k)
s2=e['s2']
for a in('service','value','mood'):
    pos,neg=s2[a]; ax[a]['kw']=f"최근 한국어 구글 후기 {s2['n']}건 중 긍정 언급 {pos} · 부정 언급 {neg}"
    v=kw(pos,neg)
    if v is not None and not e.get('event'): ax[a]['s']=v; ax[a]['auto']=True
    else: ax[a]['auto']=False
p={"id":e['id'],"name":e['name'],"area":e['area'],"region":e.get('region','서울'),"country":e.get('country','한국'),"cuisine":e['cuisine'],"menus":e['menus'],"category":"·".join(e['menus']),"lat":lat,"lng":lng,"gmaps":"https://www.google.com/maps/search/?api=1&query="+__import__('urllib.parse').parse.quote(e.get('q',e['name'])),
 "summary":e['summary'],"axes":ax,"tasteBasis":basis,"ratings":ratings,"youtubers":ys,"complaints":e['complaints'],"praise":e['praise'],"recent":e.get('recent',''),"tips":e.get('tips',[]),
 "evidence":e['evidence'],"checked":e.get('checked','2026-10-04'),"old":old,
 "window":f"{'노포(30년 이상)' if old else '일반'} 기준: 최근 {5 if old else 3}년({cut}.10 이후) 후기만 반영, 번역된 외국어 리뷰 제외"}
for f in('caution','poison','healthNote','occasion','occasionAlso','tasteFirst','tourist','roach','pest','noKakao','unranked','kakaoId','pestDate','foDate'):
    if e.get(f): p[f]=e[f]
P=[x for x in P if x['id']!=p['id']]+[p]
json.dump(P,open('places.json','w'),ensure_ascii=False,indent=1)
w={'taste':2,'service':1,'value':1,'mood':1,'access':1}
sc=round((sum(w[a]*ax[a]['s'] for a in w if ax[a]['s'] is not None)/sum(w[a] for a in w if ax[a]['s'] is not None)-1)/4*100)
print(len(P),p['name'],lat,lng,{a:ax[a]['s'] for a in ax},'점수',sc)
