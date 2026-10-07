#!/usr/bin/env python3
"""店舗サイトの外国語版（英・简・繁・韓）を、生成済みの日本語ページから作る。

  python3 tools/i18n.py                   # tempura washoku naniwa 全部
  python3 tools/i18n.py tempura           # 1サイトだけ
  python3 tools/i18n.py tempura --no-api  # 辞書にある訳だけで作る（未訳は日本語のまま）

- 出力: <site>/en/ <site>/zh-hans/ <site>/zh-hant/ <site>/ko/ に日本語と同じファイル名。
  画像・動画・CSS は ../ で日本語版のものを参照する（コピーしない）。
- 翻訳: tools/i18n/<lang>.json（原文→訳）が辞書。未訳の文字列だけ OpenAI でまとめて訳して足す。
  訳を直したい時は辞書の値を書き換えれば次回からそれが使われる。
  API が失敗しても止めない（その文字列は日本語のまま出し、次回また訳しに行く）。
- 日本語ページにも言語切替と hreflang を差し込む（何度流しても同じ結果になる）。
毎朝 tools/tabelog_menu.py の最後から呼ばれる。
"""
import html, json, os, re, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DICT_DIR = ROOT / "tools" / "i18n"
SITES = {
    "tempura": "https://tempuraoshio.com/",
    "washoku": "https://washoku-oshio.com/",
    "naniwa": "https://takoyakinaniwa.com/",
}
# (lang属性, ディレクトリ, 切替の表示, 地図のhl)
LANGS = [("en", "en", "EN", "en"), ("zh-Hans", "zh-hans", "简", "zh-CN"),
         ("zh-Hant", "zh-hant", "繁", "zh-TW"), ("ko", "ko", "한", "ko")]
LANG_NAME = {"en": "English", "zh-Hans": "Simplified Chinese (zh-Hans, mainland China)",
             "zh-Hant": "Traditional Chinese (zh-Hant, Taiwan / Hong Kong)", "ko": "Korean"}
JA_NOTE = {"en": "Japanese page", "zh-Hans": "日文页面", "zh-Hant": "日文頁面", "ko": "일본어 페이지"}
MODEL = os.environ.get("I18N_MODEL", "gpt-4.1")
RESERVE_RE = re.compile(r"yoyaku\.|hotpepper\.jp/str[^\"]*/yoyaku|toreta\.in")
JP = re.compile(r"[぀-ヿ㐀-鿿豈-﫿！-｠　-〿]")
TOKEN = re.compile(r"(<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>|<[^>]+>)", re.S)
ATTR = re.compile(r'(\s(?:alt|title|aria-label|placeholder|content)=")([^"]*)(")')

