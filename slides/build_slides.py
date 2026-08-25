"""Phase 4 前半（Next.js・API接続）勉強会スライド生成スクリプト。

出力: phase4_frontend.pptx（14枚）

## Google スライド互換のための方針

- フォントは Arial のみ（Google スライドにも存在し、日本語は自動でフォールバックされる）
- 図形は矩形と直線のみ。グラデーション・影・回転を使わない
- 表は PowerPoint ネイティブの表オブジェクト（GraphicFrame）を使う
- テキストはすべてテキストフレーム（画像化しない）→ 選択・コピーできる
- スライドサイズは 10 x 5.625 インチ（16:9）= Google スライドの既定と同じ

実行:
    cd slides && python3 build_slides.py
"""
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

# ============================================================
# 配色（テーマごとに色を変える。第五回スライドの形式を踏襲）
# ============================================================
INK = RGBColor(0x11, 0x18, 0x27)        # 本文
SUB = RGBColor(0x6B, 0x72, 0x80)        # 補足
LINE = RGBColor(0xE5, 0xE7, 0xEB)       # 罫線
PANEL = RGBColor(0xF9, 0xFA, 0xFB)      # 薄い背景
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK = RGBColor(0x11, 0x18, 0x27)       # タイトルスライドの背景

BLUE = RGBColor(0x25, 0x63, 0xEB)       # テーマ1: 境界
GREEN = RGBColor(0x05, 0x96, 0x69)      # テーマ2: 接続
ORANGE = RGBColor(0xEA, 0x58, 0x0C)     # テーマ3: 画面

CODE_BG = RGBColor(0x1F, 0x29, 0x37)
CODE_FG = RGBColor(0xE5, 0xE7, 0xEB)
CODE_DIM = RGBColor(0x9C, 0xA3, 0xAF)

WARN_BG = RGBColor(0xFE, 0xFC, 0xE8)
WARN_LINE = RGBColor(0xFA, 0xCC, 0x15)
WARN_INK = RGBColor(0x71, 0x3F, 0x12)

OK_BG = RGBColor(0xF0, 0xFD, 0xF4)
OK_LINE = RGBColor(0x86, 0xEF, 0xAC)
OK_INK = RGBColor(0x16, 0x65, 0x34)

FONT = "Arial"

# レイアウト定数（インチ）
SW, SH = 10.0, 5.625      # スライド寸法
ML = 0.5                  # 左マージン
CW = 9.0                  # コンテンツ幅


# ============================================================
# ヘルパー
# ============================================================
def new_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    return prs


def blank(prs):
    """レイアウト6 = 白紙。"""
    return prs.slides.add_slide(prs.slide_layouts[6])


def textbox(slide, x, y, w, h, *, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    tf.paragraphs[0].alignment = align
    return tf


def put(tf, runs, *, size=12, color=INK, bold=False, space_before=0,
        space_after=0, align=None, line_spacing=None, first=False):
    """段落を1つ追加する。runs は str か (text, opts) のリスト。"""
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    if align is not None:
        p.alignment = align
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    if line_spacing is not None:
        p.line_spacing = line_spacing

    items = runs if isinstance(runs, list) else [runs]
    for item in items:
        if isinstance(item, str):
            text, opts = item, {}
        elif len(item) == 1:
            text, opts = item[0], {}
        else:
            text, opts = item
        r = p.add_run()
        r.text = text
        f = r.font
        f.name = FONT
        f.size = Pt(opts.get("size", size))
        f.bold = opts.get("bold", bold)
        f.color.rgb = opts.get("color", color)
    return p


def rect(slide, x, y, w, h, *, fill=None, line=None, line_w=1.0):
    from pptx.enum.shapes import MSO_SHAPE
    sh = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(line_w)
    sh.shadow.inherit = False
    # 図形内の既定テキストを空にする
    sh.text_frame.text = ""
    return sh


def hline(slide, x, y, w, *, color=LINE, width=1.0):
    from pptx.enum.shapes import MSO_CONNECTOR
    c = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y), Inches(x + w), Inches(y)
    )
    c.line.color.rgb = color
    c.line.width = Pt(width)
    return c


def header(slide, label, title, *, accent=INK, sub=None):
    """上部のラベル + 大きいタイトル（第五回スライドの形式）。"""
    tf = textbox(slide, ML, 0.34, CW, 0.24)
    put(tf, [(label, {"bold": True, "color": accent}), ],
        size=10.5, first=True)

    tf2 = textbox(slide, ML, 0.60, CW, 0.46)
    put(tf2, title, size=25, bold=True, color=INK, first=True)

    if sub:
        tf3 = textbox(slide, ML, 1.12, CW, 0.26)
        put(tf3, sub, size=11, color=SUB, first=True)


def footer(slide, page):
    tf = textbox(slide, SW - 4.1, SH - 0.38, 3.6, 0.26, align=PP_ALIGN.RIGHT)
    put(tf, f"Phase 4 前半 ｜ Next.js・API接続 ｜ {page} / 14",
        size=8.5, color=SUB, first=True)


