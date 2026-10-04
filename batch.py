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
        va=ax['value']; v=kw(kd[1],kd[2]) if kd else None; va.pop('kw',None)
        if v is not None: va['s']=v; va['src']='kakao'; va['kwk']=f"맛을 보고 가는 메뉴라 가격이 싼지 비싼지는 보지 않고 값어치 평가만 봄: 카카오 {kd[0]}건 중 '값을 한다·만족' {kd[1]} · '돈 아깝다·값만큼은 아니다' {kd[2]}"
        else: va['s']=ax['taste']['s']; va['src']='taste'; va['auto']=False; va['kwk']="맛을 보고 가는 메뉴라 가격은 보지 않음. 값어치 후기가 적어 맛 점수를 그대로 가심비로 씀"
    if fo:
        k,txt=fo; ax['mood']['s']=max(1,ax['mood']['s']-0.5*k); ax['mood']['fo']=f"위생 {0.5*k:g}점 감점 — 2건 이상 반복된 상황마다 0.5점: {txt}"
        R=json.load(open('rule_overrides.json')); R['fo'][e['id']]=fo; json.dump(R,open('rule_overrides.json','w'),ensure_ascii=False,indent=1)
    # 분위기용: 분위기 칭찬이 후기의 15% 이상(10건 이상)이고 감점 전 분위기 점수 4.0 이상
    on=(0 if dis else s2['n'])+(kd[0] if kd else 0); op=(0 if dis else s2['mood'][0])+(kd[4] if kd else 0)
    p.pop('occasion',None)
    if on and op>=10 and op/on>=0.15 and ax['mood']['s']+(0.5*fo[0] if fo else 0)>=4.0: p['occasion']=f"후기 {on}건 중 {op}건({round(op/on*100)}%)이 분위기 칭찬"
    ro=e.get('roachNote')
    if ro:
        p['roach']=True; p['pest']=e.get('pest','바퀴벌레 후기'); mo=ax['mood']; mo['s']=max(1,mo['s']-1); mo['fo']=(mo['fo']+' / ' if mo.get('fo') else '위생 감점 — ')+'쥐·바퀴벌레는 최근 2년 안에 1건이어도 1점 감점: '+ro
    json.dump(P,open('places.json','w'),ensure_ascii=False,indent=1)
    w={'taste':2,'service':1,'value':1,'mood':1,'access':1}
    print(p['name'],{a:ax[a]['s'] for a in w}, round((sum(w[a]*ax[a]['s'] for a in w)/6-1)/4*100), '의심' if dis else '', '예외' if any(x.get('hidden') for x in p['ratings']) else '')
