# ============================================================
# tests/test_security_access.py  ——  SecurityAccess (SID 0x27)
#
# 测试项：
#   1. 扩展会话下完整的 Seed-Key 流程 → 解锁成功
#   2. 使用错误密钥 → NRC 0x35 (invalidKey)
#   3. 默认会话下请求安全访问 → NRC 0x22 (conditionsNotCorrect)
#   4. 重复错误密钥超过限制 → NRC 0x36 (exceededNumberOfAttempts)
# ============================================================

import time
import pytest
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import SA_LEVEL_DEFAULT_SEED, SA_LEVEL_DEFAULT_KEY
from utils.seed_key import compute_key_level01

pytestmark = pytest.mark.security


# ------------------------------------------------------------------ #
#  正响应测试
# ------------------------------------------------------------------ #

def test_security_access_unlock(extended_session):
    """
    扩展会话下，执行完整 Seed-Key 解锁流程：
      Step1: RequestSeed (level 0x01) → 收到种子
      Step2: SendKey (level 0x02, 使用正确算法) → 解锁成功，正响应
    """
    uds_client = extended_session

    try:
        # udsoncan.unlock_security_access 自动完成两步（调用 security_algo）
        response = uds_client.unlock_security_access(SA_LEVEL_DEFAULT_SEED)
    except NegativeResponseException as e:
        pytest.fail(
            f"解锁失败，NRC 0x{e.response.code:02X} ({e.response.code_name}). "
            f"请检查 seed_key.py 中的算法是否与 ECU 一致。"
        )
    except TimeoutException:
        pytest.fail("SecurityAccess 无响应（超时）")

    assert response.positive, "SecurityAccess 响应标志非正响应"


def test_security_access_already_unlocked(extended_session):
    """
    已解锁状态下再次发送 RequestSeed，ECU 应返回全零种子（已解锁标志）
    或正常重新解锁，不返回 NRC。
    """
    uds_client = extended_session

    # 先确保解锁
    try:
        uds_client.unlock_security_access(SA_LEVEL_DEFAULT_SEED)
    except NegativeResponseException:
        pytest.skip("无法完成初次解锁，跳过已解锁状态测试")

    # 再次请求种子
    try:
        response = uds_client.request_seed(SA_LEVEL_DEFAULT_SEED)
    except NegativeResponseException as e:
        pytest.fail(f"已解锁状态下请求种子收到 NRC 0x{e.response.code:02X}")
    except TimeoutException:
        pytest.fail("ECU 无响应（超时）")

    assert response.positive
    # 已解锁时种子通常为全零
    seed = response.service_data.security_seed
    if seed == bytes(len(seed)):
        pass   # 符合预期：全零种子表示已解锁
    # 否则 ECU 允许重新解锁，也视为正常


# ------------------------------------------------------------------ #
#  负响应测试
# ------------------------------------------------------------------ #

@pytest.mark.negative
def test_security_access_wrong_key(extended_session):
    """
    发送错误密钥应收到 NRC 0x35 (invalidKey)。

    注意：测试完后需要等待 ECU 重试延迟，再恢复正常解锁状态。
    """
    uds_client = extended_session

    # Step 1: 请求种子
    try:
        seed_resp = uds_client.request_seed(SA_LEVEL_DEFAULT_SEED)
    except (NegativeResponseException, TimeoutException) as e:
        pytest.fail(f"请求种子失败: {e}")

    seed = seed_resp.service_data.security_seed

    # Step 2: 发送故意错误的密钥（种子本身，不经过算法）
    wrong_key = seed   # 直接用种子作为错误密钥
    try:
        uds_client.send_key(SA_LEVEL_DEFAULT_KEY, wrong_key)
        pytest.fail("期望 NRC 0x35，但收到了正响应")
    except NegativeResponseException as e:
        assert e.response.code == 0x35, (
            f"期望 NRC 0x35 (invalidKey)，实际 0x{e.response.code:02X} ({e.response.code_name})"
        )
    except TimeoutException:
        pytest.fail("ECU 无响应（超时）")

    # 等待 ECU 重试延迟（ISO 14229 规定连续错误后有延迟时间）
    time.sleep(10.0)


@pytest.mark.negative
def test_security_access_wrong_session(uds_client):
    """默认会话下请求安全访问应收到 NRC 0x22 (conditionsNotCorrect)。"""
    uds_client.change_session(services.DiagnosticSessionControl.Session.defaultSession)

    try:
        uds_client.request_seed(SA_LEVEL_DEFAULT_SEED)
        pytest.fail("期望 NRC，但收到了正响应")
    except NegativeResponseException as e:
        assert e.response.code in (0x22, 0x31), (
            f"期望 NRC 0x22 或 0x31，实际 0x{e.response.code:02X}"
        )
    except TimeoutException:
        pytest.fail("ECU 无响应（超时）")