def table(slide, x, y, w, rows_data, col_widths, *,
          header_fill=None, row_h=0.32, header_h=0.30, font_size=10):
    """ネイティブ表を作る。rows_data[0] がヘッダー行。"""
    nrows = len(rows_data)
    ncols = len(rows_data[0])
    total_h = header_h + row_h * (nrows - 1)
    gf = slide.shapes.add_table(
        nrows, ncols, Inches(x), Inches(y), Inches(w), Inches(total_h)
    )
    tbl = gf.table
    tbl.first_row = True
    tbl.horz_banding = False

    for i, cw in enumerate(col_widths):
        tbl.columns[i].width = Inches(cw)
    tbl.rows[0].height = Inches(header_h)
    for r in range(1, nrows):
        tbl.rows[r].height = Inches(row_h)

    hf = header_fill or RGBColor(0x37, 0x41, 0x51)
    for r, row in enumerate(rows_data):
        for c, cell_val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = Inches(0.07)
            cell.margin_right = Inches(0.07)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = hf if r == 0 else (
                WHITE if r % 2 == 1 else PANEL
            )

            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.space_before = Pt(0)
            p.space_after = Pt(0)

            # セル値は str か (text, {opts})
            if isinstance(cell_val, str):
                text, opts = cell_val, {}
            elif len(cell_val) == 1:
                text, opts = cell_val[0], {}
            else:
                text, opts = cell_val
            run = p.add_run()
            run.text = text
            f = run.font
            f.name = FONT
            f.size = Pt(opts.get("size", font_size))
            f.bold = opts.get("bold", r == 0)
            f.color.rgb = opts.get(
                "color", WHITE if r == 0 else INK
            )
    return tbl


def code_block(slide, x, y, w, lines, *, font_size=9, line_h=0.175, pad=0.11):
    """暗い背景のコードブロック。lines は str か (text, {opts})。"""
    h = pad * 2 + line_h * len(lines)
    rect(slide, x, y, w, h, fill=CODE_BG)
    tf = textbox(slide, x + pad, y + pad, w - pad * 2, h - pad * 2)
    for i, ln in enumerate(lines):
        if isinstance(ln, str):
            text, opts = ln, {}
        else:
            text, opts = ln
        put(tf, [(text, {"color": opts.get("color", CODE_FG),
                         "bold": opts.get("bold", False)})],
            size=opts.get("size", font_size), space_after=0,
            line_spacing=1.0, first=(i == 0))
    # 等幅フォントに変更
    for p in tf.paragraphs:
        for r in p.runs:
            r.font.name = "Courier New"
    return h


def note_box(slide, x, y, w, h, text, *, fill=WARN_BG, line=WARN_LINE,
             ink=WARN_INK, size=10, bold_head=None):
    rect(slide, x, y, w, h, fill=fill, line=line)
    tf = textbox(slide, x + 0.14, y + 0.10, w - 0.28, h - 0.20,
                 anchor=MSO_ANCHOR.MIDDLE)
    if bold_head:
        put(tf, [(bold_head, {"bold": True, "color": ink})], size=size,
            space_after=2, first=True)
        put(tf, [(text, {"color": ink})], size=size)
    else:
        put(tf, [(text, {"color": ink})], size=size, first=True)


def conclusion(slide, y, text, *, accent=INK):
    """スライド下部の「このテーマの結論」帯。"""
    rect(slide, ML, y, CW, 0.42, fill=PANEL, line=LINE)
    tf = textbox(slide, ML + 0.16, y + 0.09, CW - 0.32, 0.26,
                 anchor=MSO_ANCHOR.MIDDLE)
    put(tf, [("結論： ", {"bold": True, "color": accent}),
             (text, {"color": INK})], size=11, first=True)


# ============================================================
# スライド
# ============================================================
prs = new_deck()

# ---------- S1 タイトル ----------
s = blank(prs)
rect(s, 0, 0, SW, SH, fill=DARK)

tf = textbox(s, 0.7, 1.16, 8.6, 0.26)
put(tf, [("Phase 4 前半", {"bold": True, "color": RGBColor(0xFB, 0xBF, 0x24)}),
         ("　｜　フロントエンド（Next.js・API接続）",
          {"color": RGBColor(0x9C, 0xA3, 0xAF)})],
    size=11, first=True)

tf = textbox(s, 0.7, 1.52, 8.6, 0.95)
put(tf, "Next.js と API 接続", size=36, bold=True, color=WHITE, first=True)
put(tf, "― 決めてから、作って確かめた", size=19,
    color=RGBColor(0xD1, 0xD5, 0xDB), space_before=6)

hline(s, 0.7, 2.78, 4.3, color=RGBColor(0x4B, 0x55, 0x63), width=1.2)

tf = textbox(s, 0.7, 2.95, 8.6, 0.24)
put(tf, "2026-08-19 ｜ 30分", size=10.5,
    color=RGBColor(0x9C, 0xA3, 0xAF), first=True)

tf = textbox(s, 0.7, 3.42, 8.6, 0.26)
put(tf, [("今日のトピック： ", {"bold": True, "color": WHITE}),
         ("境界 / 接続 / 画面", {"bold": True,
                               "color": RGBColor(0xFB, 0xBF, 0x24)}),
         (" の3つの判断", {"color": RGBColor(0xD1, 0xD5, 0xDB)})],
    size=13, first=True)

tf = textbox(s, 0.7, 3.80, 8.6, 0.26)
put(tf, [("ゴール： ", {"bold": True, "color": WHITE}),
         ("「境界・接続・画面」を自分のアプリでどうするか、自分で判断できるようになる",
          {"color": RGBColor(0xD1, 0xD5, 0xDB)})],
    size=13, first=True)

