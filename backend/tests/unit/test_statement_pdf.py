"""明細PDFパーサーのテスト。実際の個人明細はテストデータに含めない。"""
from datetime import date

import pytest

from app.services.statement_pdf import _parse_mufg, _parse_smcc, parse_statement_pdf


class FakePage:
    def __init__(self, tables):
        self.tables = tables

    def extract_tables(self):
        return self.tables


class FakePdf:
    def __init__(self, pages):
        self.pages = pages


def test_smccの利用日と利用店と支払金額を読む():
    row = [None, "", "26/03/05", "サンプル書店", "1,200", "1", "1", "1,200"]
    result = _parse_smcc(
        FakePdf([FakePage([[row]])]),  # type: ignore[arg-type]
        "お支払い日 2026年4月27日",
    )

    assert len(result.rows) == 1
    assert result.rows[0].occurred_on == date(2026, 3, 5)
    assert result.rows[0].merchant_name == "サンプル書店"
    assert result.rows[0].amount == 1200
    assert result.rows[0].payment_method == "credit_card"


def test_smccの同一内容の行を別取引として扱う():
    row = [None, "", "26/03/05", "サンプル書店", "150", "1", "1", "150"]
    result = _parse_smcc(
        FakePdf([FakePage([[row, row]])]),  # type: ignore[arg-type]
        "お支払い日 2026年4月27日",
    )

    assert len(result.rows) == 2
    assert result.rows[0].source_key != result.rows[1].source_key


def test_mufgは出金のみ読み入金を除外しページ跨ぎも結合する():
    first_page = [
        ["日付", "お支払い", "お預かり", "お取引内容", "差引残高", "メモ"],
        ["2026年\n4月1日", "1,000 円", "", "電気料金", "9,000 円", ""],
        ["2026年\n4月2日", "", "2,000 円", "振込入金", "11,000 円", ""],
        ["2026年", "3,000 円", "", "カードC1", "8,000 円", ""],
    ]
    # 2ページ目の余白を含む10列形式。日付だけが前ページの行の続き。
    second_page = [["", "", "4月3日", "", "", "", "", "", "", ""]]
    result = _parse_mufg(  # type: ignore[arg-type]
        FakePdf([FakePage([first_page]), FakePage([second_page])])
    )

    assert result.skipped_rows == 1
    assert [(row.occurred_on, row.amount) for row in result.rows] == [
        (date(2026, 4, 1), 1000),
        (date(2026, 4, 3), 3000),
    ]
    assert result.rows[1].merchant_name == "カードC1"
    assert result.rows[0].payment_method == "bank_account"


def test未対応_pdfは明確に失敗する(monkeypatch):
    class UnsupportedPdf:
        def __init__(self):
            self.pages = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr("app.services.statement_pdf.pdfplumber.open", lambda _stream: UnsupportedPdf())
    with pytest.raises(ValueError, match="未対応のPDF"):
        parse_statement_pdf(b"%PDF-test")