# 店名など、訳のぶれを許さない語（プロンプトに渡す）
GLOSSARY = {
    "en": """天ぷらとワイン 大塩 = Tempura & Wine Oshio (shops: 日比谷店 Hibiya, 有楽町店 Yurakucho, 丸の内店 Marunouchi, 中野店 Nakano, 天満市場店 Tenma Ichiba, 天五横丁店 Tengo Yokocho, 大阪駅前第三ビル店 Osaka Ekimae Dai-3 Bldg, 梅田店 Umeda) e.g. 天ぷらとワイン 大塩 日比谷店 = Tempura & Wine Oshio Hibiya
和食 大塩 = Washoku Oshio
たこ焼き酒場 なにわ = Takoyaki Sakaba Naniwa
株式会社アゲル = AGERU Inc. / 株式会社丹波農商 = Tamba Nosho Co., Ltd. / 丹波 = Tamba (Hyogo)
大阪駅前第三ビル / 第三ビル = Osaka Ekimae Dai-3 Building
L.O. = Last order""",
    "zh-Hans": """天ぷらとワイン 大塩 = 天妇罗与葡萄酒 大塩 (分店: 日比谷店, 有乐町店, 丸之内店, 中野店, 天满市场店, 天五横丁店, 大阪站前第三大厦店, 梅田店)
和食 大塩 = 和食 大塩 / たこ焼き酒场 なにわ = 章鱼烧酒场 Naniwa
株式会社アゲル = AGERU 株式会社 / 株式会社丹波農商 = 株式会社丹波农商
L.O. = 最后点餐""",
    "zh-Hant": """天ぷらとワイン 大塩 = 天婦羅與葡萄酒 大塩 (分店: 日比谷店, 有樂町店, 丸之內店, 中野店, 天滿市場店, 天五橫丁店, 大阪站前第三大樓店, 梅田店)
和食 大塩 = 和食 大塩 / たこ焼き酒場 なにわ = 章魚燒酒場 Naniwa
株式会社アゲル = AGERU 株式會社 / 株式会社丹波農商 = 株式會社丹波農商
L.O. = 最後點餐""",
    "ko": """天ぷらとワイン 大塩 = 덴푸라 & 와인 오시오 (지점: 日比谷店 히비야점, 有楽町店 유라쿠초점, 丸の内店 마루노우치점, 中野店 나카노점, 天満市場店 덴마 이치바점, 天五横丁店 덴고 요코초점, 大阪駅前第三ビル店 오사카역앞 제3빌딩점, 梅田店 우메다점)
和食 大塩 = 와쇼쿠 오시오 / たこ焼き酒場 なにわ = 다코야키 사카바 나니와
株式会社アゲル = 주식회사 AGERU / 株式会社丹波農商 = 주식회사 단바노쇼
L.O. = 라스트 오더""",
}
DISH_RULE = {
    "en": 'Write Japanese dish names as "Romaji (English)", e.g. 海老天 -> "Ebi Tempura (Shrimp)", 季節の野菜天 -> "Seasonal Vegetable Tempura". Drinks: brand names as they are, then a short English hint when helpful, e.g. 獺祭 -> "Dassai (Junmai Daiginjo Sake)".',
    "zh-Hans": "菜名用简体中文自然表达（如 海老天 -> 炸虾天妇罗）。酒类品牌保留原名，必要时加简短说明。",
    "zh-Hant": "菜名用繁體中文自然表達（如 海老天 -> 炸蝦天婦羅）。酒類品牌保留原名，必要時加簡短說明。",
    "ko": '요리명은 일본어 발음을 한글로 쓰고 괄호 안에 뜻을 붙인다 (예: 海老天 -> "에비텐 (새우 튀김)"). 술 브랜드는 원래 이름을 살린다.',
}

# 日付・価格のように毎日変わる文字列は API に回さず型で訳す
PATTERNS = [
    (re.compile(r"^税込価格／(\S+) 時点$"), {"en": "Prices include tax / as of {0}", "zh-Hans": "含税价格／截至 {0}",
                                          "zh-Hant": "含稅價格／截至 {0}", "ko": "세금 포함 가격 / {0} 기준"}),
    (re.compile(r"^([0-9,]+)円$"), {k: "¥{0}" for k in ("en", "zh-Hans", "zh-Hant", "ko")}),
]

# ヘッダーのナビだけ短い訳にする（PCで1行に収める）
NAV_SHORT = {
    "旬に勝る素材なし": {"en": "Seasonal", "zh-Hans": "时令食材", "zh-Hant": "時令食材", "ko": "제철 재료"},
    "会社概要": {"en": "Company", "zh-Hans": "公司简介", "zh-Hant": "公司簡介", "ko": "회사 소개"},
    "ご予約": {"en": "Reserve", "zh-Hans": "预约", "zh-Hant": "預約", "ko": "예약"},
    "店舗・メニュー": {"en": "Locations", "zh-Hans": "店铺・菜单", "zh-Hant": "店鋪・菜單", "ko": "매장・메뉴"},
}

_lock = threading.Lock()


def load_dict(lang):
    p = DICT_DIR / f"{lang.lower()}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save_dict(lang, d):
    DICT_DIR.mkdir(exist_ok=True)
    p = DICT_DIR / f"{lang.lower()}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(sorted(d.items())), ensure_ascii=False, indent=1) + "\n")
    tmp.replace(p)


