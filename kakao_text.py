# 사용: python3 kakao_text.py [--apply] — 카카오 점수를 "기간 안, 글이 한 글자라도 있는 후기"의 평균으로 바꿔 맛 점수를 다시 계산.
# 글 있는 후기가 20건 미만이면 카카오 전체 평점을 그대로 쓴다. 원자료: kakao_text_raw.json [id, 전체평점, 전체건수, 기간 안 별점분포, 글 있는 후기 별점분포]
import json,re,sys
R={r[0]:r for r in json.load(open('kakao_text_raw.json'))}
P=json.load(open('places.json')); avg=lambda h:sum((i+1)*c for i,c in enumerate(h))/sum(h)
rnd=lambda v:max(1,min(5,int(v*2+0.5)/2)); out=[]
for p in P:  # 지난번에 건 상한을 풀고 원래 맛 점수에서 다시 계산
    t=p['axes']['taste']
    if 'rawTaste' in t: t['s']=t.pop('rawTaste')
for p in P:
    r=R.get(str(p.get('kakaoId'))); b=p.get('tasteBasis','')
    b=re.sub(r', 후기 내용이 미지근한 쪽이 많아 −0\.5 \(.*?이 3점 이하\)','',b)  # 같은 규칙의 옛 표기
    m=re.search(r'카카오( 글 있는 후기)? ([\d.]+)\(×2\)',b)
    if not r or not m: continue
    _,oa,ot,allh,th=r; n=sum(th)
    if n<20: continue
    new=round(avg(th),1); parts=re.findall(r'(카카오(?: 글 있는 후기)?|한국어 구글|다이닝코드)\s*([\d.]+)\(×(\d)\)',b)
    num=sum((new if k.startswith('카카오') else float(v))*int(w) for k,v,w in parts); den=sum(int(w) for *_,w in parts); L=num/den
    v=L; mm=re.search(r'추천 \d+명 \+([\d.]+)',b); v+=float(mm.group(1)) if mm else 0
    if '비추천 −0.5' in b: v-=0.5
    low=re.search(r', 기간 안 카카오(?: 글 있는)? 후기 \d+건 중 \d+건\(\d+%\)이 3점 이하라 −0\.5',b); share=sum(th[:3])/n
    other=len(re.findall(r'−0\.5 \(',b)); v-=0.5*other
    if share>=0.5: v-=0.5  # 글 있는 후기(20건 이상) 중 3점 이하가 절반 이상이면 모든 가게에 −0.5
    old=p['axes']['taste']['s']; s=rnd(v)
    nb=re.sub(r'카카오( 글 있는 후기)? [\d.]+\(×2\)',f'카카오 글 있는 후기 {new}(×2)',b); nb=re.sub(r'→ [\d.]+',f'→ {L:.1f}',nb,1)
    out.append((p['name'],float(m.group(2)),new,sum(allh)-n,n,old,s,bool(low),share>=0.5))
    if low: nb=nb.replace(low.group(0),'')
    nb=re.sub(r', 기간 안 카카오 글 있는 후기 \d+건 중 \d+건\(\d+%\)이 3점 이하라 −0\.5','',nb)
    if share>=0.5: nb+=f", 기간 안 카카오 글 있는 후기 {n}건 중 {sum(th[:3])}건({round(share*100)}%)이 3점 이하라 −0.5"
    if '--apply' in sys.argv:
        p['axes']['taste']['s']=s; p['tasteBasis']=nb
        for x in p['ratings']:
            if x['src']=='카카오맵':
                x['textRating']=new; x['textCount']=n
                x['note']=re.sub(r' 맛 점수에는 .*$','',x.get('note',''))+f" 맛 점수에는 기간 안 후기 {sum(allh)}건 중 글이 있는 {n}건의 평균 {new}을 씀(글 없이 별점만 준 {sum(allh)-n}건은 뺌)."
# 후기 적음 상한: 한국 가게에서 (기간 안 카카오 글 있는 후기 + 최근 한국어 구글 후기)가 30건 미만이면 맛 점수 상한 4.0 (유튜버 가산 포함)
CAP_N,CAP=30,4.0; capped=[]
for p in P:
    if p.get('country','한국')!='한국': continue
    r=R.get(str(p.get('kakaoId'))); kn=sum(r[4]) if r else 0
    gn=sum(x.get('count') or 0 for x in p['ratings'] if x['src']=='구글(한국어·최근)')
    b=re.sub(r', 후기 적음\(.*?\) 맛 점수 상한 [\d.]+','',p.get('tasteBasis','')); t=p['axes']['taste']
    allt=sum((x.get('count') or 0) for x in p['ratings'] if x['src'] in ('카카오맵','구글'))  # 전체 기간 후기 수
    if kn+gn<CAP_N and allt<100 and (t.get('s') or 0)>CAP:  # 예전 후기가 많은(전체 100건 이상) 오래된 가게는 상한을 걸지 않음
        capped.append((p['name'],kn,gn,t['s'])); t['rawTaste']=t['s']; t['s']=CAP
        b+=f", 후기 적음(카카오 글 있는 후기 {kn}건 + 한국어 구글 {gn}건 = {kn+gn}건, 30건 미만) 맛 점수 상한 {CAP}"
        p['fewReviews']=f"후기 {kn+gn}건"
    else: p.pop('fewReviews',None)
    if '--apply' in sys.argv: p['tasteBasis']=b
print('후기 적음 상한:',capped)
ch=[o for o in out if o[5]!=o[6]]
print(len(out),'곳 계산, 맛 점수 바뀜',len(ch))
for o in sorted(out,key=lambda o:o[2]-o[1]): 
    if o[5]!=o[6] or abs(o[2]-o[1])>=0.3: print(f"{o[0]} | 카카오 {o[1]}→{o[2]} | 글없음 {o[3]}/{o[3]+o[4]} | 맛 {o[5]}→{o[6]} | 낮은비율감점 {o[7]}→{o[8]}")
import statistics; print('평균 변화',round(statistics.mean(o[2]-o[1] for o in out),2))
if '--apply' in sys.argv: json.dump(P,open('places.json','w'),ensure_ascii=False,indent=1)
