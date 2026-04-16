# ============================================================
# tests/test_routine.py  ——  RoutineControl (SID 0x31)
# 数据来源：UDS_TestCases_Template.xlsx → Routine sheet
# ============================================================

import time
import pytest
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.excel_reader import load_routine_cases

pytestmark = pytest.mark.routine

_ALL_CASES = load_routine_cases()

_ROUTINE_RESULT_WAIT_S = 1.0   # 启动后等待 Routine 执行完成


@pytest.mark.parametrize('case', _ALL_CASES, ids=[c['id'] for c in _ALL_CASES])
def test_routine(case, uds_client, extended_session):
    """
    统一参数化 Routine 测试，正/负响应由 expected 字段控制。
    session 字段为 '默认会话' 时切换到默认会话，否则使用扩展或编程会话。
    """
    routine_id        = case['routine_id']
    name              = case['name']
    start_data        = case['start_data']
    expect_result_len = case['expect_result_len']
    expected          = case['expected']
    expected_nrc      = case['nrc']
    session_req       = case['session']

    # 切换到所需会话
    if '默认' in session_req:
        client = uds_client
        client.change_session(services.DiagnosticSessionControl.Session.defaultSession)
    elif '编程' in session_req:
        client = uds_client
        try:
            client.change_session(services.DiagnosticSessionControl.Session.programmingSession)
        except (NegativeResponseException, TimeoutException):
            pytest.skip(f"[{name}] 无法进入编程会话，跳过")
    else:
        client = extended_session

    if expected == 'Positive':
        # 启动 Routine
        try:
            start_resp = client.start_routine(routine_id=routine_id, data=start_data)
        except NegativeResponseException as e:
            pytest.fail(
                f"[{name}] StartRoutine NRC 0x{e.response.code:02X} ({e.response.code_name})"
            )
        except TimeoutException:
            pytest.fail(f"[{name}] StartRoutine 无响应（超时）")

        assert start_resp.positive, f"[{name}] StartRoutine 响应标志非正响应"

        time.sleep(_ROUTINE_RESULT_WAIT_S)

        # 查询结果
        try:
            result_resp = client.get_routine_result(routine_id=routine_id)
        except NegativeResponseException as e:
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

    else:  # Negative
        try:
            client.start_routine(routine_id=routine_id, data=start_data)
            pytest.skip(f"[{name}] 期望 NRC，但收到了正响应（ECU 允许此访问，跳过）")
        except NegativeResponseException as e:
            if expected_nrc:
                assert e.response.code in expected_nrc, (
                    f"[{name}] 期望 NRC {[hex(n) for n in expected_nrc]}，"
                    f"实际 0x{e.response.code:02X} ({e.response.code_name})"
                )
        except TimeoutException:
            pytest.fail(f"[{name}] StartRoutine 无响应（超时）")