def api_key():
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k
    p = Path.home() / ".openai_env"
    if p.exists():
        for line in p.read_text().splitlines():
            m = re.match(r"\s*(?:export\s+)?OPENAI_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line)
            if m:
                return m.group(1)
    return None


def call_openai(key, lang, items):
    """items: [(id, kind, text)] -> {id: 訳}。失敗は例外。"""
    sys_prompt = f"""You translate the website of a Japanese restaurant group into {LANG_NAME[lang]}.
Return a JSON object mapping each id to its translation. Translate every item; never omit ids.
Style: warm, natural, concise restaurant copy for travellers. Use "we/our" (first person plural) for the restaurant. Keep a positive tone; no negative wording. No dialect.
Keep numbers, prices, times, dates, phone numbers, URLs and symbols exactly as written (convert 円 prices to ¥ form, e.g. 1,280円 -> ¥1,280).
Keep line breaks: if the source has N "\\n", the translation must have the same N "\\n" at the matching places.
Days of week: translate compactly (en: Mon, Tue ... / Mon–Thu; 祝 = public holidays; 祝前日 = day before a holiday).
Person names: en = given name + family name in romaji (北村 光穂 -> Mitsuho Kitamura); zh = keep kanji; ko = Hangul reading.
Do not promote unlimited drinking in copy: avoid words like "all-you-can-drink"/"free-flow" except when it is literally a menu item name.
kind=dish means a menu item name. {DISH_RULE[lang]}
kind=addr means a Japanese address: translate it into the local address format, keeping all numbers.
Fixed names:
{GLOSSARY[lang]}"""
    payload = {"model": MODEL, "temperature": 0.2, "response_format": {"type": "json_object"},
               "messages": [{"role": "system", "content": sys_prompt},
                            {"role": "user", "content": json.dumps({"items": [{"id": i, "kind": k, "text": t} for i, k, t in items]}, ensure_ascii=False)}]}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.loads(json.loads(r.read())["choices"][0]["message"]["content"])
    return {str(k): v for k, v in out.items() if isinstance(v, str) and v.strip()}


def translate_missing(need, use_api=True):
    """need: {lang: {text: kind}}。辞書にないものを API で訳して辞書へ。"""
    dicts = {lang: load_dict(lang) for lang, *_ in LANGS}
    jobs = []
    for lang, texts in need.items():
        todo = [(t, k) for t, k in texts.items() if t not in dicts[lang]]
        for i in range(0, len(todo), 40):
            jobs.append((lang, todo[i:i + 40]))
    if not jobs:
        return dicts
    key = api_key() if use_api else None
    if not key:
        print(f"i18n: 未訳 {sum(len(c) for _, c in jobs)} 件（APIを使わないので日本語のまま出します）")
        return dicts

    def run(job):
        lang, chunk = job
        items = [(str(n), k, t) for n, (t, k) in enumerate(chunk)]
        for attempt in range(3):
            try:
                out = call_openai(key, lang, items)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"i18n: {lang} の翻訳に失敗（{type(e).__name__}）。{len(chunk)}件は日本語のまま")
                    return 0
                time.sleep(5 * (attempt + 1))
        got = 0
        with _lock:
            for n, (t, k) in enumerate(chunk):
                v = out.get(str(n))
                if v and not (lang != "zh-Hans" and lang != "zh-Hant" and re.search("[\u3041-\u3096\u30a1-\u30fa]", v)):
                    dicts[lang][t] = v
                    got += 1
            save_dict(lang, dicts[lang])
        return got

    with ThreadPoolExecutor(8) as ex:
        n = sum(ex.map(run, jobs))
    print(f"i18n: 新しく訳した {n} 件")
    return dicts


# ---------------------------------------------------------------- ページの分解と組み立て

def strip_injected(t):
    t = re.sub(r"\n?<!-- i18n:start -->.*?<!-- i18n:end -->", "", t, flags=re.S)
    t = re.sub(r'<div class="lang-switch"[^>]*>.*?</div>\n?\s*', "", t, flags=re.S)
    return t


def is_page_link(v):
    return bool(re.match(r"^[\w.-]+\.html(#.*)?$", v))


def segments(t):
    """日本語を含むテキストのかたまり（<br>でつながった文字列）を順に返す。
    yield: (開始token番号, 終了token番号, 前の前のタグ, 直前のタグ, 文字列)"""
    toks = TOKEN.split(t)
    i, prev_tags = 0, ["", ""]
    while i < len(toks):
        tk = toks[i]
        if i % 2 == 1 and not re.match(r"<br\s*/?>", tk, re.I):
            prev_tags = [prev_tags[1], tk]
            i += 1
            continue
        j, parts = i, []
        while j < len(toks) and (j % 2 == 0 or re.match(r"<br\s*/?>", toks[j], re.I)):
            parts.append("\n" if j % 2 else toks[j])
            j += 1
        raw = "".join(parts)
        if JP.search(raw):
            yield i, j, prev_tags[0], prev_tags[1], raw
        i = max(j, i + 1)


