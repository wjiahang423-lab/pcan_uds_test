# ============================================================
# tests/test_session.py  ——  DiagnosticSessionControl (SID 0x10)
# 数据来源：UDS_TestCases_Template.xlsx → DiagSession sheet
# ============================================================

import pytest
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.excel_reader import load_diag_session_cases

pytestmark = pytest.mark.session_ctrl

_ALL_CASES  = load_diag_session_cases()
_POSITIVE   = [c for c in _ALL_CASES if c['expected'] == 'Positive']
_NEGATIVE   = [c for c in _ALL_CASES if c['expected'] == 'Negative']


# ---- 正响应用例 ----

@pytest.mark.parametrize('case', _POSITIVE, ids=[c['id'] for c in _POSITIVE])
def test_change_session_positive(case, uds_client):
    """切换到合法会话应收到正响应，响应 session_type 字段与请求一致。"""
    session_val = case['session_type']
    name        = case['name']

    try:
        response = uds_client.change_session(session_val)
    except NegativeResponseException as e:
        pytest.fail(f"[{name}] 期望正响应，收到 NRC 0x{e.response.code:02X} ({e.response.code_name})")
    except TimeoutException:
        pytest.fail(f"[{name}] ECU 无响应（超时）")

    assert response.positive, f"[{name}] 响应标志为非正响应"
    assert response.service_data.session_type == session_val, (
        f"[{name}] 响应会话类型 0x{response.service_data.session_type:02X} "
        f"!= 请求值 0x{session_val:02X}"
    )

    # 恢复默认会话，保持测试隔离
    uds_client.change_session(services.DiagnosticSessionControl.Session.defaultSession)


# ---- 负响应用例 ----

@pytest.mark.negative
@pytest.mark.parametrize('case', _NEGATIVE, ids=[c['id'] for c in _NEGATIVE])
def test_change_session_negative(case, uds_client):
    """请求不支持的会话类型应收到对应 NRC。"""
    session_val = case['session_type']
    name        = case['name']
    expected_nrc = case['nrc']   # list[int]

    try:
        uds_client.change_session(session_val)
        pytest.fail(f"[{name}] 期望 NRC，但收到了正响应")
    except NegativeResponseException as e:
        if expected_nrc:
            assert e.response.code in expected_nrc, (
                f"[{name}] 期望 NRC {[hex(n) for n in expected_nrc]}，"
                f"实际 0x{e.response.code:02X} ({e.response.code_name})"
            )
    except TimeoutException:
        pytest.fail(f"[{name}] ECU 无响应（超时）")
