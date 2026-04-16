# ============================================================
# tests/test_security_access.py  ——  SecurityAccess (SID 0x27)
# 数据来源：UDS_TestCases_Template.xlsx → SecurityAccess sheet
# ============================================================

import time
import pytest
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.excel_reader import load_security_access_cases

pytestmark = pytest.mark.security

_ALL_CASES = load_security_access_cases()
_POSITIVE  = [c for c in _ALL_CASES if c['expected'] == 'Positive']
_NEGATIVE  = [c for c in _ALL_CASES if c['expected'] == 'Negative']

# 错误密钥后的等待时间（ISO 14229 要求）
_WRONG_KEY_DELAY_S = 10.0


# ---- 正响应：完整 Seed-Key 解锁流程 ----

@pytest.mark.parametrize('case', _POSITIVE, ids=[c['id'] for c in _POSITIVE])
def test_security_access_positive(case, uds_client, extended_session):
    """
    执行完整 Seed-Key 解锁流程，验证正响应。
    pre_session 为 '编程会话' 时需手动切换（此处 extended_session 已是扩展会话，
    编程会话需在测试体内切换）。
    """
    name        = case['name']
    seed_level  = case['seed_level']
    pre_session = case['pre_session']

    if '编程' in pre_session:
        client = uds_client
        try:
            client.change_session(services.DiagnosticSessionControl.Session.programmingSession)
        except (NegativeResponseException, TimeoutException):
            pytest.skip(f"[{name}] 无法进入编程会话，跳过")
    else:
        client = extended_session

    try:
        response = client.unlock_security_access(seed_level)
    except NegativeResponseException as e:
        pytest.fail(
            f"[{name}] 解锁失败，NRC 0x{e.response.code:02X} ({e.response.code_name})。"
            f"请确认 seed_key.py 算法与 ECU 一致。"
        )
    except TimeoutException:
        pytest.fail(f"[{name}] SecurityAccess 无响应（超时）")

    assert response.positive, f"[{name}] SecurityAccess 响应标志非正响应"

    # 恢复扩展会话
    try:
        client.change_session(services.DiagnosticSessionControl.Session.extendedDiagnosticSession)
    except Exception:
        pass


# ---- 负响应：错误密钥 / 错误会话 / 超限 ----

@pytest.mark.negative
@pytest.mark.parametrize('case', _NEGATIVE, ids=[c['id'] for c in _NEGATIVE])
def test_security_access_negative(case, uds_client, extended_session):
    """
    负响应测试：
    - NRC 0x35 (invalidKey)：请求种子后发送错误密钥
    - NRC 0x22 (conditionsNotCorrect)：默认会话直接请求种子
    - NRC 0x36 (exceededNumberOfAttempts)：连续发送错误密钥
    """
    name         = case['name']
    seed_level   = case['seed_level']
    key_level    = case['key_level']
    expected_nrc = case['nrc']
    pre_session  = case['pre_session']

    # 切换到所需前置会话
    if '默认' in pre_session:
        client = uds_client
        client.change_session(services.DiagnosticSessionControl.Session.defaultSession)
    else:
        client = extended_session

    # NRC 0x22：直接请求种子即可触发
    if 0x22 in expected_nrc and '默认' in pre_session:
        try:
            client.request_seed(seed_level)
            pytest.fail(f"[{name}] 期望 NRC，但收到了正响应")
        except NegativeResponseException as e:
            assert e.response.code in expected_nrc, (
                f"[{name}] 期望 NRC {[hex(n) for n in expected_nrc]}，"
                f"实际 0x{e.response.code:02X} ({e.response.code_name})"
            )
        except TimeoutException:
            pytest.fail(f"[{name}] ECU 无响应（超时）")
        return

    # NRC 0x35 / 0x36：需要先获取种子，再发送错误密钥
    if key_level is None:
        pytest.skip(f"[{name}] key_level 未配置，跳过")

    try:
        seed_resp = client.request_seed(seed_level)
    except (NegativeResponseException, TimeoutException) as e:
        pytest.fail(f"[{name}] 请求种子失败: {e}")

    seed      = seed_resp.service_data.security_seed
    wrong_key = seed   # 直接用种子作为错误密钥

    try:
        client.send_key(key_level, wrong_key)
        pytest.fail(f"[{name}] 期望 NRC，但收到了正响应")
    except NegativeResponseException as e:
        assert e.response.code in expected_nrc, (
            f"[{name}] 期望 NRC {[hex(n) for n in expected_nrc]}，"
            f"实际 0x{e.response.code:02X} ({e.response.code_name})"
        )
    except TimeoutException:
        pytest.fail(f"[{name}] ECU 无响应（超时）")

    # 错误密钥后等待 ECU 重试延迟
    time.sleep(_WRONG_KEY_DELAY_S)
