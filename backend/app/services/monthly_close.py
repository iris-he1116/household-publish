"""月末自動締めジョブの判定と実行。

launchd から毎日 23:59 に呼ばれる。月末当日は当月を、Mac のスリープなどで
実行が翌日以降になった場合は前月を対象にする。同じ月を繰り返し実行しても、
``in_progress`` のときだけ締めるため二重にイベントを記録しない。
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.queries import settlement as q
from app.services.settlement import close_month


def year_month_due_for_close(now: datetime | None = None) -> str:
    """指定時刻で自動締めの対象になる年月を ``YYYY-MM`` で返す。

    - 月末日の 23:59 以降: 当月
    - それ以外: 前月

    ``now`` を省略した場合はホストのローカル時刻を使う。launchd の実行時刻と
    同じタイムゾーンになるため、別の設定を二重管理しない。
    """
    local_now = now if now is not None else datetime.now().astimezone()
    today = local_now.date()
    tomorrow = today + timedelta(days=1)
    is_month_end = tomorrow.month != today.month
    reached_close_time = (local_now.hour, local_now.minute) >= (23, 59)

    if is_month_end and reached_close_time:
        target = today
    else:
        target = today.replace(day=1) - timedelta(days=1)

    return target.strftime("%Y-%m")


def close_due_month(
    session: Session, now: datetime | None = None
) -> tuple[str, bool]:
    """締め対象月を必要なら締め、``(対象年月, 締めたか)`` を返す。"""
    year_month = year_month_due_for_close(now)
    settlement = q.get_or_create_settlement(session, year_month)

    if settlement.status != "in_progress":
        return year_month, False

    close_month(session, user=None, year_month=year_month)
    return year_month, True
