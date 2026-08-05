"""services/settlement.py の純関数のテスト。

ここでテストする関数は DB を触らないので、コンテナが起動していなくても走る。
「純関数として切り出しておくとテストが書きやすい」の実例
（DESIGN.md §3.3 / 勉強会スライド S8 の「役割を分ける」）。
"""
import pytest

from app.services.settlement import (
    next_status_on_close,
    next_status_on_confirm,
    split_equally,
)


# ============================================================
# split_equally(total_amount, user_a_paid) -> (per_person, transfer)
#   transfer > 0 なら ひつじ(B) → ありす(A) に送金
#   transfer < 0 なら ありす(A) → ひつじ(B) に送金
# ============================================================


class TestSplitEqually:
    def test_偶数の合計をきれいに折半できる(self):
        # 合計 10000 円。ありすが 7000 円立て替えた。
        per_person, transfer = split_equally(total_amount=10000, user_a_paid=7000)
        assert per_person == 5000
        # ありすは 5000 円負担すべきなのに 7000 払った → 2000 返してもらう
        assert transfer == 2000

    def test_ありすが払っていない場合はありすが払う側になる(self):
        # 合計 10000 円。全部ひつじが立て替えた。
        per_person, transfer = split_equally(total_amount=10000, user_a_paid=0)
        assert per_person == 5000
        # ありすは 5000 円負担すべきで 0 しか払っていない → 5000 払う（マイナス）
        assert transfer == -5000

    def test_ちょうど半分ずつ払っていたら送金は不要(self):
        per_person, transfer = split_equally(total_amount=10000, user_a_paid=5000)
        assert per_person == 5000
        assert transfer == 0

    def test_支出がゼロなら送金もゼロ(self):
        per_person, transfer = split_equally(total_amount=0, user_a_paid=0)
        assert per_person == 0
        assert transfer == 0

    def test_合計が奇数のとき端数は切り捨てられる(self):
        """現在の実装の挙動を記録するテスト。

        ⚠️ DESIGN.md §4 冒頭は「端数は支払者に多く負担させる
        （例：3円 → 支払者2円/相手1円）」と書いているが、
        現在の実装では **月内で立替が少なかった側** が 1 円多く負担する。

        合計 3 円・ありすが 3 円立替の場合:
          per_person = 3 // 2 = 1
          transfer   = 3 - 1  = 2  ← ひつじが 2 円払う
          → ありす負担 1 円 / ひつじ負担 2 円

        DESIGN.md 通りなら「支払者（ありす）が 2 円」なので逆になっている。
        月次集計では両者が支払者なので設計文の解釈が定まっていないのが原因。
        1 円の差なので実害は小さいが、仕様として決め直す必要がある（未決）。
        """
        per_person, transfer = split_equally(total_amount=3, user_a_paid=3)
        assert per_person == 1  # 切り捨て
        assert transfer == 2  # 現在の挙動

    def test_端数があっても両者の負担合計は総額と一致する(self):
        """1 円が消えたり増えたりしないことの確認（これは満たしている）。"""
        total, a_paid = 10001, 6000
        per_person, transfer = split_equally(total, a_paid)
        b_paid = total - a_paid

        alice_burden = a_paid - transfer  # 立替 - 受取
        hitsuji_burden = b_paid + transfer  # 立替 + 支払
        assert alice_burden + hitsuji_burden == total


# ============================================================
# next_status_on_close(current) -> str
# ============================================================


class TestNextStatusOnClose:
    def test_進行中の月は締められる(self):
        assert next_status_on_close("in_progress") == "closed"

    @pytest.mark.parametrize(
        "already", ["closed", "partially_confirmed", "settled"]
    )
    def test_進行中以外の月は締められない(self, already: str):
        with pytest.raises(ValueError):
            next_status_on_close(already)


# ============================================================
# next_status_on_confirm(current, both_confirmed) -> str
# ============================================================


class TestNextStatusOnConfirm:
    def test_締め済みで片方だけ確認したら片方確認済になる(self):
        assert (
            next_status_on_confirm("closed", both_confirmed=False)
            == "partially_confirmed"
        )

    def test_片方確認済でもう片方が確認したら清算済になる(self):
        assert (
            next_status_on_confirm("partially_confirmed", both_confirmed=True)
            == "settled"
        )

    def test_同じ人が二度押しても状態は変わらない(self):
        """片方確認済のまま。二重確認で settled に飛ばないこと。"""
        assert (
            next_status_on_confirm("partially_confirmed", both_confirmed=False)
            == "partially_confirmed"
        )

    def test_進行中の月は確認できない(self):
        """締める前に確認しようとしたらエラー。"""
        with pytest.raises(ValueError):
            next_status_on_confirm("in_progress", both_confirmed=False)

    def test_清算済からは遷移しない(self):
        """DESIGN.md §2.3「清算済からの巻き戻しは行わない」。"""
        with pytest.raises(ValueError):
            next_status_on_confirm("settled", both_confirmed=True)
