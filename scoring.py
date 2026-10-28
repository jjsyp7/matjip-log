"""Shared option 1 scoring, extracted unchanged from the Bayesian simulation.

Only the standard library is required. Call apply_scoring to update taste,
basis and confidence; calculate_taste leaves its input untouched.
"""
import datetime as dt
import math
import re

PARAMETERS = {
    "kakao": {"C": 3.8, "M": 20},
    "google": {"C": 4.3, "M": 25},
    "google_only_western": {"C": 4.1, "M": 30, "offset": -0.3},
}
LOCAL_GOOGLE = {"한국": "한국어", "일본": "일본어", "미국": "영어",
                "이탈리아": "이탈리아어", "프랑스": "프랑스어", "홍콩": "중국어"}
WESTERN = {"미국", "이탈리아", "프랑스"}

def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def bayes(rating, count, c, m):
    if not number(rating) or not 1 <= rating <= 5:
        raise ValueError("rating must be finite and between 1 and 5")
    if not number(count) or count < 0 or count != int(count):
        raise ValueError("count must be a nonnegative integer")
    if not number(c) or not 1 <= c <= 5 or not number(m) or m <= 0:
        raise ValueError("invalid prior")
    return (count * rating + m * c) / (count + m)


def tabelog(rating):
    if rating < 3.2:
        value = rating
    elif rating < 3.5:
        value = 3.2 + (rating - 3.2) * 0.8 / 0.3
    elif rating < 3.8:
        value = 4 + (rating - 3.5) * 0.7 / 0.3
    else:
        value = 4.7 + (rating - 3.8) * 0.3 / 0.2
    return max(1, min(5, value))


def rounded_taste(value, step):
    value = max(1, min(5, value))
    return math.floor(value / step + 0.5) * step if step else value


def score(place, taste=None):
    weights = {"taste": 2, "service": 0.5, "value": 1, "mood": 1, "access": 1}
    if place.get("cuisine") == "카페·디저트":
        weights["mood"] = 2
    total = weight = 0
    for axis, w in weights.items():
        s = taste if axis == "taste" and taste is not None else place["axes"].get(axis, {}).get("s")
        if number(s):
            total += w * s
            weight += w
    return math.floor((total / weight - 1) / 4 * 100 + 0.5) if weight else None


def creator_adjustment(place, as_of, warnings):
    cutoff = f"{as_of.year - 3}-{as_of.month:02d}"
    groups = {"추천": set(), "비추천": set()}
    for y in place.get("youtubers", []):
        grade = y.get("grade")
        if grade not in groups or y.get("tie"):
            continue
        date = y.get("date")
        if not date:
            warnings.append("creator_date_missing:" + y["who"])
        elif not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", date):
            warnings.append("creator_date_invalid:" + y["who"])
            continue
        elif date[:7] < cutoff or date[:7] > as_of.strftime("%Y-%m"):
            continue
        groups[grade].add(y["who"])
    recs = len(groups["추천"])
    return (min(1, 0.5 + 0.25 * (recs - 1)) if recs else 0) - (0.5 if groups["비추천"] else 0)


