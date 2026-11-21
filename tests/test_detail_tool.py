"""get_activity_detail MCP 工具的单元测试（Phase 6.2-D）。

全部使用 httpx.MockTransport 模拟 HTC API：一次 handler 按请求 payload
特征区分列表查询（含 limit/order）与详情查询（含 detailDataType），
不访问真实网络、不需要 Cookie。

detail 响应体复用 synthetic fixture（tests/fixtures/sample_activity_detail.json，
顶层 list、3 个 collector：心率 / location / 空 power），不含真实用户数据。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from src.huawei_health_mcp.client import HTCClient, HTCHTTPError
from src.huawei_health_mcp.server import get_activity_detail

FIXTURE = Path(__file__).parent / "fixtures" / "sample_activity_detail.json"

# 与 synthetic fixture 中 detail 对象一致的记录级值（毫秒 / int）
TARGET_ID = "synthetic-detail-0001"
RECORD_START_MS = 1786706473000
RECORD_END_MS = 1786709186000

RECORDS_BODY = [
    # 一条干扰记录在前，验证按 id 正确定位而非取第一条
    {"id": "other-activity-1", "activityType": 90,
     "startTime": 1786620000000, "endTime": 1786623600000},
    {"id": TARGET_ID, "activityType": 56,
     "startTime": RECORD_START_MS, "endTime": RECORD_END_MS},
]


def _make_mock_client(handler) -> HTCClient:
    """用 MockTransport 构造一个不联网的 HTCClient。"""
    transport = httpx.MockTransport(handler)
    return HTCClient(headers={}, client=httpx.Client(transport=transport))


def _two_phase_handler(captured: dict[str, Any], detail_body: Any) -> Any:
    """构造同时服务列表查询与详情查询的 handler。

    列表请求 payload 含 limit/order；详情请求 payload 含 activityType +
    detailDataType。详情响应默认用 synthetic fixture。
    """

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        if "detailDataType" in payload:
            captured["detail"] = payload
            return httpx.Response(200, json=detail_body)
        captured["list"] = payload
        return httpx.Response(200, json=RECORDS_BODY)

    return handler


# ---------------- 1/2/3/4/5/10/11：正常路径全链路 ----------------

def test_success_full_chain_returns_parsed_detail():
    """正常链路：列表定位 → 详情请求 → parser → 序列化 dict。

    覆盖：正确传入并解析 activity id、client/parser 被正确调用、
    多 collector 与 samplePoints/value[] 保留、模型序列化风格。
    """
    captured: dict[str, Any] = {}
    detail_body = json.loads(FIXTURE.read_text(encoding="utf-8"))
    mock_client = _make_mock_client(_two_phase_handler(captured, detail_body))

    with patch(
        "src.huawei_health_mcp.server.create_htc_client", return_value=mock_client
    ):
        result = get_activity_detail(activity_id=TARGET_ID)

    # client 被调用两次（列表 + 详情），且列表请求带定位用 limit
    assert "list" in captured and "detail" in captured
    assert captured["list"]["limit"] == 50

    # 顶层字段来自 detail 对象（synthetic fixture）
    assert isinstance(result, dict)
    assert result["activity_id"] == TARGET_ID
    assert result["activity_type"] == 56
    assert result["active_time"] == 2713
    assert result["time_zone"] == "Asia/Shanghai"
    # 顶层毫秒契约（6.2-C 真实数据修正）
    assert result["start_time"].startswith("2026-08-14T11:21:13")

    # details[]：3 个 collector（心率 / location / 空 power）
    assert len(result["details"]) == 3

    hr = result["details"][0]
    assert "exercise_heart_rate" in hr["data_collector_id"]
    assert hr["sample_points"][0]["data_type_name"] == (
        "com.huawei.instantaneous.exercise_heart_rate"
    )
    assert hr["sample_points"][0]["values"] == {"bpm": 100.0}

    loc = result["details"][1]
    loc_values = loc["sample_points"][0]["values"]
    assert set(loc_values) == {
        "latitude", "longitude", "precision", "altitude", "coordinate"
    }
    assert isinstance(loc_values["coordinate"], int)  # integerValue 保真

    assert result["details"][2]["sample_points"] == []


def test_detail_payload_uses_record_values_verbatim():
    """详情 payload 逐字使用定位到的记录的毫秒时间戳与类型，不换算。"""
    captured: dict[str, Any] = {}
    detail_body = json.loads(FIXTURE.read_text(encoding="utf-8"))
    mock_client = _make_mock_client(_two_phase_handler(captured, detail_body))

    with patch(
        "src.huawei_health_mcp.server.create_htc_client", return_value=mock_client
    ):
        get_activity_detail(activity_id=TARGET_ID)

    detail_payload = captured["detail"]
    assert detail_payload["startTime"] == str(RECORD_START_MS)
    assert detail_payload["endTime"] == str(RECORD_END_MS)
    assert detail_payload["activityType"] == "56"
    assert detail_payload["highFreqDetailsPreferred"] is True
    # 默认请求 8 个核心数据类型（Phase 6.1 确认集合）
    assert len(detail_payload["detailDataType"]) == 8
    assert detail_payload["detailDataType"][0] == (
        "com.huawei.instantaneous.exercise_heart_rate"
    )


# ---------------- 6：空 detail 响应 ----------------

def test_empty_detail_response_legal():
    """详情响应为空列表时合法返回（details=[]），不抛错。"""
    captured: dict[str, Any] = {}
    mock_client = _make_mock_client(_two_phase_handler(captured, []))

    with patch(
        "src.huawei_health_mcp.server.create_htc_client", return_value=mock_client
    ):
        result = get_activity_detail(activity_id=TARGET_ID)

    assert isinstance(result, dict)
    assert result["details"] == []


# ---------------- 7：API HTTP 错误 ----------------

def test_http_error_propagates():
    """HTC HTTP 错误（500）向上清晰传播，不变成不可读 traceback。"""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        if "detailDataType" in payload:
            return httpx.Response(500, text="server error")
        return httpx.Response(200, json=RECORDS_BODY)

    mock_client = _make_mock_client(handler)
    with patch(
        "src.huawei_health_mcp.server.create_htc_client", return_value=mock_client
    ):
        with pytest.raises(HTCHTTPError) as exc_info:
            get_activity_detail(activity_id=TARGET_ID)

    assert "500" in str(exc_info.value)


# ---------------- 8：认证失效 ----------------

def test_auth_failure_propagates():
    """认证失效（401）在列表查询阶段即清晰报错。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    mock_client = _make_mock_client(handler)
    with patch(
        "src.huawei_health_mcp.server.create_htc_client", return_value=mock_client
    ):
        with pytest.raises(HTCHTTPError) as exc_info:
            get_activity_detail(activity_id=TARGET_ID)

    assert "401" in str(exc_info.value)


