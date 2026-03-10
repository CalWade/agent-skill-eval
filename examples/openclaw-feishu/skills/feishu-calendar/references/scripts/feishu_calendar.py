"""
feishu_calendar.py — 飞书日历 Python 封装
支持 OAuth User Token 授权、自动 token 刷新、日程查询与创建
"""
import json
import subprocess
import time
from datetime import datetime


class FeishuCalendar:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.user_token: str | None = None
        self.refresh_token: str | None = None
        self.expires_at: float = 0
        self.calendar_id: str | None = None

    def _curl(self, *args) -> dict:
        r = subprocess.run(["curl", "-s", *args], capture_output=True, text=True)
        return json.loads(r.stdout)

    # ── Token 管理 ────────────────────────────────────────────────────────────

    def get_tenant_token(self) -> str:
        """获取 tenant_access_token（用于 Bot 自己的日历）"""
        d = self._curl(
            "-X", "POST",
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"app_id": self.app_id, "app_secret": self.app_secret}),
        )
        return d["tenant_access_token"]

    def get_app_token(self) -> str:
        """获取 app_access_token（用于 OAuth code 换取 / 刷新流程）"""
        d = self._curl(
            "-X", "POST",
            "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"app_id": self.app_id, "app_secret": self.app_secret}),
        )
        return d["app_access_token"]

    def exchange_code(self, code: str) -> str:
        """用 OAuth code 换取 user_access_token（首次授权）"""
        app_token = self.get_app_token()
        d = self._curl(
            "-X", "POST",
            "https://open.feishu.cn/open-apis/authen/v1/access_token",
            "-H", f"Authorization: Bearer {app_token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"grant_type": "authorization_code", "code": code}),
        )
        data = d["data"]
        self.user_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.expires_at = time.time() + data["expires_in"] - 60
        return self.user_token

    def ensure_token(self) -> str:
        """检查 token 有效性，过期则自动刷新"""
        if self.user_token and time.time() < self.expires_at:
            return self.user_token
        if not self.refresh_token:
            raise RuntimeError("无 refresh_token，请先完成 OAuth 授权（exchange_code）")
        app_token = self.get_app_token()
        d = self._curl(
            "-X", "POST",
            "https://open.feishu.cn/open-apis/authen/v1/refresh_access_token",
            "-H", f"Authorization: Bearer {app_token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"grant_type": "refresh_token", "refresh_token": self.refresh_token}),
        )
        data = d["data"]
        self.user_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.expires_at = time.time() + data["expires_in"] - 60
        return self.user_token

    def get_auth_url(self, redirect_uri: str, state: str = "openclaw") -> str:
        """生成 OAuth 授权链接（发给用户点击）"""
        from urllib.parse import quote
        return (
            "https://open.feishu.cn/open-apis/authen/v1/authorize"
            f"?app_id={self.app_id}"
            f"&redirect_uri={quote(redirect_uri, safe='')}"
            f"&scope=calendar%3Acalendar"
            f"&state={state}"
        )

    # ── 日历操作 ──────────────────────────────────────────────────────────────

    def _get_primary_calendar_id(self, token: str) -> str:
        if self.calendar_id:
            return self.calendar_id
        d = self._curl(
            "https://open.feishu.cn/open-apis/calendar/v4/calendars",
            "-H", f"Authorization: Bearer {token}",
        )
        cals = d["data"]["calendar_list"]
        # 优先取 type=primary 的日历
        for c in cals:
            if c.get("type") == "primary":
                self.calendar_id = c["calendar_id"]
                return self.calendar_id
        self.calendar_id = cals[0]["calendar_id"]
        return self.calendar_id

    def get_upcoming_events(self, days: int = 7) -> list[dict]:
        """获取未来 N 天的日程（需 OAuth）"""
        token = self.ensure_token()
        cal_id = self._get_primary_calendar_id(token)
        start = int(time.time())
        end = start + days * 86400
        d = self._curl(
            f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{cal_id}/events"
            f"?page_size=50&start_time={start}&end_time={end}",
            "-H", f"Authorization: Bearer {token}",
        )
        return d["data"]["items"]

    def print_upcoming_events(self, days: int = 7):
        """打印未来 N 天日程"""
        items = self.get_upcoming_events(days)
        for e in sorted(items, key=lambda x: x.get("start_time", {}).get("timestamp", "0")):
            ts = e.get("start_time", {}).get("timestamp")
            dt = e.get("start_time", {}).get("date_time")
            if ts:
                t = datetime.fromtimestamp(int(ts) / 1000)
                tstr = t.strftime("%m/%d %H:%M")
            elif dt:
                t = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                tstr = t.strftime("%m/%d %H:%M")
            else:
                tstr = "全天"
            print(f"{tstr}  {e.get('summary', '（无标题）')}")

    def create_event(
        self,
        summary: str,
        start_dt: str,
        end_dt: str,
        description: str = "",
        timezone: str = "Asia/Shanghai",
        use_user_token: bool = False,
    ) -> str:
        """
        创建日程，返回 event_id。
        start_dt / end_dt: RFC3339 格式，如 "2026-03-09T10:00:00+08:00"
        use_user_token=True 时操作主人日历，否则操作 Bot 日历
        """
        token = self.ensure_token() if use_user_token else self.get_tenant_token()
        cal_id = self._get_primary_calendar_id(token)
        body = {
            "summary": summary,
            "description": description,
            "start_time": {"date_time": start_dt, "timezone": timezone},
            "end_time": {"date_time": end_dt, "timezone": timezone},
            "visibility": "default",
            "attendee_ability": "can_invite_others",
        }
        d = self._curl(
            "-X", "POST",
            f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{cal_id}/events",
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(body),
        )
        return d["data"]["event"]["event_id"]

    def invite_attendees(self, event_id: str, user_ids: list[str]):
        """邀请参会人（open_id 列表）"""
        token = self.ensure_token()
        cal_id = self._get_primary_calendar_id(token)
        body = {
            "attendees": [{"type": "user", "user_id": uid} for uid in user_ids],
            "user_id_type": "open_id",
        }
        self._curl(
            "-X", "POST",
            f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{cal_id}/events/{event_id}/attendees",
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(body),
        )

    def check_freebusy(
        self, user_ids: list[str], time_min: str, time_max: str
    ) -> dict:
        """查询一组用户的忙闲状态"""
        token = self.ensure_token()
        body = {
            "time_min": time_min,
            "time_max": time_max,
            "user_id_list": user_ids,
            "user_id_type": "open_id",
        }
        return self._curl(
            "-X", "POST",
            "https://open.feishu.cn/open-apis/calendar/v4/freebusy/batch_get",
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(body),
        )


# ── 使用示例 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cal = FeishuCalendar("YOUR_APP_ID", "YOUR_APP_SECRET")

    # 首次使用：OAuth 授权
    # print(cal.get_auth_url("https://your-domain.com/auth/callback"))
    # code = input("输入授权 code: ")
    # cal.exchange_code(code)

    # 查看未来7天日程
    # cal.print_upcoming_events(7)

    # 创建日程
    # event_id = cal.create_event(
    #     summary="AI项目周会",
    #     start_dt="2026-03-09T10:00:00+08:00",
    #     end_dt="2026-03-09T11:00:00+08:00",
    #     description="本周进展同步",
    #     use_user_token=True,
    # )
    # print(f"日程已创建: {event_id}")
