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
s.notes_slide.notes_text_frame.text = '【1分30秒】導入\n\n◆ 名乗り\n・Phase 4 の前半、フロントエンドと API 接続を担当します\n\n◆ 今日の立ち位置を図で示す\n・下の帯を指す：ブラウザ → Next.js → FastAPI → PostgreSQL\n・右の3つは前回まで（Phase 2 で DB、Phase 3 で API）\n・今日はその左端、Next.js を足す話\n\n◆ 今日話すこと・話さないこと\n・話す：実装の前に何を決めたか、決めた通りに動いたか\n・話さない：Next.js の全機能。1画面作るのに必要な判断だけ\n・結果として3画面を作ったので、机上の話ではなく実際に測った数字を出します\n\n◆ 一言添える\n・先に言っておくと、途中で一度つまずいています。そこが今日の山場（S9）\n'

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
s.notes_slide.notes_text_frame.text = '【1分30秒】全体像\n\n◆ 3テーマを読み上げる\n・境界＝処理をどこで動かすか\n・接続＝API をどう呼ぶか\n・画面＝機能をどこまで作るか\n\n◆ 右の列（困る時）を強調する\n・この3つは、どれも自分が実際に困った／困りかけたこと\n・「ページ全体が重くなる」「登録したのに一覧が古いまま」\n・「モックを7枚作ったが半分は年に数回しか使わない」\n\n◆ 形式の予告\n・各テーマ3枚ずつ。なぜ・困る時 → どう対応 → 実例\n・前回（第五回）と同じ形式にしています\n\n◆ ゴールの確認\n・学ぶのは機能ではなく判断\n・最後に、自分のアプリで決めることを3つ書き出す時間を取ります\n'

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
s.notes_slide.notes_text_frame.text = '【3分】Next.js はどこにいるか\n\n◆ 4層の図を上から順に\n・ブラウザ＝画面を見て操作する\n・Next.js＝画面を組み立てる。HTTP の入口\n・FastAPI＝Phase 3 で作った API\n・PostgreSQL＝Phase 2 で作った DB\n\n◆ ここが最初の発見\n・Next.js を「フロントを作るツール」だと思っていた\n・実際はサーバーとしても動く。Node のプロセスが立つ\n・npm run dev すると localhost:3000 でサーバーが起動している\n\n◆ だから経路が2つできる\n・(1) ブラウザ → Next.js（サーバー）→ FastAPI\n・(2) ブラウザ → FastAPI に直接\n・どちらを選ぶかで、書き方も、ブラウザから見える情報も変わる\n\n◆ 今日の1つ目のテーマにつなぐ\n・この「どちらで動かすか」が、次の「境界」の話\n\n◆ 補足（聞かれたら）\n・小さいアプリなら経路は1つでいい。分ける理由があるときだけ分ける\n・自分は(1)に統一した。理由は S8 で話します\n'

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
s.notes_slide.notes_text_frame.text = "【2分】境界：なぜ・困る時\n\n◆ 表を読む前に一言\n・「サーバーコンポーネント」は名前が紛らわしいと思っている\n・サーバーでしか動かない、という意味ではない\n・本質は右の列＝ブラウザに JavaScript を送るかどうか\n\n◆ 表の右列を指す\n・サーバー：送らない。HTML を組み立ててから渡す\n・クライアント：送る。ブラウザ上で JS が動いて描画する\n\n◆ 既定はサーバー\n・何も書かなければサーバー\n・'use client' と書いた時だけクライアントになる\n・この1行で、ブラウザに送るものが変わる\n\n◆ 困る例（右下のコード）\n・ページの先頭に 'use client' を書いてしまった場合\n・配下のコンポーネントが全部クライアント扱いになる\n・支出42件の一覧も、ブラウザ側で組み立てることになる\n・表示までに往復が増えて、一瞬「空っぽの画面」が見える\n\n◆ つなぎ\n・ではどこに書けばいいのか、が次の1枚\n"

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

note_box(s, 5.1, 3.16, 4.4, 1.00,
         "ページ（根）に 'use client' を書くと配下が全部クライアントになる。"
         "ただし layout の中にクライアント部品を「置く」のは別。"
         "その部品だけがクライアントで、children はサーバーのまま。",
         fill=PANEL, line=LINE, ink=INK, size=9.5,
         bold_head="原則： 'use client' は葉に付ける。根に付けない")