# ---------------- malformed detail 响应 ----------------

def test_malformed_detail_response_no_traceback():
    """详情响应结构异常（非对象元素）时不崩溃：parser 容错返回空 detail。"""
    captured: dict[str, Any] = {}
    mock_client = _make_mock_client(_two_phase_handler(captured, [42]))

    with patch(
        "src.huawei_health_mcp.server.create_htc_client", return_value=mock_client
    ):
        result = get_activity_detail(activity_id=TARGET_ID)

    assert result["details"] == []
    assert result["activity_id"] is None  # parser 对畸形输入的既定行为


# ---------------- activity 不存在 ----------------

def test_activity_not_found_raises_value_error():
    """列表里找不到该 activity_id 时给出可操作的 ValueError。"""
    captured: dict[str, Any] = {}
    detail_body = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        if "detailDataType" in payload:
            captured["detail"] = payload
            return httpx.Response(200, json=detail_body)
        captured["list"] = payload
        # 列表里只有别的活动
        return httpx.Response(200, json=[RECORDS_BODY[0]])

    mock_client = _make_mock_client(handler)
    with patch(
        "src.huawei_health_mcp.server.create_htc_client", return_value=mock_client
    ):
        with pytest.raises(ValueError) as exc_info:
            get_activity_detail(activity_id=TARGET_ID)

    # 错误信息含 id 与可操作提示；且没有发起详情请求
    assert TARGET_ID in str(exc_info.value)
    assert "detail" not in captured

# ---------------- lookback_days：定位窗口（Phase 6.4） ----------------

# 一条 60 天前的旧活动（synthetic）与一条近期活动
NOW_MS = 1786886400000            # 2026-08-14 前后的合成“现在”
OLD_ID = "synthetic-old-activity-60d"
OLD_START_MS = NOW_MS - 60 * 86400 * 1000
OLD_END_MS = OLD_START_MS + 45 * 60 * 1000
_FIXED_NOW = datetime.fromtimestamp(NOW_MS / 1000, tz=timezone.utc)


class _FixedDatetime(datetime):
    """Keep the synthetic activity window deterministic across calendar dates."""

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            # 忠实于 datetime.now() 的语义：返回本地时区的 naive datetime。
            # 旧实现返回 _FIXED_NOW 的 UTC-naive，在本地时区路径（如 _local_midnight）
            # 下会让窗口计算偏移；改成先按本地时区换算再去 tzinfo，语义才一致。
            return _FIXED_NOW.astimezone().replace(tzinfo=None)
        return _FIXED_NOW.astimezone(tz)

