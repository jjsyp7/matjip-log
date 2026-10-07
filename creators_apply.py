# 사용: python3 creators_apply.py [--apply] — places.json의 youtubers(믿는 유튜버 의견)가 바뀐 뒤 맛 점수의 가산·감점을 다시 맞춘다.
# 3년 넘은 영상·이해관계를 밝힌 영상은 가산에서 뺀다(분기마다 다시 돌리면 자동으로 만료됨). 한국 가게만 점수를 고친다. 추천한 사람 수 → +0.5, 한 명 늘 때마다 +0.25(최대 +1.0). 비추천이 있으면 −0.5. 그 뒤 `python3 kakao_text.py --apply`를 돌릴 것.
import json,re,sys,datetime
_t=datetime.date.today(); CUT=f"{_t.year-3}-{_t.month:02d}"  # 이 달보다 먼저 올라온 영상은 3년이 지난 것
P=json.load(open('places.json')); rnd=lambda v:max(1,min(5,int(v*2+0.5)/2)); ch=[]
RB=r', 믿는 유튜버 추천 (\d+)명 \+([\d.]+)'; RN=r', 믿는 유튜버 비추천 −0\.5'
for p in P:
    if p.get('country','한국')!='한국': continue
    ys=p.get('youtubers',[])
    for y in ys:  # 3년 넘은 영상과 이해관계를 밝힌 영상은 가산하지 않는다(등급 표시를 '참고(…)'로 바꾸고 원래 등급은 origGrade에 둔다)
        g=y.get('origGrade',y.get('grade'))
        why='이해관계' if y.get('tie') else ('3년 지난 영상' if y.get('date') and y['date']<CUT else None)
        if why and g in('추천','비추천'): y['origGrade']=g; y['grade']=f"참고({why})"
        elif 'origGrade' in y: y['grade']=y.pop('origGrade')
    recs=len({y['who'] for y in ys if y.get('grade')=='추천'}); negs=len({y['who'] for y in ys if y.get('grade')=='비추천'})
    nb=min(1.0,0.5+0.25*(recs-1)) if recs else 0; nn=0.5 if negs else 0
    b=p.get('tasteBasis',''); t=p['axes']['taste']; cur=t.get('rawTaste',t.get('s'))
    m=re.search(RB,b); ob=float(m.group(2)) if m else 0; on=0.5 if re.search(RN,b) else 0
    if (ob,on)==(nb,nn) and (not m or int(m.group(1))==recs): continue  # 등급 표시는 위에서 이미 고쳐 둠
    base=re.sub(RN,'',re.sub(RB,'',b)); add=(f", 믿는 유튜버 추천 {recs}명 +{nb:g}" if nb else "")+(", 믿는 유튜버 비추천 −0.5" if nn else "")
    k=re.search(r'→ [\d.]+( \(구글은[^)]*\))?',base)
    newb=base[:k.end()]+add+base[k.end():] if k else base+add
    parts=re.findall(r'(카카오(?: 글 있는 후기)?|한국어 구글|다이닝코드|식신)\s*([\d.]+)\((?:×(\d)|\d+명)\)',base)
    if parts and all(w for *_,w in parts):
        L=sum(float(v)*int(w) for _,v,w in parts)/sum(int(w) for *_,w in parts)
        if '상한 3.5' in base: L=min(L,3.5)
        v=L+nb-nn-0.5*len(re.findall(r'3점 이하라 −0\.5|−0\.5 \(',base))
    else: v=(cur or 3)-ob+on+nb-nn
    new=rnd(v); ch.append((p['name'],recs,negs,cur,new))
    if '--apply' in sys.argv:
        p['tasteBasis']=newb; t.pop('rawTaste',None); t['s']=new
for c in ch: print(f"{c[0]} | 추천 {c[1]}명 비추천 {c[2]}명 | 맛 {c[3]} → {c[4]}")
print(len(ch),'곳 바뀜')
if '--apply' in sys.argv: json.dump(P,open('places.json','w'),ensure_ascii=False,indent=1)