tf = textbox(s, ML, 3.62, 4.4, 0.5)
put(tf, [("今日の一手： ", {"bold": True, "color": BLUE}),
         ("最初に作る画面で、クライアントが必要な部品を1つだけ決める",)],
    size=10.5, first=True)

conclusion(s, 4.28,
           "既定はサーバー。操作がある部品だけをクライアントに切り出す。",
           accent=BLUE)
footer(s, 5)
s.notes_slide.notes_text_frame.text = "【2分】境界：どう対応するか\n\n◆ 判断は1問だけ、と言い切る\n・「ブラウザでしか出来ないことを使うか？」\n・Yes ならクライアント、No ならサーバー（＝何も書かない）\n\n◆ 左のリストを読む\n・onClick / onChange / onSubmit ＝ 操作への反応\n・useState ＝ 状態を持つ\n・useEffect ＝ 副作用\n・localStorage / window / document\n\n◆ 原則（右下のボックス）\n・'use client' は葉に付ける。根に付けない\n・根に付けると配下が全部クライアントになる（S4 の失敗パターン）\n\n◆ ここは混同しやすいので丁寧に\n・「layout にクライアント部品を置く」のは、根に 'use client' を書くのとは別\n・自分のアプリのナビがまさにこれ\n・ナビは現在地で色を変えるので usePathname が要る → クライアント\n・でも layout に置いても、children の3画面はサーバーのまま\n・つまり影響するのは「その部品自身」だけ\n\n◆ 今日の一手\n・最初に作る画面で、クライアントが必要な部品を1つだけ決める\n"

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
s.notes_slide.notes_text_frame.text = '【2分30秒】境界：実例\n\n◆ 上の表：3画面の振り分け\n・左がサーバー、右がクライアント\n・注目してほしいのは、行が「画面」なのに中身は「部品」で分かれていること\n・画面単位ではなく部品単位で決めた\n\n◆ 意外だった2つ（聞かれなくても話す）\n・カテゴリ別グラフはサーバーのままにできた\n  → ライブラリを使わず CSS の width % で棒を描いたので JS が要らなかった\n・絞り込みと月の切り替えもサーバーのまま\n  → useState ではなく URL に持たせた（/?category=1）ので <Link> の遷移で済む\n\n◆ 下の実測表\n・ファイル数は サーバー17 / クライアント8\n・ホーム画面を開いてブラウザが叩いた API は 0 件\n・サーバーが返す HTML に「¥16,640」がそのまま入っている\n\n【実演】ここで curl の結果を見せる\n・curl http://localhost:3000 | grep 16,640\n・ブラウザの Network タブを開いても API 通信が1件も出ないことを見せてもいい\n・これが S4 で言った「JS を送らない」の実物\n\n◆ 結論\n・画面ではなく部品で決める。表示はサーバー、操作はクライアント\n'

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
s.notes_slide.notes_text_frame.text = '【2分】接続：なぜ・困る時\n\n◆ 症状から入る\n・支出を登録した。DB には入っている。psql で確認できる\n・API も 201 を返している\n・なのに画面の一覧が古いまま\n\n◆ 中央のコードを指す\n・よくある書き方。fetch して json にする\n・これだけでは、更新後に再取得されるとは限らない\n\n◆ 切り分けるべき4点（右のリスト）\n・キャッシュされて古い結果が返っているのか\n・再取得の指示を出していないだけなのか\n・そもそも取得と更新で別の経路を使うべきなのか\n・使っているバージョンで既定の動きが変わっていないか\n\n◆ 伏線を張る\n・最後の1点が今日の山場。ここで自分は一度つまずいた\n・その話は2枚あと（S9）でします\n\n◆ このテーマの立場\n・取得と更新は別の問題として考える必要がある\n・同じ fetch でも扱いが違う、というのが次の枚\n'

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
s.notes_slide.notes_text_frame.text = "【3分】接続：どう対応するか\n\n◆ 表：経路を分ける\n・表示（GET）＝サーバーコンポーネント。async function にして直接 await\n・変更（POST/PATCH/DELETE）＝Server Actions。'use server' を書いて、最後に refresh()\n\n◆ 左右のコードを対比して見せる\n・左：Page が async。await apiGet して、その結果を渡すだけ\n・右：'use server' の関数。fetch した後 refresh() を呼ぶ\n\n◆ Server Actions を選んだ理由（3つ。ここは自分の判断として話す）\n・API の URL がブラウザに出ない。lib/api.ts に server-only を付けてある\n・CORS の設定が要らない。ブラウザは Next.js しか叩かないから\n・Phase 5 で JWT を HttpOnly Cookie に入れるとき、扱いがサーバー側で完結する\n\n◆ 下の実測表を読む\n・支出を1件登録した前後。ページ遷移はしていない\n・合計 ¥20,288 → ¥22,868、件数 9 → 10\n・外食カテゴリ ¥2,800（1件）→ ¥5,380（2件）\n・送金額 ¥1,896 → ¥3,186\n・ブラウザの API 呼び出しは前後とも 0\n\n◆ ここが言いたいこと\n・集計・グラフ・一覧・送金額が同時に更新されている\n・個別に取り直すコードは1行も書いていない。refresh() 1行だけ\n\n【実演】余裕があれば実際に登録して見せる\n・表の数字は測定したときの記録なので、その場で実演すると今の値から動きます\n・見せ方：合計と件数を読み上げてから登録 → 数字が一斉に変わるのを指す\n"

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
s.notes_slide.notes_text_frame.text = '【2分30秒】接続：実例（今日一番伝えたい話）\n\n◆ 何が起きたか\n・検索で出てきた記事を見ながら書こうとした\n・記事どうしで書き方が食い違っていた\n・調べたら、バージョンで作法が変わっていた\n\n◆ 表を読む（左が記事、右が実際）\n・fetch のキャッシュ：既定でキャッシュされる → されない\n・キャッシュ回避：no-store を明示 → 不要\n・更新後の反映：router.refresh() をクライアントで → refresh() を Server Action 内で\n・変更処理：クライアントから fetch(POST) → Server Actions\n\n◆ 決め手になったもの（右のコード）\n・npm run dev したら AGENTS.md というファイルが勝手に生成されていた\n・中身を読む：「This is NOT the Next.js you know」\n・「訓練データと違うかもしれない。node_modules の中のドキュメントを読め」\n・フレームワーク自身がバージョン差の問題を認めている\n\n【実演】実物を見せる\n・cat frontend/AGENTS.md\n\n◆ 読んだ結果わかったこと\n・ドキュメントが node_modules に同梱されている\n・動的ルートの params が Promise になっていた（await が要る）\n・記事のまま書いていたら動かないコードになっていた\n\n◆ 結論\n・バージョンを確認して、公式を一次情報にする。記事は補助\n・これは Next.js に限らず、他のライブラリでも同じだと思う\n'

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
s.notes_slide.notes_text_frame.text = '【2分】画面：なぜ・困る時\n\n◆ 最初に範囲を断る\n・ここは「どのページを作るか」の話\n・コンポーネントをどう分けるか（Feature-based など）は Phase 4 後半のテーマ\n\n◆ 経緯\n・設計フェーズでモックを7枚作った\n・実装量を見積もったら 12〜16 時間だった\n・多いと思って、使用頻度を書き出してみた\n\n◆ 表の真ん中の列を指す\n・ダッシュボード：毎日\n・支出一覧：週1〜月1\n・月次清算：月1\n・PayPay 取り込み：週1〜月1\n・カテゴリ管理：年に数回\n・アカウントメニュー：ほぼ使わない\n\n◆ 気づき\n・半分は年に数回しか使わない画面だった\n・設計しているときは全部必要に見えていた\n・使用頻度を書き出すまで気づかなかった\n\n◆ 問題提起\n・作る前に「作らないもの」を決めないと、使われない画面に時間を使う\n'

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
s.notes_slide.notes_text_frame.text = '【1分30秒】画面：どう対応するか\n\n◆ 3問を読み上げる\n・その画面を週1回以上使うか\n・他の画面に入れられないか\n・その画面が無いと運用が止まるか\n\n◆ 表の使い方\n・No が多いほど、独立した画面にする必要がない\n・No が3つなら作らない\n\n◆ ここが一番大事（中央のボックス）\n・機能を消すのではなく、画面を作らない\n・API とカラムは残したまま、UI だけ作らない\n・必要になったら画面を足すだけで済む\n\n◆ 自分の例で補足\n・カテゴリの API は Phase 3 で4本作ってある\n・is_archived カラムもある\n・でも管理画面は作らなかった。追加は入力欄の「+ 新規」で足りる\n\n◆ 今日の一手\n・自分のモックで、使用頻度が一番低い画面を1つ挙げる\n'

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
s.notes_slide.notes_text_frame.text = '【2分】画面：実例\n\n◆ 表を上から\n・ダッシュボード → 残す（ホームに改称）\n・支出一覧 → ホームに統合\n・月次清算、PayPay 取り込み → 残す（核心機能）\n・カテゴリ管理 → 廃止\n・ログイン → Phase 5 に送る（認証が前提なので）\n・アカウントメニュー → 廃止\n\n◆ 廃止した機能の行き先（左下）\n・消したのではなく、置き場所を変えただけだと伝える\n・支出一覧 → ホーム下部。編集は行内で直接\n・カテゴリ追加 → 入力欄の「+ 新規」\n・並び替え・アーカイブ → 作らない（API は残っている）\n\n◆ 得たもの\n・実装が概ね半分になった\n・Phase 5（認証）に早く進める\n\n◆ 代償も正直に話す\n・カテゴリの並び替えが UI からできない\n・モックを作り直す手間が発生した。PC 版とスマホ版で6枚\n・ただ、実装前に気づけたので手戻りは小さかった\n\n◆ 結論\n・使用頻度で切る。API を残しておけば後から画面を足せる\n'

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
s.notes_slide.notes_text_frame.text = "【3分】ワーク\n\n◆ 進め方を先に言う\n・3分取ります。手元のモックかコードを開いてください\n・3つを1行ずつ書く。書けたら1つだけ共有してもらいます（パスも可）\n\n◆ 3問を読み上げる\n・境界：最初に作る画面で 'use client' が必要な部品を1つ挙げる\n・接続：更新後に画面を更新する手段を決めたか。使う関数名を1つ書く\n・画面：作らないと決めた画面はあるか。1つ挙げる。無ければ「なし」\n\n◆ まだコードがない人へ（右下）\n・紙に書くだけでいい\n・作る予定の画面で、どこをクライアントにするか／どう更新するか／作らない画面はどれか\n\n◆ 時間を計る\n・3分経ったら声をかける\n・巡回して詰まっている人がいたら、自分の例を出して助ける\n  例：自分は「入力フォーム」「refresh()」「カテゴリ管理画面」と書いた\n\n◆ 共有のとき\n・1人1つでいい。全員に当てない\n"

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
s.notes_slide.notes_text_frame.text = "【1分30秒】まとめ\n\n◆ 3つを振り返る\n・境界：既定はサーバー。操作がある部品だけ 'use client'\n・接続：表示は await、変更は Server Actions。更新後に refresh()\n・画面：使用頻度が低い画面は作らない。API は残しておく\n\n◆ ここを強調する\n・3つ全部やろうとしないでほしい\n・決めた1つだけ、明日やる\n\n◆ 副産物\n・バージョンを確認して公式を読む。記事は補助に使う\n・Next.js 以外でも効く話だと思う\n\n◆ 締め\n・次回は Phase 4 後半、コンポーネント設計と UI ライブラリ\n・質問があれば\n\n◆ 想定質問への備え\n・「shadcn/ui は使わないのか」\n  → 今回は入れなかった。3画面で汎用部品が出てこなかったから。後半のテーマ\n・「型は生成しないのか」\n  → OpenAPI からの生成も検討したが、型が10個程度だったので手書きにした\n・「なぜ Server Actions？普通に fetch ではだめ？」\n  → S8 の3つの理由。特に Phase 5 の Cookie 認証を見据えて\n・「エラーはどう出している？」\n  → 422 は detail[].loc[1] を見て該当フィールドの下に日本語で出している\n"

# ============================================================
prs.save("phase4_frontend.pptx")
print(f"✓ phase4_frontend.pptx を作成（{len(prs.slides.__iter__.__self__._sldIdLst)}枚）")