tf = textbox(s, 0.7, 4.42, 8.6, 0.24)
put(tf, "ブラウザ  →  Next.js  →  FastAPI  →  PostgreSQL",
    size=11.5, color=RGBColor(0x9C, 0xA3, 0xAF), first=True)
tf = textbox(s, 0.7, 4.70, 8.6, 0.24)
put(tf, "Phase 3 で右の3つを作った。今日はその左端を足す話",
    size=9.5, color=RGBColor(0x6B, 0x72, 0x80), first=True)
s.notes_slide.notes_text_frame.text = (
    "自己紹介と範囲の確認。Phase 3 で API までできている前提。"
    "今日は「実装前に何を決めたか」を話す。"
)

# ---------- S2 今日の3テーマ ----------
s = blank(prs)
header(s, "全体像 ｜ 今日の3テーマ", "学ぶこととゴール",
       sub="3つとも学ぶのは「判断」。答えはこの後で出す")

table(s, ML, 1.52, CW,
      [["テーマ", "学ぶ判断", "こういう時に困る"],
       [("境界", {"bold": True, "color": BLUE}),
        "処理を\nどこで動かすか",
        "ページ全体が重くなり、表示前に空の画面が見える"],
       [("接続", {"bold": True, "color": GREEN}),
        "API を\nどう呼ぶか",
        "登録したのに、一覧が古いまま変わらない"],
       [("画面", {"bold": True, "color": ORANGE}),
        "機能を\nどこまで作るか",
        "モックを7枚作ったが、半分は年に数回しか使わない"]],
      [1.1, 2.5, 5.4], row_h=0.52, header_h=0.30, font_size=10.5)

note_box(s, ML, 3.62, CW, 0.62,
         "今日は Next.js の全機能ではなく、"
         "画面を1つ作るときに必要な判断だけを扱う。",
         fill=PANEL, line=LINE, ink=INK, size=11,
         bold_head="今日の立場")

tf = textbox(s, ML, 4.44, CW, 0.5)
put(tf, [("ゴール： ", {"bold": True}),
         ("「境界・接続・画面」を自分のアプリでどうするか、自分で判断できるようになる",)],
    size=11.5, first=True)
put(tf, "そのために最後に、自分のアプリで決めることを3つ書き出す時間を取る",
    size=10, color=SUB, space_before=4)
footer(s, 2)
s.notes_slide.notes_text_frame.text = (
    "第五回と同じ形式。3テーマそれぞれを「なぜ・困る時 → どう対応 → 実例」で回す。"
)

# ---------- S3 Next.js はどこにいるか ----------
s = blank(prs)
header(s, "ARCHITECTURE ｜ 3分", "Next.js はどこにいるか",
       sub="Phase 3 で作った層の左に、もう1つ層が乗る")

# 層の図
layers = [
    ("ブラウザ", "画面を見る・操作する", PANEL, INK, LINE),
    ("Next.js", "画面を組み立てる／HTTP の入口", BLUE, WHITE, None),
    ("FastAPI", "API（Phase 3 で作った）", RGBColor(0x1F, 0x29, 0x37), WHITE, None),
    ("PostgreSQL", "永続化（Phase 2 で作った）", RGBColor(0x37, 0x41, 0x51), WHITE, None),
]
y = 1.58
for name, desc, fill, ink, ln in layers:
    rect(s, ML, y, 4.05, 0.62, fill=fill, line=ln)
    tf = textbox(s, ML + 0.16, y + 0.10, 3.7, 0.42)
    put(tf, name, size=13, bold=True, color=ink, first=True)
    put(tf, desc, size=9,
        color=(SUB if fill == PANEL else RGBColor(0xD1, 0xD5, 0xDB)),
        space_before=1)
    y += 0.76

points = [
    "Next.js は「画面を作るツール」だけではなく、"
    "サーバーとしても動く。",
    "だから API を呼ぶ経路が2つできる。"
    "Next.js から呼ぶか、ブラウザから直接呼ぶか。",
    "どちらで呼ぶかで、書き方も見え方も変わる。"
    "これが今日の1つ目「境界」の話。",
    "小さいアプリなら経路は1つでよい。"
    "分ける理由があるときだけ分ける。",
]
ty = 1.62
for pt_text in points:
    rect(s, 4.85, ty, 0.09, 0.09, fill=BLUE)
    tf = textbox(s, 5.08, ty - 0.04, 4.42, 0.62)
    put(tf, pt_text, size=10.5, first=True, line_spacing=1.18)
    ty += 0.72

footer(s, 3)
s.notes_slide.notesated = None if False else None
s.notes_slide.notes_text_frame.text = (
    "Phase 3 の S5「FastAPI はどこにいるか」の対応版。"
    "層が1つ増えただけ、と伝える。"
)

# ============================================================
# テーマ1：境界
# ============================================================

# ---------- S4 境界：なぜ・困る時 ----------
s = blank(prs)
header(s, "境界 ｜ サーバーとクライアント", "なぜ・困る時：ページ全体が重くなった",
       accent=BLUE)

