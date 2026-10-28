# 사용: python3 mk_jp.py spec.json — 해외(일본) 가게 등록. 현지인 기준:
# 맛은 scoring.py의 1안 조각별 환산과 베이지안 평균, 유튜버 가감점으로 계산한다.
# 한국어 후기는 점수에 넣지 않고 kr(한국인 입맛 메모)에만 쓴다. 서비스·가성비·분위기·접근성은 읽고 매긴 값.
import json,sys,urllib.parse
from scoring import apply_scoring, score
avg=lambda h:(round(sum((i+1)*c for i,c in enumerate(h))/sum(h),1) if sum(h) else None)
P=json.load(open('places.json'))
for e in json.load(open(sys.argv[1])):
    tb,tn=e['tabelog'][:2]; ja=e['ja']; ko=e['ko']; ga=avg(ja); ka=avg(ko)
    ys=e.get('youtubers',[]); basis=e.get('tasteBasis',''); ax=e['axes']
    g=e['google']; hist=g['hist']; tot=sum(hist); old=e.get('old',False); yrs=5 if old else 3
    nonja=sum(ko)+e.get('x',0); alln=nonja+sum(ja)
    ratings=[{"src":"타베로그","rating":tb,"count":tn,"note":"일본 현지인이 주로 쓰는 사이트. 3.5면 좋은 집, 3.7 이상이면 아주 좋은 집으로 통함."},
      {"src":"구글","rating":g['r'],"count":tot,"lowPct":round((hist[3]+hist[4])/tot*100,1),"note":f"5점 {hist[0]:,} · 4점 {hist[1]:,} · 3점 {hist[2]:,} · 2점 {hist[3]:,} · 1점 {hist[4]:,}. 최신순 {e['read']}건을 불러와 기간 안의 후기를 언어별로 나눠 읽음."},
      {"src":"구글(일본어·최근)","rating":ga,"count":sum(ja),"note":f"일본어로 쓴 후기만 집계: 5점 {ja[4]} · 4점 {ja[3]} · 3점 {ja[2]} · 2점 {ja[1]} · 1점 {ja[0]}."}]
    if sum(ko): ratings.append({"src":"구글(한국어·최근)","rating":ka,"count":sum(ko),"note":f"한국어로 쓴 후기: 5점 {ko[4]} · 4점 {ko[3]} · 3점 {ko[2]} · 2점 {ko[1]} · 1점 {ko[0]}. 점수 계산에는 쓰지 않음."})
    p={"id":e['id'],"name":e['name'],"area":e['area'],"region":e.get('region','도쿄'),"country":"일본","cuisine":e['cuisine'],"menus":e['menus'],"category":"·".join(e['menus']),"lat":e['lat'],"lng":e['lng'],
     "gmaps":"https://www.google.com/maps/search/?api=1&query="+urllib.parse.quote(e['q']),"summary":e['summary'],"axes":ax,"tasteBasis":basis,"ratings":ratings,"youtubers":ys,
     "complaints":e['complaints'],"praise":e['praise'],"recent":e.get('recent',''),"tips":e.get('tips',[]),"kr":e['kr'],"evidence":e['evidence'],"checked":e.get('checked','2026-10-07'),"old":old,
     "window":f"{'노포(30년 이상)' if old else '일반'} 기준: 최근 {yrs}년 후기만 반영. 해외는 현지어(일본어) 후기 기준, 한국어 후기는 메모로만 정리","tabelog":"https://tabelog.com"+e['tabelog'][2]}
    if e.get('gdis'):
        ratings[1]['distrust']=True; ratings[2]['distrust']=True
    if e.get('roachNote'):
        p['roach']=True; p['pest']='바퀴벌레 후기'; mo=ax['mood']; mo['s']=max(1,mo['s']-1); mo['fo']='위생 감점 — 쥐·바퀴벌레는 최근 2년 안에 1건이어도 1점 감점: '+e['roachNote']
    if e.get('tbr'):
        n,a,b,txt=e['tbr']; ratings[0]['note']=f"일본 현지인이 주로 쓰는 사이트(3.5면 좋은 집, 3.7 이상이면 아주 좋은 집). 최근 방문순 후기 {n}건을 읽음: 개별 점수 평균 {a} — 4.0 이상 {b[3]} · 3.5~3.9 {b[2]} · 3.0~3.4 {b[1]} · 3.0 미만 {b[0]}. 낮은 점수 후기 내용: {txt}."
        p['complaints'].append({"axis":"taste","text":"타베로그 낮은 점수 후기: "+txt+".","n":b[0],"when":"타베로그 3.0 이하, 최근 후기","tb":True})
    if e.get('glow'):
        g2=e['glow']; ratings[1]['note']+=f" 낮은 평점순도 따로 불러와 기간 안 {g2[0]}건 확인(1~2점: 일본어 {g2[1]}건 · 한국어 {g2[2]}건)."
    if alln>=30 and nonja/alln>=0.7: p['tourist']=f"구글 최신 후기 {alln}건 중 {nonja}건이 일본어가 아님"
    if sum(ko)>=30 and alln and sum(ko)/alln>=0.2: p['krPopular']=f"구글 최신 후기 {alln}건 중 {sum(ko)}건({round(sum(ko)/alln*100)}%)이 한국어"
    for f in('caution','poison','healthNote','occasion'):
        if e.get(f): p[f]=e[f]
    previous=next((x for x in P if x['id']==p['id']),{})
    if 'price' in e or 'price' in previous: p['price']=e.get('price',previous.get('price'))
    apply_scoring(p)
    P=[x for x in P if x['id']!=p['id']]+[p]
    print(p['name'],{a:ax[a]['s'] for a in ('taste','service','value','mood','access')},'점수',score(p),'관광객' if p.get('tourist') else '',f"ja {ga}/{sum(ja)} ko {ka}/{sum(ko)}")
json.dump(P,open('places.json','w'),ensure_ascii=False,indent=1)
