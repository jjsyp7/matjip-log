import json,subprocess,sys,re
def kw(pos,neg):
    m=pos+neg
    if m<8: return None
    return max(1,min(5,round((3+2*(pos-neg)/m*(m/(m+5)))*2)/2))
specs=json.load(open(sys.argv[1]))
for e in specs:
    kc=e.pop('kc',None); fo=e.pop('fo',None); kd=e.pop('kd',None); hn=e.pop('hiddenNote',None)
    r=subprocess.run(['python3','mk.py'],input=json.dumps(e,ensure_ascii=False),capture_output=True,text=True)
    if r.returncode: print(r.stderr[-400:]); continue
    P=json.load(open('places.json')); p=[x for x in P if x['id']==e['id']][0]; ax=p['axes']
    dis=any(x.get('distrust') for x in p['ratings'] if x['src']=='구글')
    if hn:
        for x in p['ratings']:
            if x.get('hidden'): x['note']=hn
    if kc:
        n,a,b=kc; ax['service']['kwk']=f"카카오 기간 안 후기 {n}건 중 친절 언급 {a} · 불친절 언급 {b}"
        v=kw(a,b)
        if v is not None: ax['service']['s']=v; ax['service']['src']='kakao'; ax['service']['auto']=True
    s2=e['s2']
    if kd:  # [n, 값어치 긍정, 돈 아깝다, 비싸다만, 분위기 긍정, 분위기 부정]
        n,vp,wn,pn,mp,mn=kd
        K=json.load(open('kakao_counts.json')); K[p['kakaoId']]=kd; json.dump(K,open('kakao_counts.json','w'))
        gp,gn=(0,0) if dis else s2['mood']; ax['mood']['kwk']=f"카카오 기간 안 후기 {n}건 중 긍정 언급 {mp} · 부정 언급 {mn}"
        v=kw(mp+gp,mn+gn)
        if v is not None: ax['mood']['s']=v; ax['mood']['auto']=True
        else: ax['mood']['s']=e['axes']['mood']['s']; ax['mood']['auto']=False
        if not p.get('tasteFirst'):
            gp,gn=(0,0) if dis else s2['value']; ax['value']['kwk']=f"카카오 기간 안 후기 {n}건 중 긍정 언급 {vp} · 부정 언급 {wn+pn}"
            v=kw(vp+gp,wn+pn+gn)
            if v is not None: ax['value']['s']=v; ax['value']['auto']=True
            else: ax['value']['s']=e['axes']['value']['s']; ax['value']['auto']=False
    if p.get('tasteFirst'):
        va=ax['value']; kg=e.get('kg'); v=kw(kg[1],kg[2]) if kg else None; va.pop('kw',None)
        if v is not None: va.update(s=v,src='kakao',auto=True); va['kwk']=f"맛을 보고 가는 메뉴라 가격·양은 보지 않고 가심비(값을 한다고 느꼈는지)만 봄: 카카오 {kg[0]}건 중 '비싸도 만족·값어치 한다' {kg[1]} · '돈 아깝다·값만큼은 아니다' {kg[2]}"
        else: va.update(s=None,src='none',auto=False); va['kwk']="맛을 보고 가는 메뉴라 가격·양은 보지 않음. 가심비를 직접 말한 후기가 8건 미만이라 이 칸은 점수에서 뺌"
    if fo:
        k,txt=fo; ax['mood']['s']=max(1,ax['mood']['s']-0.5*k); ax['mood']['fo']=f"위생 {0.5*k:g}점 감점 — 2건 이상 반복된 상황마다 0.5점: {txt}"
        R=json.load(open('rule_overrides.json')); R['fo'][e['id']]=fo; json.dump(R,open('rule_overrides.json','w'),ensure_ascii=False,indent=1)
    # 분위기용: 분위기 칭찬 비율 10% 이상 + 위생 감점 없음 + 관광객 위주 아님 (세 조건 모두)
    op=(0 if dis else s2['mood'][0])+(kd[4] if kd else 0)
    on=(0 if dis else s2['n'])+(kd[0] if kd else 0)
    p.pop('occasion',None); p['_occPos']=[op,on]
    ro=e.get('roachNote')
    if ro:
        p['roach']=True; p['pest']=e.get('pest','바퀴벌레 후기'); mo=ax['mood']; mo['s']=max(1,mo['s']-1); mo['fo']=(mo['fo']+' / ' if mo.get('fo') else '위생 감점 — ')+'쥐·바퀴벌레는 최근 2년 안에 1건이어도 1점 감점: '+ro
    op,on=p.pop('_occPos',[0,0])
    if on and round(op/on*100)>=10 and not ax['mood'].get('fo') and not p.get('tourist'): p['occasion']=f"후기 {on}건 중 {op}건({round(op/on*100)}%)이 분위기 칭찬, 위생 감점 없음, 관광객 위주 아님"
    json.dump(P,open('places.json','w'),ensure_ascii=False,indent=1)
    w={'taste':2,'service':1,'value':1,'mood':1,'access':1}
    print(p['name'],{a:ax[a]['s'] for a in w}, round((sum(w[a]*ax[a]['s'] for a in w if ax[a]['s'] is not None)/sum(w[a] for a in w if ax[a]['s'] is not None)-1)/4*100), '의심' if dis else '', '예외' if any(x.get('hidden') for x in p['ratings']) else '')