table(s, ML, 1.42, CW,
      [["", "意味", "ブラウザに JavaScript を送るか"],
       [("サーバー\nコンポーネント", {"bold": True}),
        "サーバーで HTML を組み立ててから送る",
        "送らない"],
       [("クライアント\nコンポーネント", {"bold": True}),
        "ブラウザ上で JavaScript が動いて描画する",
        "送る"]],
      [1.9, 4.1, 3.0], row_h=0.46, header_h=0.28, font_size=10.5)

tf = textbox(s, ML, 3.02, CW, 0.24)
put(tf, [("なぜ必要か： ", {"bold": True, "color": BLUE}),
         ("既定はサーバー。'use client' と書いた時だけクライアントになる。"
          "この1行で、送るものが変わる。",)],
    size=10.5, first=True)

tf = textbox(s, ML, 3.34, 4.5, 0.9)
put(tf, [("こういう時に困る： ", {"bold": True, "color": BLUE}),
         ("ページの先頭に 'use client' を書いた",)], size=10.5, first=True)
for line in ["配下のコンポーネントが全部クライアントになる",
             "支出42件の一覧も、ブラウザ側で組み立てることになる",
             "表示までに4往復。一瞬「空っぽの画面」が見える"]:
    put(tf, "・" + line, size=10, color=INK, space_before=3)

code_block(s, 5.2, 3.34, 4.3,
           [("app/expenses/page.tsx", {"color": CODE_DIM}),
            ("'use client'", {"color": RGBColor(0xFC, 0xA5, 0xA5), "bold": True}),
            "",
            "export default function Page() {",
            "  // ここから下は全部クライアント扱い",
            "  return <ExpenseList items={...} />",
            "}"],
           font_size=8.5)

footer(s, 4)
s.notes_slide.notes_text_frame.text = (
    "「サーバーコンポーネント」は名前が紛らわしい。"
    "サーバーでしか動かないのではなく、ブラウザに JS を送らないのが本質。"
)

# ---------- S5 境界：どう対応 ----------
s = blank(prs)
header(s, "境界 ｜ サーバーとクライアント", "どう対応するか：判断は1問だけ",
       accent=BLUE)

note_box(s, ML, 1.44, CW, 0.52,
         "ブラウザでしか出来ないことを使うか？",
         fill=RGBColor(0xEF, 0xF6, 0xFF), line=BLUE, ink=BLUE, size=15)

tf = textbox(s, ML, 2.12, 4.4, 1.3)
put(tf, "「ブラウザでしか出来ないこと」とは", size=11.5, bold=True, first=True)
for line in ["onClick / onChange / onSubmit（操作への反応）",
             "useState / useReducer（状態を持つ）",
             "useEffect（副作用）",
             "localStorage / window / document"]:
    put(tf, "・" + line, size=10, space_before=4)

rows = [["答え", "どうする"],
        [("Yes", {"bold": True}), "クライアント（'use client' を書く）"],
        [("No", {"bold": True}), "サーバー（既定。何も書かない）"]]
table(s, 5.1, 2.14, 4.4, rows, [1.0, 3.4], row_h=0.34,
      header_h=0.28, font_size=10.5)

note_box(s, 5.1, 3.28, 4.4, 0.66,
         "ページ（根）に付けると配下が全部クライアントになる。"
         "操作がある部品にだけ付ける。",
         fill=PANEL, line=LINE, ink=INK, size=10,
         bold_head="原則： 'use client' は葉に付ける。根に付けない")

tf = textbox(s, ML, 3.62, 4.4, 0.5)
put(tf, [("今日の一手： ", {"bold": True, "color": BLUE}),
         ("最初に作る画面で、クライアントが必要な部品を1つだけ決める",)],
    size=10.5, first=True)

conclusion(s, 4.28,
           "既定はサーバー。操作がある部品だけをクライアントに切り出す。",
           accent=BLUE)
footer(s, 5)
s.notes_slide.notes_text_frame.text = "判断基準を1問に絞るのがポイント。"

# ---------- S6 境界：実例 ----------
s = blank(prs)
header(s, "境界 ｜ サーバーとクライアント", "対応の実例：作って測ってみた",
       accent=BLUE, sub="3画面を実装した結果。クライアントにしたのは「操作がある部品」だけ")

table(s, ML, 1.52, CW,
      [["画面", "サーバー（表示だけ）", "クライアント（操作がある）"],
       [("ホーム", {"bold": True}),
        "集計・カテゴリ別グラフ・支出一覧・ページ送り",
        "入力フォーム・絞り込み・行内編集"],
       [("月次清算", {"bold": True}),
        "集計・送金額・内訳・月ナビ・過去履歴",
        "「確認する」ボタン"],
       [("PayPay 取り込み", {"bold": True}),
        "未判定の一覧・判定済み履歴",
        "CSV 選択・1行ごとの判定"]],
      [1.7, 3.9, 3.4], row_h=0.40, header_h=0.26, font_size=9.5)

# 実測値
tf = textbox(s, ML, 3.04, CW, 0.24)
put(tf, [("3画面を作り終えた時点の内訳と、ホーム画面での計測",
          {"bold": True, "color": BLUE})], size=11, first=True)

