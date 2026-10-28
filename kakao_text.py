# 사용: python3 kakao_text.py [--apply]
# 카카오 글 후기 평점과 표본 수를 갱신한 뒤 공통 1안으로 계산한다.
# 20건 미만도 수축에 사용하며, 3점 이하 비율 감점의 20건 기준은 유지한다.
import json
import re
import sys

from scoring import apply_scoring


def refresh_kakao(places, raw, as_of=None):
    records = {str(r[0]): r for r in raw}
    rows = []
    for p in places:
        record = records.get(str(p.get('kakaoId')))
        rating = next((r for r in p['ratings'] if r['src'] == '카카오맵'), None)
        if record and rating and not rating.get('hidden') and not rating.get('distrust'):
            _, _, _, all_hist, text_hist = record
            n = sum(text_hist)
            # A mean is unavailable when no written review exists; use the
            # stored overall rating/count proxy, as the simulation specifies.
            if n:
                value = round(sum((i + 1) * c for i, c in enumerate(text_hist)) / n, 1)
                rating.update(textRating=value, textCount=n)
                rating['note'] = re.sub(r' 맛 점수에는 .*$', '', rating.get('note', '')) + (
                    f' 맛 점수에는 기간 안 후기 {sum(all_hist)}건 중 글이 있는 {n}건의 평균 {value}을 씀'
                    f'(글 없이 별점만 준 {sum(all_hist) - n}건은 뺌).')
            else:
                rating.pop('textRating', None)
                rating.pop('textCount', None)
            if not p['axes']['taste'].get('manual'):
                basis = re.sub(r', 후기 내용이 미지근한 쪽이 많아 −0\.5 \(.*?이 3점 이하\)', '', p.get('tasteBasis', ''))
                basis = re.sub(r', 기간 안 카카오(?: 글 있는)? 후기 \d+건 중 \d+건\(\d+%\)이 3점 이하라 −0\.5', '', basis)
                low = sum(text_hist[:3])
                if n >= 20 and low / n >= 0.5:
                    basis += f', 기간 안 카카오 글 있는 후기 {n}건 중 {low}건({round(low / n * 100)}%)이 3점 이하라 −0.5'
                p['tasteBasis'] = basis
        rows.append(apply_scoring(p, as_of))
    return rows


def main():
    with open('kakao_text_raw.json') as f:
        raw = json.load(f)
    with open('places.json') as f:
        places = json.load(f)
    rows = refresh_kakao(places, raw)
    print(len(rows), '곳 계산, 맛 점수 바뀜', sum(r['new_taste'] != r['old_taste'] for r in rows))
    if '--apply' in sys.argv:
        with open('places.json', 'w') as f:
            json.dump(places, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
