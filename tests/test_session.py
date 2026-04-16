# ============================================================
# tests/test_session.py  ——  DiagnosticSessionControl (SID 0x10)
#
# 测试项：
#   1. 进入 Default Session        → 正响应 0x50 0x01
#   2. 进入 Extended Session       → 正响应 0x50 0x03
#   3. 进入 Programming Session    → 正响应 0x50 0x02
#   4. 无效会话子功能              → NRC 0x12 (subFunctionNotSupported)
# ============================================================

import pytest
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

pytestmark = pytest.mark.session_ctrl


# ---- 正响应用例 ----

_VALID_SESSIONS = [
    (services.DiagnosticSessionControl.Session.defaultSession,          'DefaultSession'),
    (services.DiagnosticSessionControl.Session.extendedDiagnosticSession, 'ExtendedSession'),
    (services.DiagnosticSessionControl.Session.programmingSession,       'ProgrammingSession'),
]

@pytest.mark.parametrize('session,name', _VALID_SESSIONS, ids=[s[1] for s in _VALID_SESSIONS])
def test_change_session_positive(session, name, uds_client):
    """切换到合法会话应收到正响应，会话类型字段与请求一致。"""
    try:
        response = uds_client.change_session(session)
    except NegativeResponseException as e:
        pytest.fail(f"[{name}] 期望正响应，收到 NRC 0x{e.response.code:02X} ({e.response.code_name})")
    except TimeoutException:
        pytest.fail(f"[{name}] ECU 无响应（超时）")

    assert response.positive, f"[{name}] 响应标志为非正响应"
    assert response.service_data.session_type == session.value, (
        f"[{name}] 响应会话类型 0x{response.service_data.session_type:02X} "
        f"!= 请求值 0x{session.value:02X}"
    )

    # 恢复默认会话，保持测试隔离
    uds_client.change_session(services.DiagnosticSessionControl.Session.defaultSession)


# ---- 负响应用例 ----

@pytest.mark.negative
def test_change_session_invalid_subfunction(uds_client):
    """
    请求不支持的会话类型（0x05）应收到 NRC 0x12 (subFunctionNotSupported)。
    注意：部分 ECU 实现可能返回 0x31 (requestOutOfRange)，按实际修改断言。
    """
    INVALID_SESSION = 0x05
    try:
        uds_client.change_session(INVALID_SESSION)
        pytest.fail("期望 NRC，但收到了正响应")
    except NegativeResponseException as e:
        assert e.response.code in (0x12, 0x31), (
            f"期望 NRC 0x12 或 0x31，实际收到 0x{e.response.code:02X} ({e.response.code_name})"
        )
    except TimeoutException:
        pytest.fail("ECU 无响应（超时）")
