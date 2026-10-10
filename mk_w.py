# 사용: python3 mk_w.py spec.json — 일본 밖 해외 가게 등록(2026-10-10 기준).
# 맛 = 현지 사이트가 있으면 (현지 사이트×2 + 현지어 구글 최근×1)/3, 없으면 현지어 구글 최근 평균.
# 현지 사이트: 미국 옐프. 홍콩 오픈라이스는 접속이 안 되고, 프랑스·이탈리아 더포크에는 등록되지 않은 가게가 많아 구글 현지어만 씀.
# 한국어 후기는 점수에 넣지 않고 kr 메모에만 쓴다.
import json,sys,urllib.parse
avg=lambda h:(round(sum((i+1)*c for i,c in enumerate(h))/sum(h),1) if sum(h) else None)
P=json.load(open('places.json'))
for e in json.load(open(sys.argv[1])):
    loc=e['loc']; ko=e['ko']; la=avg(loc); ka=avg(ko); lang=e['lang']; site=e.get('site')
    if site: L=(2*site['rating']+la)/3; basis=f"{site['name']} {site['rating']}(×2) + {lang} 구글 {la}(×1) → {L:.1f}"
    else: L=la; basis=f"{lang} 구글 최근 후기 평균 {la} ({e.get('nosite','현지 사이트 자료 없음')})"
    ys=e.get('youtubers',[]); recs=len({y['who'] for y in ys if y.get('grade')=='\ucd94\ucc9c' and not y.get('tie')}); bonus=min(1.0,0.5+0.25*(recs-1)) if recs else 0
    if bonus: basis+=f", \ubbff\ub294 \uc720\ud29c\ubc84 \ucd94\ucc9c {recs}\uba85 +{bonus:g}"
    basis+=" (\ud55c\uad6d\uc5b4 \ud6c4\uae30\ub294 \uc810\uc218\uc5d0 \ub123\uc9c0 \uc54a\uc74c)"
    ax=e['axes']; ax['taste']['s']=max(1,min(5,int((L+bonus)*2+0.5)/2))
    g=e['google']; hist=g['hist']; tot=sum(hist); nonloc=sum(ko)+e.get('x',0); alln=nonloc+sum(loc)
    ratings=[]
    if site: ratings.append({"src":site['name'],"rating":site['rating'],"count":site['count'],"note":site['note']})
    ratings+=[{"src":"구글","rating":g['r'],"count":tot,"lowPct":round((hist[3]+hist[4])/tot*100,1),"note":f"5점 {hist[0]:,} · 4점 {hist[1]:,} · 3점 {hist[2]:,} · 2점 {hist[3]:,} · 1점 {hist[4]:,}. 최신순 {e['read']}건을 불러와 최근 3년 후기를 언어별로 나눠 읽음."},
      {"src":f"구글({lang}·최근)","rating":la,"count":sum(loc),"note":f"{lang}로 쓴 후기만 집계: 5점 {loc[4]} · 4점 {loc[3]} · 3점 {loc[2]} · 2점 {loc[1]} · 1점 {loc[0]}."}]
    if sum(ko): ratings.append({"src":"구글(한국어·최근)","rating":ka,"count":sum(ko),"note":f"한국어로 쓴 후기: 5점 {ko[4]} · 4점 {ko[3]} · 3점 {ko[2]} · 2점 {ko[1]} · 1점 {ko[0]}. 점수 계산에는 쓰지 않음."})
    p={"id":e['id'],"name":e['name'],"area":e['area'],"region":e['region'],"country":e['country'],"cuisine":e['cuisine'],"menus":e['menus'],"category":"·".join(e['menus']),"lat":e['lat'],"lng":e['lng'],
     "gmaps":"https://www.google.com/maps/search/?api=1&query="+urllib.parse.quote(e['q']),"summary":e['summary'],"axes":ax,"tasteBasis":basis,"ratings":ratings,"youtubers":ys,
     "complaints":[dict(axis=a,text=t,n=n,when=w) for a,t,n,w in e['complaints']],"praise":e['praise'],"recent":"","tips":e['tips'],"kr":e['kr'],"evidence":e['evidence'],"checked":e['checked'],"old":False,"price":e['price'],
     "window":f"일반 기준: 최근 3년 후기만 반영. 해외는 현지어({lang}) 후기 기준, 한국어 후기는 메모로만 정리"}
    if alln>=30 and nonloc/alln>=0.7: p['tourist']=f"구글 최신 후기 {alln}건 중 {nonloc}건이 {lang}가 아님"
    if sum(ko)>=30 and sum(ko)/alln>=0.2: p['krPopular']=f"구글 최신 후기 {alln}건 중 {sum(ko)}건({round(sum(ko)/alln*100)}%)이 한국어"
    for f in('caution','poison','healthNote','occasion'):
        if e.get(f): p[f]=e[f]
    P=[x for x in P if x['id']!=p['id']]+[p]
    w={'taste':2,'service':1,'value':1,'mood':1,'access':1}
    print(p['name'],{a:ax[a]['s'] for a in w},round((sum(w[a]*ax[a]['s'] for a in w)/6-1)/4*100),'관광객' if p.get('tourist') else '',f"{lang} {la}/{sum(loc)} ko {ka}/{sum(ko)}")
json.dump(P,open('places.json','w'),ensure_ascii=False,indent=1)