table(s, ML, 3.30, 5.5,
      [["計測項目", "結果"],
       ["ファイル数（サーバー / クライアント）",
        ("17 / 8", {"bold": True, "color": BLUE})],
       ["ブラウザから叩いた API の数",
        ("0 件", {"bold": True, "color": BLUE})],
       ["サーバーが返す HTML に「¥ 16,640」",
        ("含まれる", {"bold": True, "color": BLUE})]],
      [3.3, 2.2], row_h=0.27, header_h=0.25, font_size=9.5)

tf = textbox(s, 6.2, 3.30, 3.3, 1.2)
put(tf, "つまり", size=10.5, bold=True, first=True)
put(tf, "ブラウザは API を1回も呼んでいないのに、"
        "データが表示されている。", size=9.5, space_before=4,
    line_spacing=1.15)
put(tf, "クライアントにしたのは入力・絞り込み・ボタンなど"
        "「操作がある部品」8つだけ。",
    size=9.5, space_before=4, line_spacing=1.15)

conclusion(s, 4.62,
           "画面ではなく部品で決める。表示はサーバー、操作はクライアント。",
           accent=BLUE)
footer(s, 6)
s.notes_slide.notes_text_frame.text = (
    "curl でサーバーの HTML を見せると一発で伝わる。"
    "ブラウザの Network タブを開いても API 通信が1件も出ない、"
    "というのが S4 で言った「JS を送らない」の実物。"
)

# ============================================================
# テーマ2：接続
# ============================================================

# ---------- S7 接続：なぜ・困る時 ----------
s = blank(prs)
header(s, "接続 ｜ データの取得と更新",
       "なぜ・困る時：登録したのに一覧が変わらない", accent=GREEN)

tf = textbox(s, ML, 1.40, CW, 0.24)
put(tf, [("なぜ必要か： ", {"bold": True, "color": GREEN}),
         ("取得と更新は別の問題として考える必要がある。"
          "同じ fetch でも、扱いが違う。",)], size=10.5, first=True)

tf = textbox(s, ML, 1.74, 4.5, 0.9)
put(tf, [("こういう時に困る： ", {"bold": True, "color": GREEN}),
         ("支出を登録した",)], size=10.5, first=True)
for line in ["DB には入っている（psql で確認できる）",
             "API も 201 を返している",
             "でも画面の一覧は古いまま"]:
    put(tf, "・" + line, size=10, space_before=3)

code_block(s, 5.2, 1.74, 4.3,
           [("よくある書き方", {"color": CODE_DIM}),
            "const res = await fetch(url)",
            "const data = await res.json()",
            "",
            ("これだけでは、更新後に", {"color": CODE_DIM}),
            ("再取得されるとは限らない", {"color": CODE_DIM})],
           font_size=8.5)

tf = textbox(s, ML, 2.94, CW, 1.2)
put(tf, "この症状から切り分けるべきこと", size=11.5, bold=True, first=True)
for line in ["キャッシュされていて古い結果が返っているのか",
             "再取得の指示を出していないだけなのか",
             "そもそも取得と更新で別の経路を使うべきなのか",
             "（使っているバージョンで、既定の動きが変わっていないか）"]:
    put(tf, "・" + line, size=10, space_before=4)

note_box(s, ML, 4.28, CW, 0.52,
         "最後の1点が今日の山場。ここで一度つまずいた。",
         fill=WARN_BG, line=WARN_LINE, ink=WARN_INK, size=10.5)
footer(s, 7)
s.notes_slide.notes_text_frame.text = (
    "S9 への伏線。バージョン差の話につなげる。"
)

# ---------- S8 接続：どう対応 ----------
s = blank(prs)
header(s, "接続 ｜ データの取得と更新",
       "どう対応するか：取得と更新で経路を分ける", accent=GREEN)

table(s, ML, 1.42, CW,
      [["操作", "経路", "書き方"],
       [("表示（GET）", {"bold": True}),
        "サーバーコンポーネント",
        "async function にして直接 await する"],
       [("変更（POST / PATCH / DELETE）", {"bold": True}),
        "Server Actions",
        "'use server' を書き、最後に refresh() を呼ぶ"]],
      [2.6, 2.6, 3.8], row_h=0.40, header_h=0.28, font_size=10)

code_block(s, ML, 2.46, 4.4,
           [("表示：サーバーコンポーネント", {"color": CODE_DIM}),
            "export default async function Page() {",
            "  const data = await apiGet('/api/expenses/')",
            "  return <ExpenseList items={data.items} />",
            "}"],
           font_size=8, line_h=0.16)

code_block(s, 5.2, 2.46, 4.3,
           [("変更：Server Actions", {"color": CODE_DIM}),
            ("'use server'", {"color": RGBColor(0x86, 0xEF, 0xAC), "bold": True}),
            "export async function createExpense(fd) {",
            "  await fetch(API + '/api/expenses/', {...})",
            ("  refresh()", {"color": RGBColor(0x86, 0xEF, 0xAC)}),
            "}"],
           font_size=8, line_h=0.16)

tf = textbox(s, ML, 3.54, CW, 0.24)
put(tf, [("実際に支出を1件登録したときの変化（ページ遷移なし）",
          {"bold": True, "color": GREEN})], size=10.5, first=True)