def kind_of(text, before2, before):
    if re.match(r"^(東京都|大阪市|大阪府|兵庫県)", text):
        return "addr"
    if before == "<b>" and 'class="line"' in before2:
        return "dish"
    if before == "<figcaption>" and "menu-img/" in before2:
        return "dish"
    return "text"


def split_ws(s):
    m = re.match(r"^(\s*)(.*?)(\s*)$", s, re.S)
    return m.group(1), m.group(2), m.group(3)


def norm(core):
    """ <br> のまわりの空白をならし、エンティティを戻した原文（辞書のキー） """
    return "\n".join(x.strip() for x in html.unescape(core).split("\n"))


def collect(t, need):
    t = strip_injected(t)
    for _, _, b2, b1, raw in segments(t):
        core = norm(split_ws(raw)[1])
        if not any(p.match(core) for p, _ in PATTERNS):
            need.setdefault(core, kind_of(core, b2, b1))
    for tag in TOKEN.split(t)[1::2]:
        if tag.startswith(("<!--", "<script", "<style")):
            continue
        for _, v, _ in ATTR.findall(tag):
            v = html.unescape(v)
            if JP.search(v):
                need.setdefault(v, "dish" if "menu-img/" in tag else "text")
    for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
        for k, v in json.loads(ld).items():
            if k in ("servesCuisine",):
                for x in v:
                    need.setdefault(x, "text")


def tr(s, lang, d):
    for p, fmt in PATTERNS:
        m = p.match(s)
        if m:
            return fmt[lang].format(*m.groups())
    return d.get(s, s)


def tr_addr(s, lang, d):
    """住所は原文を残し、英語・韓国語は訳を上に併記（中国語は原文で読める）"""
    if lang.startswith("zh"):
        return s
    v = d.get(s)
    return f"{v}\n{s}" if v and v != s else s


def switcher(cur_lang, fname, depth):
    up = "../" if depth else ""
    links = [("ja", f"{up}{fname}", "日本語")] + [(lg, f"{up}{dr}/{fname}", lab) for lg, dr, lab, _ in LANGS]
    on = ' class="on" aria-current="true"'
    a = "".join(f'<a href="{h}" hreflang="{lg}" lang="{lg}"{on if lg == cur_lang else ""}>{lab}</a>' for lg, h, lab in links)
    return f'<div class="lang-switch" aria-label="Language">{a}</div>\n  '


def head_block(base, fname, cur_dir):
    page = "" if fname == "index.html" else fname
    url = lambda d: base + (d + "/" if d else "") + page
    lines = [f'<link rel="alternate" hreflang="ja" href="{url("")}">']
    lines += [f'<link rel="alternate" hreflang="{lg}" href="{url(dr)}">' for lg, dr, _, _ in LANGS]
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{url("")}">')
    lines.append(f'<link rel="canonical" href="{url(cur_dir)}">')
    return "\n<!-- i18n:start -->\n" + "\n".join(lines) + "\n<!-- i18n:end -->"


def inject(t, base, fname, cur_lang, cur_dir, depth):
    t = strip_injected(t)
    t = re.sub(r'\n?<link rel="canonical"[^>]*>', "", t)
    t = t.replace("</head>", head_block(base, fname, cur_dir).lstrip("\n") + "\n</head>", 1)
    t = t.replace('<button class="menu-btn"', switcher(cur_lang, fname, depth) + '<button class="menu-btn"', 1)
    return t


