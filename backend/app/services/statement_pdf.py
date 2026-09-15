"""Digitally-generated statement PDF parsers.

Only the supported table layouts are accepted.  We intentionally do not run
OCR: a scanned or changed document must fail clearly instead of silently
creating inaccurate household expenses.
"""
from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import pdfplumber

from app.services.paypay_import import parse_amount


@dataclass(frozen=True)
class ParsedStatementRow:
    occurred_on: date
    amount: int
    merchant_name: str
    source_key: str
    source_type: str
    source_label: str
    payment_method: str
    raw_row: dict[str, str]


@dataclass(frozen=True)
class ParsedStatement:
    source_type: str
    source_label: str
    rows: list[ParsedStatementRow]
    skipped_rows: int


def _clean(value: object) -> str:
    text = "" if value is None else str(value)
    return " ".join(unicodedata.normalize("NFKC", text).split())


def _key(prefix: str, *parts: object) -> str:
    stable = "\x1f".join(_clean(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(stable.encode('utf-8')).hexdigest()}"


def _first_text(pdf: pdfplumber.PDF) -> str:
    return "\n".join((page.extract_text() or "") for page in pdf.pages[:2])


def _parse_smcc(pdf: pdfplumber.PDF, document_text: str) -> ParsedStatement:
    payment_match = re.search(r"お支払い日\s*(\d{4})年(\d{1,2})月(\d{1,2})日", document_text)
    statement_id = payment_match.group(0) if payment_match else "支払日不明"
    occurrences: Counter[tuple[str, str, int]] = Counter()
    parsed: list[ParsedStatementRow] = []

    for page in pdf.pages:
        for table in page.extract_tables():
            for cells in table:
                if len(cells) < 8:
                    continue
                used_on_text = _clean(cells[2])
                if not re.fullmatch(r"\d{2}/\d{2}/\d{2}", used_on_text):
                    continue
                merchant = _clean(cells[3])
                try:
                    used_on = date(
                        2000 + int(used_on_text[0:2]),
                        int(used_on_text[3:5]),
                        int(used_on_text[6:8]),
                    )
                    amount = parse_amount(_clean(cells[7]) or _clean(cells[4]))
                except (ValueError, IndexError):
                    continue

                identity = (used_on.isoformat(), merchant, amount)
                occurrences[identity] += 1
                occurrence = occurrences[identity]
                parsed.append(
                    ParsedStatementRow(
                        occurred_on=used_on,
                        amount=amount,
                        merchant_name=merchant or "利用店名なし",
                        source_key=_key("smcc", statement_id, *identity, occurrence),
                        source_type="smcc",
                        source_label="三井住友カード",
                        payment_method="credit_card",
                        raw_row={
                            "利用日": used_on_text,
                            "利用店名": merchant,
                            "支払金額": str(amount),
                            "明細内同一取引番号": str(occurrence),
                        },
                    )
                )

    if not parsed:
        raise ValueError("三井住友カードPDFから利用明細を読み取れませんでした")
    return ParsedStatement("smcc", "三井住友カード", parsed, 0)


def _mufg_cells(cells: Sequence[object]) -> tuple[str, str, str, str, str] | None:
    if len(cells) == 6:
        selected = cells[:5]
    elif len(cells) >= 7:
        selected = cells[2:7]
    else:
        return None
    return tuple(_clean(value) for value in selected)  # type: ignore[return-value]


def _mufg_date(value: str) -> date | None:
    match = re.fullmatch(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", value)
    if not match:
        return None
    return date(*(int(part) for part in match.groups()))


def _parse_mufg(pdf: pdfplumber.PDF) -> ParsedStatement:
    table_rows: list[tuple[str, str, str, str, str]] = []
    for page in pdf.pages:
        for table in page.extract_tables():
            for cells in table:
                normalized = _mufg_cells(cells)
                if normalized is not None:
                    table_rows.append(normalized)

    # MUFG sometimes divides a transaction at a page break: one row contains
    # only "2026年" and the next starts with "4月28日".  Join only those
    # adjacent fragments, leaving ordinary complete rows untouched.
    joined: list[tuple[str, str, str, str, str]] = []
    pending: tuple[str, str, str, str, str] | None = None
    for current in table_rows:
        current_date = current[0]
        if re.fullmatch(r"\d{4}年", current_date):
            pending = current
            continue
        if pending is not None and re.fullmatch(r"\d{1,2}月\s*\d{1,2}日", current_date):
            merged = tuple(
                (pending[index] + current[index]) if index == 0 else (pending[index] or current[index])
                for index in range(5)
            )
            joined.append(merged)  # type: ignore[arg-type]
            pending = None
            continue
        if _mufg_date(current_date) is not None:
            joined.append(current)

    parsed: list[ParsedStatementRow] = []
    skipped = 0
    for occurred_text, withdrawal_text, deposit_text, description, balance in joined:
        occurred_on = _mufg_date(occurred_text)
        if occurred_on is None:
            continue
        if not withdrawal_text:
            if deposit_text:
                skipped += 1
            continue
        try:
            amount = parse_amount(withdrawal_text)
        except ValueError:
            continue
        merchant = description or "取引内容なし"
        parsed.append(
            ParsedStatementRow(
                occurred_on=occurred_on,
                amount=amount,
                merchant_name=merchant,
                source_key=_key("mufg", occurred_text, amount, merchant, balance),
                source_type="mufg",
                source_label="三菱UFJ銀行",
                payment_method="bank_account",
                raw_row={
                    "日付": occurred_text,
                    "出金": str(amount),
                    "取引内容": merchant,
                    "残高": balance,
                },
            )
        )

    if not parsed:
        raise ValueError("三菱UFJ銀行PDFから出金明細を読み取れませんでした")
    return ParsedStatement("mufg", "三菱UFJ銀行", parsed, skipped)


def parse_statement_pdf(content: bytes) -> ParsedStatement:
    """Detect and parse one supported digital statement PDF."""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            document_text = _first_text(pdf)
            normalized = _clean(document_text)
            if "三井住友カード" in normalized and "お支払い明細" in normalized:
                return _parse_smcc(pdf, document_text)
            if "Eco通帳" in normalized and (
                "金融機関コード 0005" in normalized or "directg.s.bk.mufg.jp" in normalized
            ):
                return _parse_mufg(pdf)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("PDFを読み取れませんでした。破損またはパスワード設定をご確認ください") from exc
    raise ValueError("未対応のPDFです。現在は三井住友カードと三菱UFJ銀行に対応しています")