table(s, ML, 3.80, CW,
      [["", "合計", "件数", "外食カテゴリ", "送金額", "ブラウザのAPI呼び出し"],
       ["送信前", "¥20,288", "9 件", "¥2,800（1件）", "¥1,896", "0"],
       ["送信後",
        ("¥22,868", {"bold": True, "color": GREEN}),
        ("10 件", {"bold": True, "color": GREEN}),
        ("¥5,380（2件）", {"bold": True, "color": GREEN}),
        ("¥3,186", {"bold": True, "color": GREEN}),
        ("0", {"bold": True})]],
      [1.0, 1.5, 0.9, 1.9, 1.3, 2.4], row_h=0.26, header_h=0.26,
      font_size=9)

tf = textbox(s, ML, 4.58, CW, 0.22)
put(tf, "集計・グラフ・一覧が同時に更新される。個別に取り直すコードは書いていない（refresh() 1行だけ）",
    size=9.5, color=INK, first=True)

conclusion(s, 4.84,
           "表示はサーバーで await、変更は Server Actions。更新後は refresh()。",
           accent=GREEN)
footer(s, 8)
s.notes_slide.notes_text_frame.text = (
    "経路を分けるのが結論。Server Actions は Phase 5 の認証にも効く。"
    "Server Actions を選んだ理由: API の URL がブラウザに出ない / "
    "CORS 設定が不要 / Phase 5 で Cookie を扱うとき有利。"
)

# ---------- S9 接続：実例（山場） ----------
s = blank(prs)
header(s, "接続 ｜ データの取得と更新",
       "対応の実例：調べたら記事と違っていた", accent=GREEN)

tf = textbox(s, ML, 1.40, CW, 0.24)
put(tf, [("条件： ", {"bold": True, "color": GREEN}),
         ("検索で出てきた記事を見ながら書こうとした。"
          "書き方が記事どうしで食い違っていた。",)], size=10.5, first=True)

table(s, ML, 1.70, CW,
      [["項目", "記事に多い情報（13〜14）", "実際（16.3.1）"],
       ["fetch のキャッシュ", "既定でキャッシュされる",
        ("キャッシュされない", {"bold": True})],
       ["キャッシュ回避", "{ cache: 'no-store' } を明示",
        ("不要（既定がその動き）", {"bold": True})],
       ["更新後の画面反映", "router.refresh() をクライアントで",
        ("refresh() を Server Action 内で", {"bold": True})],
       ["変更処理", "クライアントから fetch(POST)",
        ("Server Actions", {"bold": True})]],
      [2.1, 3.5, 3.4], row_h=0.30, header_h=0.26, font_size=9.5)

# Next.js 自身の警告（このスライドの決定打）
tf = textbox(s, ML, 3.16, CW, 0.24)
put(tf, [("しかも、Next.js 自身が警告していた",
          {"bold": True, "color": GREEN}),
         ("　― npm run dev が AGENTS.md を自動生成する",
          {"color": SUB, "size": 9.5})], size=11, first=True)

code_block(s, ML, 3.44, 5.4,
           [("# This is NOT the Next.js you know",
             {"color": RGBColor(0xFC, 0xA5, 0xA5), "bold": True}),
            "",
            "This version has breaking changes — APIs,",
            "conventions, and file structure may all",
            "differ from your training data. Read the",
            "relevant guide in node_modules/next/dist/",
            "docs/ before writing any code."],
           font_size=7.5, line_h=0.142, pad=0.09)

tf = textbox(s, 6.1, 3.44, 3.4, 1.3)
put(tf, [("読み取れること", {"bold": True})], size=10, first=True)
put(tf, "・フレームワーク自身がバージョン差の問題を認めている",
    size=9, space_before=4, line_spacing=1.12)
put(tf, "・ドキュメントが node_modules に同梱されている",
    size=9, space_before=3, line_spacing=1.12)
put(tf, "・読んだ結果、動的ルートの params が Promise だと分かった",
    size=9, space_before=3, line_spacing=1.12)

conclusion(s, 4.86,
           "バージョンを確認して、公式を一次情報にする。記事は補助に使う。",
           accent=GREEN)
footer(s, 9)
s.notes_slide.notes_text_frame.text = (
    "今日一番伝えたい話。動かないコードを書く前に気づけた。"
    "Next.js は 13→16 で作法が変わっている。"
    "AGENTS.md は next dev が自動生成するもので、"
    "フレームワーク側がバージョン差の問題を認識している証拠になる。"
    "やったこと: 公式でバージョン確認 → 記事は 13〜14 時代と判明 → 計画を書き直した。"
    "代償: 公式を読む時間、日本語記事が使えない場面、毎回バージョンを確認する手間。"
)

# ============================================================
# テーマ3：画面
# ============================================================

# ---------- S10 画面：なぜ・困る時 ----------
s = blank(prs)
header(s, "画面 ｜ 作る範囲を決める",
       "なぜ・困る時：7画面のモックを作ったが多すぎた", accent=ORANGE,
       sub="「どのページを作るか」の話。"
           "コンポーネントの分け方（Feature-based など）は Phase 4 後半のテーマ")

tf = textbox(s, ML, 1.52, CW, 0.24)
put(tf, [("なぜ必要か： ", {"bold": True, "color": ORANGE}),
         ("作る前に「作らないもの」を決めないと、"
          "使われない画面に時間を使う。",)], size=10.5, first=True)

tf = textbox(s, ML, 1.84, CW, 0.24)
put(tf, [("こういう時に困る： ", {"bold": True, "color": ORANGE}),
         ("設計フェーズでモックを7枚作った。実装量を見積もったら 12〜16 時間だった。",)],
    size=10.5, first=True)