WINDOW_RECORDS = [
    {"id": OLD_ID, "activityType": 56,
     "startTime": OLD_START_MS, "endTime": OLD_END_MS},
    {"id": TARGET_ID, "activityType": 56,
     "startTime": RECORD_START_MS, "endTime": RECORD_END_MS},
]


def _window_aware_handler(captured: dict, detail_body) -> Any:
    """模拟真实 API 的时间过滤：只返回 startTime 落在请求窗口内的记录。"""

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        if "detailDataType" in payload:
            captured["detail"] = payload
            return httpx.Response(200, json=detail_body)
        captured["list"] = payload
        window_start = int(payload["startTime"])
        visible = [
            r for r in WINDOW_RECORDS if r["startTime"] >= window_start
        ]
        return httpx.Response(200, json=visible)

    return handler


def test_detail_lookup_wider_window_finds_old_activity():
    """60 天前的活动：默认 30 天找不到，扩到 90 天能找到且 payload 逐字正确。"""
    detail_body = json.loads(FIXTURE.read_text(encoding="utf-8"))

    # 默认 30 天：旧活动不可见 → ValueError
    captured: dict = {}
    mock_client = _make_mock_client(_window_aware_handler(captured, detail_body))
    with patch(
        "src.huawei_health_mcp.server.create_htc_client", return_value=mock_client
    ), patch("src.huawei_health_mcp.server.datetime", _FixedDatetime):
        with pytest.raises(ValueError):
            get_activity_detail(activity_id=OLD_ID)

    # 扩大到 90 天：能定位，detail payload 逐字使用旧活动自身毫秒时间戳
    captured.clear()
    mock_client = _make_mock_client(_window_aware_handler(captured, detail_body))
    with patch(
        "src.huawei_health_mcp.server.create_htc_client", return_value=mock_client
    ), patch("src.huawei_health_mcp.server.datetime", _FixedDatetime):
        result = get_activity_detail(activity_id=OLD_ID, lookback_days=90)

    assert captured["detail"]["startTime"] == str(OLD_START_MS)
    assert captured["detail"]["endTime"] == str(OLD_END_MS)
    assert captured["detail"]["activityType"] == "56"
    assert result["activity_id"] == "synthetic-detail-0001"  # 解析自 detail 响应


def test_detail_lookup_rejects_invalid_window():
    """detail 工具同样校验窗口：非法值抛 ValueError，不发请求。"""
    with pytest.raises(ValueError):
        get_activity_detail(activity_id=OLD_ID, lookback_days=0)
    with pytest.raises(ValueError):
        get_activity_detail(activity_id=OLD_ID, lookback_days=9999)


def test_fixed_now_anchor_and_window_independent_of_real_clock():
    """issue #2 回归：定位窗口必须锚定 _FIXED_NOW，与真实墙钟/日历日期无关。

    锁定两层契约：
      1. _FixedDatetime.now(timezone.utc) 恒等于锚点 _FIXED_NOW；
         _FixedDatetime.now()（tz=None）忠实于 datetime.now()：本地时区 naive。
      2. 端到端：即便把真实墙钟拨到锚点之后 400 天，server 发出的列表请求窗口
         起点仍等于锚点 - 30 天——不会随真实日历漂移而把旧活动过滤掉。
    """
    # 1) 锚点恒等与 tz=None 语义忠实性
    assert _FixedDatetime.now(timezone.utc) == _FIXED_NOW
    local_naive = _FixedDatetime.now()
    assert local_naive.tzinfo is None
    assert local_naive == _FIXED_NOW.astimezone().replace(tzinfo=None)

    # 2) 端到端：真实墙钟漂移不应影响 server 的窗口计算
    detail_body = json.loads(FIXTURE.read_text(encoding="utf-8"))
    captured: dict = {}
    mock_client = _make_mock_client(_window_aware_handler(captured, detail_body))
    drifted_real_now_ms = NOW_MS + 400 * 86400 * 1000
    with patch("time.time", return_value=drifted_real_now_ms / 1000), patch(
        "src.huawei_health_mcp.server.create_htc_client", return_value=mock_client
    ), patch("src.huawei_health_mcp.server.datetime", _FixedDatetime):
        with pytest.raises(ValueError):
            # 默认 30 天窗口应排除 60 天前的旧活动（锚点语义），而非因墙钟漂移改变
            get_activity_detail(activity_id=OLD_ID)

    anchored_window_start_ms = NOW_MS - 30 * 86400 * 1000
    assert captured["list"]["startTime"] == str(anchored_window_start_ms)