def translate_page(t, lang, d, dirname, maphl):
    t = strip_injected(t)
    toks = TOKEN.split(t)
    # 1) テキスト
    nav = (toks.index("<nav>"), toks.index("</nav>")) if "<nav>" in toks and "</nav>" in toks else (-1, -1)
    for i, j, b2, b1, raw in list(segments(t)):
        lead, core, trail = split_ws(raw)
        key = norm(core)
        if nav[0] < i < nav[1] and key in NAV_SHORT:
            v = NAV_SHORT[key][lang]
        else:
            v = tr_addr(key, lang, d) if kind_of(key, b2, b1) == "addr" else tr(key, lang, d)
        toks[i] = lead + html.escape(v, quote=False).replace("\n", "<br>") + trail
        for x in range(i + 1, j):
            toks[x] = ""
    # 2) タグ：属性の訳・相対パス・予約リンクの注記
    in_reserve = False
    for n in range(1, len(toks), 2):
        tag = toks[n]
        if tag.startswith("<script") and "application/ld+json" in tag:
            m = re.match(r'(<script type="application/ld\+json">)(.*?)(</script>)', tag, re.S)
            ld = json.loads(m.group(2))
            ld["alternateName"] = tr(ld["name"], lang, d)
            ld["servesCuisine"] = [tr(x, lang, d) for x in ld.get("servesCuisine", [])]
            for k in ("url", "menu"):
                if k in ld:
                    ld[k] = re.sub(r"^(https://[^/]+/)", r"\g<1>" + dirname + "/", ld[k])
            ld["inLanguage"] = lang
            toks[n] = m.group(1) + json.dumps(ld, ensure_ascii=False) + m.group(3)
            continue
        if tag.startswith(("<!--", "<script", "<style")) and not tag.startswith("<script src"):
            if tag.startswith("<!--") and JP.search(tag):
                toks[n] = ""
            continue
        if tag.startswith("<html"):
            tag = re.sub(r'lang="[^"]*"', f'lang="{lang}"', tag)
        tag = ATTR.sub(lambda m: m.group(1) + html.escape(tr(html.unescape(m.group(2)), lang, d)) + m.group(3)
                       if JP.search(m.group(2)) else m.group(0), tag)

        def rel(m):
            v = m.group(2)
            if re.match(r"^(https?:|//|#|mailto:|tel:|data:|javascript:)", v) or is_page_link(v) or v.startswith("../"):
                return m.group(0)
            return m.group(1) + "../" + v + m.group(3)
        tag = re.sub(r'(\s(?:src|href|poster)=")([^"]*)(")', rel, tag)
        tag = tag.replace("hl=ja", f"hl={maphl}")
        if tag.startswith("<a ") and RESERVE_RE.search(tag) and re.search(r'class="btn\b', tag):
            in_reserve = True
        elif tag == "</a>" and in_reserve:
            tag = f'<small class="ja-page">（{JA_NOTE[lang]}）</small></a>' if lang.startswith("zh") else f'<small class="ja-page">({JA_NOTE[lang]})</small></a>'
            in_reserve = False
        toks[n] = tag
    return "".join(toks)


def build_site(site, use_api=True):
    d = ROOT / site
    base = SITES[site]
    pages = sorted(p for p in d.glob("*.html"))
    need = {lg: {} for lg, *_ in LANGS}
    srcs = {}
    for p in pages:
        t = p.read_text()
        srcs[p.name] = strip_injected(t)
        tmp = {}
        collect(t, tmp)
        for lg in need:
            for k, v in tmp.items():
                need[lg].setdefault(k, v)
    dicts = translate_missing(need, use_api)
    for p in pages:
        # 日本語ページ：切替と hreflang だけ差し込む（中身はそのまま）
        t0 = p.read_text()
        t1 = inject(srcs[p.name], base, p.name, "ja", "", 0)
        if t1 != t0:
            p.write_text(t1)
        for lg, dr, _, hl in LANGS:
            out = d / dr
            out.mkdir(exist_ok=True)
            body = translate_page(srcs[p.name], lg, dicts[lg], dr, hl)
            body = inject(body, base, p.name, lg, dr, 1)
            f = out / p.name
            if not f.exists() or f.read_text() != body:
                f.write_text(body)
    # 日本語側から消えたページは外国語版も消す
    for _, dr, _, _ in LANGS:
        for f in (d / dr).glob("*.html"):
            if not (d / f.name).exists():
                f.unlink()
    left = {lg: sum(1 for k in need[lg] if k not in dicts[lg]) for lg in need}
    print(f"{site}: {len(pages)}ページ × {len(LANGS)}言語 / 未訳 {left}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for s in args or list(SITES):
        try:
            build_site(s, use_api="--no-api" not in sys.argv)
        except Exception as e:  # 同期を止めない
            print(f"i18n: {s} で失敗: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
