"""services/paypay_import.py の純関数のテスト。

`ensure_judgeable()` は DB もセッションも ORM オブジェクトも触らないので、
**コンテナを起動しなくても** このテストは走る。

勉強会 第5回「分離」の 3問診断:
  1. 同じルールが2箇所以上に書かれているか      → Yes だった（adopt / exclude に重複）
  2. DB を立ち上げないとルールを確認できないか  → Yes だった（統合テストでしか検証できなかった）
  3. 入口（Web / CLI / AI）が増える予定があるか  → No
処方「ルールを純関数へ1つ切り出す」を実施した結果、1 と 2 が解消された。
"""
import pytest

from app.services.paypay_import import ensure_judgeable


ALICE = 1
HITSUJI = 2


class TestEnsureJudgeable:
    def test_未判定かつ本人なら通る(self):
        # 例外が出なければ OK
        ensure_judgeable(
            status="pending",
            imported_by=ALICE,
            actor_user_id=ALICE,
            action="adopt",
        )

    @pytest.mark.parametrize("action", ["adopt", "exclude"])
    def test_操作名がエラーメッセージに入る(self, action: str):
        """adopt / exclude のどちらから呼ばれたかがメッセージで分かる。"""
        with pytest.raises(ValueError, match=f"は {action} できません"):
            ensure_judgeable(
                status="adopted",
                imported_by=ALICE,
                actor_user_id=ALICE,
                action=action,
            )

    @pytest.mark.parametrize("already", ["adopted", "excluded"])
    def test_判定済みの行は再判定できない(self, already: str):
        """二重計上・二重除外の防止。"""
        with pytest.raises(ValueError, match="できません"):
            ensure_judgeable(
                status=already,
                imported_by=ALICE,
                actor_user_id=ALICE,
                action="adopt",
            )

    def test_他人が取り込んだ行は判定できない(self):
        """DESIGN.md §1.4「PayPay 履歴は各自が自分の分をアップロードする」。

        ありすが取り込んだ行を、ひつじが判定しようとするケース。
        """
        with pytest.raises(ValueError, match="他人のステージング行"):
            ensure_judgeable(
                status="pending",
                imported_by=ALICE,
                actor_user_id=HITSUJI,
                action="adopt",
            )

    def test_状態チェックが所有者チェックより先に効く(self):
        """両方に違反している場合、status のエラーが先に出る。

        メッセージが安定するので、呼び出し側やテストが壊れにくい。
        """
        with pytest.raises(ValueError, match="は adopt できません"):
            ensure_judgeable(
                status="adopted",
                imported_by=ALICE,
                actor_user_id=HITSUJI,  # 所有者も違う
                action="adopt",
            )
