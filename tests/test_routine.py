# ============================================================
# tests/test_routine.py  ——  RoutineControl (SID 0x31)
#
# 测试项：
#   1. 启动支持的 Routine（参数化）→ 正响应
#   2. 获取 Routine 结果（若支持）
#   3. 无效 Routine ID → NRC 0x31 (requestOutOfRange)
#   4. 在默认会话中启动仅限扩展会话的 Routine → NRC 0x22
# ============================================================

import time
import pytest
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import ROUTINE_TEST_CASES

pytestmark = pytest.mark.routine

ROUTINE_STOP_WAIT_S = 1.0


# ---- 正响应：启动并查询 Routine ----

@pytest.mark.parametrize(
    'case',
    ROUTINE_TEST_CASES,
    ids=[c['name'] for c in ROUTINE_TEST_CASES],
)
def test_routine_start_and_result(case, extended_session):
    """
    启动 RoutineControl，等待完成，查询结果。
    期望正响应，若配置了 expect_result_len 则验证结果长度。
    """
    uds_client = extended_session
    routine_id         = case['routine_id']
    start_data         = case.get('start_data', b'')
    expect_result_len  = case.get('expect_result_len', 0)
    name               = case['name']

    # 启动
    try:
        start_resp = uds_client.start_routine(routine_id=routine_id, data=start_data)
    except NegativeResponseException as e:
        pytest.fail(
            f"[{name}] StartRoutine NRC 0x{e.response.code:02X} ({e.response.code_name})"
        )
    except TimeoutException:
        pytest.fail(f"[{name}] StartRoutine 无响应（超时）")

    assert start_resp.positive, f"[{name}] StartRoutine 响应标志非正响应"

    # 等待执行
    time.sleep(ROUTINE_STOP_WAIT_S)

    # 查询结果
    try:
        result_resp = uds_client.get_routine_result(routine_id=routine_id)
    except NegativeResponseException as e:
        # 部分 ECU 不支持 RequestRoutineResults，跳过而不失败
        if e.response.code == 0x31:
            pytest.skip(f"[{name}] 该 Routine 不支持 RequestRoutineResults")
        pytest.fail(f"[{name}] GetRoutineResult NRC 0x{e.response.code:02X}")
    except TimeoutException:
        pytest.fail(f"[{name}] GetRoutineResult 无响应（超时）")

    assert result_resp.positive, f"[{name}] GetRoutineResult 响应标志非正响应"

    if expect_result_len > 0:
        raw = result_resp.service_data.routine_status_record
        assert len(raw) >= expect_result_len, (
            f"[{name}] 结果数据长度 {len(raw)} < 期望 {expect_result_len}"
        )


# ---- 负响应：无效 Routine ID ----

@pytest.mark.negative
def test_routine_invalid_id(extended_session):
    """启动无效 Routine ID (0x0000) 应收到 NRC 0x31 (requestOutOfRange)。"""
    try:
        extended_session.start_routine(routine_id=0x0000)
        pytest.fail("期望 NRC，但收到了正响应")
    except NegativeResponseException as e:
        assert e.response.code in (0x31, 0x22), (
            f"期望 NRC 0x31 或 0x22，实际 0x{e.response.code:02X}"
        )
    except TimeoutException:
        pytest.fail("ECU 无响应（超时）")


# ---- 负响应：错误会话 ----

@pytest.mark.negative
def test_routine_wrong_session(uds_client):
    """默认会话下启动仅限扩展会话的 Routine，应收到 NRC 0x22。"""
    if not ROUTINE_TEST_CASES:
        pytest.skip("无已配置的 Routine 用例")

    case = ROUTINE_TEST_CASES[0]
    uds_client.change_session(services.DiagnosticSessionControl.Session.defaultSession)

    try:
        uds_client.start_routine(routine_id=case['routine_id'])
        pytest.skip("该 Routine 在默认会话也可执行，跳过负响应验证")
    except NegativeResponseException as e:
        assert e.response.code in (0x22, 0x31), (
            f"期望 NRC 0x22 或 0x31，实际 0x{e.response.code:02X}"
        )
    except TimeoutException:
        pytest.fail("ECU 无响应（超时）")