table(s, ML, 2.18, CW,
      [["当初の画面", "使用頻度", "実装の重さ"],
       ["ダッシュボード", ("毎日", {"bold": True}), "重い"],
       ["支出一覧", "週1〜月1", "中"],
       ["月次清算", ("月1", {"bold": True}), "中"],
       ["PayPay 取り込み", "週1〜月1", "重い"],
       ["カテゴリ管理", ("年に数回", {"bold": True, "color": ORANGE}), "中"],
       ["ログイン", "（認証は Phase 5）", "中"],
       ["アカウントメニュー", ("ほぼ使わない", {"bold": True, "color": ORANGE}),
        "軽い"]],
      [3.4, 3.2, 2.4], row_h=0.25, header_h=0.25, font_size=9.5)

note_box(s, ML, 4.34, CW, 0.48,
         "使用頻度を書き出したら、半分は年に数回しか使わない画面だった。",
         fill=WARN_BG, line=WARN_LINE, ink=WARN_INK, size=10.5)
footer(s, 10)
s.notes_slide.notes_text_frame.text = (
    "使用頻度を書き出すまで気づかなかった。設計時は全部必要に見えていた。"
    "なお、これは「どのページを作るか」の話で、"
    "コンポーネントの粒度（Feature-based など）は後半のテーマだと一言添える。"
)

# ---------- S11 画面：どう対応 ----------
s = blank(prs)
header(s, "画面 ｜ 作る範囲を決める", "どう対応するか：使用頻度で切る",
       accent=ORANGE)

tf = textbox(s, ML, 1.44, CW, 0.24)
put(tf, "画面を1つずつ、この3問にかける。No が多いほど独立させる必要がない。",
    size=10.5, color=SUB, first=True)

qs = [("1.", "その画面を週1回以上使うか"),
      ("2.", "他の画面に入れられないか"),
      ("3.", "その画面が無いと運用が止まるか")]
qy = 1.80
for num, q in qs:
    tf = textbox(s, ML, qy, 5.0, 0.28)
    put(tf, [(num + " ", {"bold": True, "color": ORANGE}),
             (q, {"bold": True})], size=12, first=True)
    qy += 0.38

table(s, 5.5, 1.80, 4.0,
      [["No の数", "やること"],
       [("0", {"bold": True}), "そのまま作る"],
       [("1〜2", {"bold": True}), "他の画面に統合する"],
       [("3", {"bold": True}), "作らない（API は残す）"]],
      [1.2, 2.8], row_h=0.32, header_h=0.28, font_size=10)

note_box(s, ML, 3.08, CW, 0.62,
         "API とカラムは残したまま、UI だけ作らない。"
         "必要になったら画面を足すだけで済む。",
         fill=PANEL, line=LINE, ink=INK, size=10.5,
         bold_head="大事な点： 機能を消すのではなく、画面を作らない")

tf = textbox(s, ML, 3.86, CW, 0.5)
put(tf, [("今日の一手： ", {"bold": True, "color": ORANGE}),
         ("自分のモックで、使用頻度が一番低い画面を1つ挙げる",)],
    size=10.5, first=True)

conclusion(s, 4.48,
           "使用頻度が低い画面は独立させない。API は残して UI だけ作らない。",
           accent=ORANGE)
footer(s, 11)
s.notes_slide.notes_text_frame.text = "YAGNI の実践。判断を3問に落とす。"

# ---------- S12 画面：実例 ----------
s = blank(prs)
header(s, "画面 ｜ 作る範囲を決める", "対応の実例：7画面 → 3画面",
       accent=ORANGE)

table(s, ML, 1.46, 5.3,
      [["当初の画面", "判断"],
       ["ダッシュボード", "残す（ホームに改称）"],
       ["支出一覧", ("ホームに統合", {"bold": True, "color": ORANGE})],
       ["月次清算", "残す"],
       ["PayPay 取り込み", "残す"],
       ["カテゴリ管理", ("廃止", {"bold": True, "color": ORANGE})],
       ["ログイン", "Phase 5 に送る"],
       ["アカウントメニュー", ("廃止", {"bold": True, "color": ORANGE})]],
      [2.6, 2.7], row_h=0.26, header_h=0.26, font_size=9.5)

tf = textbox(s, 6.15, 1.46, 3.35, 1.4)
put(tf, "廃止した機能の行き先", size=11, bold=True, first=True)
for line in ["支出一覧 → ホーム下部に統合。編集は行内で",
             "カテゴリ追加 → 入力欄の「+ 新規」",
             "並び替え・アーカイブ → 作らない",
             "表示名・パスワード変更 → Phase 5"]:
    put(tf, "・" + line, size=9.5, space_before=4, line_spacing=1.1)

note_box(s, 6.15, 3.02, 3.35, 0.72,
         "実装が概ね半分になり、Phase 5 に早く進める。",
         fill=OK_BG, line=OK_LINE, ink=OK_INK, size=10,
         bold_head="得たもの")

tf = textbox(s, ML, 3.52, 5.3, 0.62)
put(tf, [("代償", {"bold": True, "color": ORANGE})], size=11, first=True)
put(tf, "・カテゴリの並び替えが UI からできない（API は残してある）",
    size=9.5, space_before=3)
