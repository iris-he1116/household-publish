"""PayPay CSV のパース（純関数のみ・DB 不要）。

実物の CSV（PayPay アプリの出力）で判明した仕様を固定する。
実データは個人情報なのでリポジトリに置かない。ここでは同じ形の最小データを作る。
"""
from datetime import date, datetime

import pytest

from app.services.paypay_import import (
    _parse_csv,
    is_expense_row,
    parse_amount,
    parse_occurred_on,
)

# 実物と同じ13列のヘッダ
HEADER = (
    "取引日,出金金額（円）,入金金額（円）,海外出金金額,通貨,変換レート（円）,"
    "利用国,取引内容,取引先,取引方法,支払い区分,利用者,取引番号"
)


def _row(*, dt, out="-", in_="-", kind="支払い", merchant="テスト店", txn="1"):
    return f'{dt},{out},{in_},-,-,-,-,{kind},{merchant},PayPay残高,-,-,{txn}'


class TestParseAmount:
    def test_カンマ入りを読める(self):
        assert parse_amount('3,984') == 3984

    def test_カンマなしを読める(self):
        assert parse_amount('981') == 981

    def test_1万以上のカンマを読める(self):
        assert parse_amount('14,303') == 14303

    @pytest.mark.parametrize("bad", ["-", "", "   "])
    def test_空欄は例外(self, bad):
        with pytest.raises(ValueError):
            parse_amount(bad)


class TestParseOccurredOn:
    def test_実物の日時形式(self):
        # 実物は「2026/08/30 21:15:57」。時刻は落として日付だけにする
        assert parse_occurred_on("2026/08/30 21:15:57") == date(2026, 8, 30)

    def test_ISO形式も受ける(self):
        assert parse_occurred_on("2026-08-30") == date(2026, 8, 30)

    def test_読めない形式は例外(self):
        with pytest.raises(ValueError):
            parse_occurred_on("30 Aug 2026")


class TestIsExpenseRow:
    def test_支払いは対象(self):
        assert is_expense_row("支払い") is True

    @pytest.mark.parametrize("kind", ["チャージ", "ポイント、残高の獲得", "送った金額"])
    def test_それ以外は対象外(self, kind):
        # チャージ＝口座から残高への移動、ポイント＝入金、送金＝共有支出に含めない方針
        assert is_expense_row(kind) is False


class TestParseCsv:
    def _parse(self, *rows):
        text = "\n".join([HEADER, *rows])
        return _parse_csv(text, imported_by=1, imported_at=datetime(2026, 9, 1))

    def test_支払いだけ取り込む(self):
        rows = self._parse(
            _row(dt="2026/08/30 21:15:57", out='"3,984"', txn="A"),
            _row(dt="2026/08/30 19:54:46", in_='"10,000"', kind="チャージ", txn="B"),
            _row(dt="2026/08/29 21:10:51", in_="10", kind="ポイント、残高の獲得", txn="C"),
            _row(dt="2026/08/27 09:53:56", out='"4,300"', kind="送った金額", txn="D"),
        )
        assert [r["paypay_txn_id"] for r in rows] == ["A"]

    def test_同じ取引番号の支払いとポイントが混ざっても重複しない(self):
        # 実物では13組あったパターン。ポイント側が落ちるので UNIQUE に当たらない
        rows = self._parse(
            _row(dt="2026/08/09 21:10:51", out='"2,144"', txn="SAME"),
            _row(dt="2026/08/09 21:10:51", in_="10", kind="ポイント、残高の獲得", txn="SAME"),
        )
        assert len(rows) == 1
        assert rows[0]["amount"] == 2144

    def test_店舗名が取引先から取れる(self):
        rows = self._parse(
            _row(dt="2026/08/30 21:15:57", out="981", merchant="サンプルストア - テスト駅前店")
        )
        assert rows[0]["merchant_name"] == "サンプルストア - テスト駅前店"

    def test_店舗名が空欄なら_None(self):
        rows = self._parse(_row(dt="2026/08/30 21:15:57", out="981", merchant="-"))
        assert rows[0]["merchant_name"] is None

    def test_壊れた行はスキップして他は取り込む(self):
        # 1行の不備で取り込み全体を落とさない
        rows = self._parse(
            _row(dt="2026/08/30 21:15:57", out="981", txn="OK1"),
            _row(dt="こわれた日付", out="500", txn="NG"),
            _row(dt="2026/08/28 10:00:00", out="不明", txn="NG2"),
            _row(dt="2026/08/27 10:00:00", out="700", txn="OK2"),
        )
        assert [r["paypay_txn_id"] for r in rows] == ["OK1", "OK2"]

    def test_取引番号が空の行はスキップ(self):
        rows = self._parse(_row(dt="2026/08/30 21:15:57", out="981", txn=""))
        assert rows == []

    def test_raw_row_に元データを保持する(self):
        rows = self._parse(_row(dt="2026/08/30 21:15:57", out="981", txn="A"))
        assert rows[0]["raw_row"]["取引内容"] == "支払い"