def calculate_taste(place, as_of, step=0.5, manual_policy="preserve"):
    country = place["country"]
    if country not in LOCAL_GOOGLE:
        raise ValueError(f"unsupported country: {country}")
    warnings, components = [], []
    ratings = {r["src"]: r for r in place["ratings"]}
    if len(ratings) != len(place["ratings"]):
        raise ValueError(f"duplicate source: {place['id']}")

    def add(src, weight, prior=None, text=False, minimum=0, transform=None, offset=0):
        r = ratings.get(src)
        if not r or r.get("hidden") or r.get("distrust") or r.get("rating") is None:
            return
        use_text = text and r.get("textRating") is not None and r.get("textCount") is not None
        value, count = (r["textRating"], r["textCount"]) if use_text else (r["rating"], r.get("count"))
        if not number(value) or not 1 <= value <= 5:
            raise ValueError(f"invalid rating: {place['id']} / {src}")
        if count is None:
            warnings.append("count_missing:" + src)
            return
        if not number(count) or count < 0 or count != int(count):
            raise ValueError(f"invalid count: {place['id']} / {src}")
        if count < minimum:
            return
        if text and not use_text:
            warnings.append("kakao_total_count_proxy")
        adjusted = transform(value) if transform else value
        adjusted = max(1, min(5, adjusted + offset))
        if prior:
            adjusted = bayes(adjusted, count, prior["C"], prior["M"])
        components.append(dict(src=src, R=value, N=count, weight=weight, adjusted=adjusted,
                               used_text=use_text, prior=prior, offset=offset))

    google_src = f"구글({LOCAL_GOOGLE[country]}·최근)"
    google_allowed = not ratings.get("구글", {}).get("distrust")
    if country == "한국":
        add("카카오맵", 2, PARAMETERS["kakao"], text=True)
        if google_allowed:
            add(google_src, 1, PARAMETERS["google"])
        add("다이닝코드", 1, minimum=20)
    elif country == "일본":
        add("타베로그", 2, transform=tabelog)
        # Japan without Tabelog remains unrated, as in the existing policy.
        if components and google_allowed:
            add(google_src, 1, PARAMETERS["google"], minimum=10)
    else:
        add("옐프", 2)
        western_only = not components and country in WESTERN
        prior = PARAMETERS["google_only_western"] if western_only else PARAMETERS["google"]
        if google_allowed:
            add(google_src, 1, prior, offset=prior.get("offset", 0))

    old_taste = place["axes"]["taste"]["s"]
    if not number(old_taste) or not 1 <= old_taste <= 5:
        raise ValueError(f"invalid stored taste: {place['id']}")
    bonus = creator_adjustment(place, as_of, warnings)
    basis = place.get("tasteBasis", "")
    # Existing explicit deductions are retained; do not infer negative share from lowPct
    # (that field can mean 1–2 stars rather than <=3 stars).
    deduction = 0.5 * len(re.findall(r"3점 이하라 [−-]0\.5|[−-]0\.5 \(", basis))
    total_n = sum(c["N"] for c in components)
    confidence = ("A" if total_n >= 100 else "B" if total_n >= 30 else "C") if components else None
    if not components:
        new_taste, status = old_taste, "retained_no_usable_rating"
        warnings.append("no_usable_rating")
    elif place["axes"]["taste"].get("manual") and manual_policy == "preserve":
        new_taste = place["axes"]["taste"].get("rawTaste", old_taste)
        status = "retained_manual"
        warnings.append("manual_retained_confidence_from_available_ratings")
    else:
        base = sum(c["adjusted"] * c["weight"] for c in components) / sum(c["weight"] for c in components)
        if "상한 3.5" in basis:
            base = min(base, 3.5)
        new_taste = rounded_taste(base + bonus - deduction, step)
        status = "recomputed"
    old_score, new_score = score(place), score(place, new_taste)
    if old_score is None or new_score is None:
        raise ValueError(f"no score: {place['id']}")
    eligible = not (place.get("unranked") or place.get("poison"))
    return dict(id=place["id"], name=place["name"], country=country, status=status,
                old_taste=old_taste, new_taste=new_taste, old_score=old_score, new_score=new_score,
                delta=new_score-old_score, eligible=eligible,
                old_visible=eligible and old_score > 70, new_visible=eligible and new_score > 70,
                confidence=confidence, effective_n=total_n, creator_adjustment=bonus,
                retained_taste_deduction=deduction, components=components, warnings=warnings)


def remove_review_cap(basis):
    """Remove only the retired few-review cap, leaving the 3.5 cap intact."""
    return re.sub(r",?\s*후기 적음(?:\([^)]*\))?\s*맛 점수 상한 [\d.]+", "", basis).strip()


def taste_basis(place, result):
    old = remove_review_cap(place.get("tasteBasis", ""))
    # Retain the human rationale and add a replaceable calculation note.
    old = re.split(r"(?:^|\n)1안 계산: ", old, maxsplit=1)[0]
    if result["status"] != "recomputed":
        note = (f"수동 맛 {result['new_taste']:g}점 유지" if result["status"] == "retained_manual"
                else f"유효 평점 없음, 기존 맛 {result['new_taste']:g}점 유지")
        return (old + "\n" if old else "") + "1안 계산: " + note

    parts = []
    for c in result["components"]:
        name = "카카오 글 후기" if c["used_text"] else c["src"].replace("·", " ")
        detail = f"{name} {c['R']:g} ({c['N']}건"
        if c["prior"]:
            detail += f", C={c['prior']['C']:g}, M={c['prior']['M']:g}"
        if c["offset"]:
            detail += f", 보정 {c['offset']:+g}"
        detail += f") → {c['adjusted']:.4f} (가중치 {c['weight']})"
        parts.append(detail)
    basis = " + ".join(parts)
    if "상한 3.5" in old:
        basis += ", 평점이 한 곳만 남아 맛 점수 상한 3.5"
    if result["creator_adjustment"]:
        basis += f", 유튜버 가감점 {result['creator_adjustment']:+g}"
    # Keep explicit deduction clauses so repeat runs do not lose or double them.
    deductions = re.findall(r"[^,]*3점 이하라 [−-]0\.5|[^,]*[−-]0\.5 \([^)]*\)", old)
    for clause in deductions:
        basis += ", " + clause.strip()
    basis += f" → 맛 {result['new_taste']:g}점 (0.5 단위 반올림)"
    if "kakao_total_count_proxy" in result["warnings"]:
        basis += ", 카카오 전체 후기 수 대용"
    return basis


def apply_scoring(place, as_of=None, *, manual_policy="preserve"):
    """Apply the simulation policy in place and return its calculation evidence.

    No usable rating means grade=None, effective_n=0, matching the simulation.
    Confidence describes the available samples even for a manual taste score.
    """
    result = calculate_taste(place, as_of or dt.date.today(), manual_policy=manual_policy)
    basis = taste_basis(place, result)
    place["axes"]["taste"]["s"] = result["new_taste"]
    place["axes"]["taste"].pop("rawTaste", None)
    place.pop("fewReviews", None)
    place["tasteBasis"] = basis
    place["confidence"] = {"grade": result["confidence"], "effective_n": result["effective_n"]}
    return result