put(tf, "・モックを作り直す手間が発生した（PC 版とスマホ版で6枚）",
    size=9.5, space_before=3)

conclusion(s, 4.44,
           "使用頻度で切る。API を残しておけば、後から画面を足せる。",
           accent=ORANGE)
footer(s, 12)
s.notes_slide.notes_text_frame.text = (
    "モックの作り直しは代償として正直に話す。"
    "ただ実装前に気づけたので手戻りは小さかった。"
)

# ---------- S13 宿題 ----------
s = blank(prs)
header(s, "自分のアプリへ ｜ 3つを決める", "自分のアプリで決めること",
       sub="手元のモックかコードを開いて、3つを1行ずつ書く")

items = [
    ("1.", "境界", BLUE,
     "最初に作る画面で、'use client' が必要な部品を1つ挙げる"),
    ("2.", "接続", GREEN,
     "更新後に画面を更新する手段を決めたか（使う関数名を1つ書く）"),
    ("3.", "画面", ORANGE,
     "作らないと決めた画面はあるか（1つ挙げる。無ければ「なし」）"),
]
iy = 1.60
for num, name, col, desc in items:
    rect(s, ML, iy, 0.42, 0.42, fill=col)
    tf = textbox(s, ML, iy + 0.10, 0.42, 0.24, align=PP_ALIGN.CENTER)
    put(tf, num.rstrip("."), size=13, bold=True, color=WHITE, first=True)

    tf = textbox(s, ML + 0.58, iy + 0.02, 8.4, 0.42)
    put(tf, [(name, {"bold": True, "color": col, "size": 13}),
             ("　" + desc, {"size": 11})], first=True)
    iy += 0.72

note_box(s, ML, 3.86, CW, 0.60,
         "作る予定の画面で「どこをクライアントにするか・どう更新するか・"
         "作らない画面はどれか」を紙に書く。",
         fill=PANEL, line=LINE, ink=INK, size=10.5,
         bold_head="まだコードがない人")

tf = textbox(s, ML, 4.64, CW, 0.3)
put(tf, "書けたら、1つだけ共有してください（パス可）",
    size=10.5, color=SUB, first=True)
footer(s, 13)
s.notes_slide.notes_text_frame.text = (
    "3分ほど時間を取る。第五回と同じ形式。"
)

# ---------- S14 まとめ ----------
s = blank(prs)
rect(s, 0, 0, SW, SH, fill=DARK)

tf = textbox(s, 0.7, 0.62, 8.6, 0.24)
put(tf, "まとめ ｜ 明日やる1つ", size=10.5, bold=True,
    color=RGBColor(0xFB, 0xBF, 0x24), first=True)

tf = textbox(s, 0.7, 0.92, 8.6, 0.5)
put(tf, "明日やる1つを決める", size=28, bold=True, color=WHITE, first=True)

tf = textbox(s, 0.7, 1.62, 8.6, 0.26)
put(tf, [("今日のキーワード： ", {"color": RGBColor(0x9C, 0xA3, 0xAF)}),
         ("境界 / 接続 / 画面", {"bold": True, "color": WHITE})],
    size=13, first=True)

summary = [
    ("境界", BLUE, "既定はサーバー。操作がある部品だけ 'use client' を付ける"),
    ("接続", GREEN, "表示は await、変更は Server Actions。更新後に refresh()"),
    ("画面", ORANGE, "使用頻度が低い画面は作らない。API は残しておく"),
]
sy = 2.08
for name, col, desc in summary:
    rect(s, 0.7, sy, 0.14, 0.30, fill=col)
    tf = textbox(s, 0.98, sy + 0.02, 8.3, 0.28)
    put(tf, [(name, {"bold": True, "color": WHITE, "size": 12.5}),
             ("　" + desc, {"color": RGBColor(0xD1, 0xD5, 0xDB), "size": 11})],
        first=True)
    sy += 0.52

rect(s, 0.7, 3.72, 8.6, 0.52, fill=RGBColor(0x1F, 0x29, 0x37),
     line=RGBColor(0x4B, 0x55, 0x63))
tf = textbox(s, 0.9, 3.84, 8.2, 0.30, anchor=MSO_ANCHOR.MIDDLE)
put(tf, [("3つ全部ではなく、決めた1つだけ。",
          {"bold": True, "color": WHITE})], size=13, first=True)

tf = textbox(s, 0.7, 4.52, 8.6, 0.26)
put(tf, [("今日の副産物： ", {"color": RGBColor(0x9C, 0xA3, 0xAF)}),
         ("バージョンを確認して公式を読む。記事は補助に使う。",
          {"color": RGBColor(0xD1, 0xD5, 0xDB)})],
    size=11, first=True)

tf = textbox(s, 0.7, 4.86, 8.6, 0.26)
put(tf, "次回：Phase 4 後半（コンポーネント設計・UI ライブラリ）",
    size=10.5, color=RGBColor(0x6B, 0x72, 0x80), first=True)
s.notes_slide.notes_text_frame.text = (
    "3つ全部やらせないのが大事。1つに絞る。"
)

# ============================================================
prs.save("phase4_frontend.pptx")
print(f"✓ phase4_frontend.pptx を作成（{len(prs.slides.__iter__.__self__._sldIdLst)}枚）")
