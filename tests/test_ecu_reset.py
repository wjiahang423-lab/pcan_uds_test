# ============================================================
# tests/test_ecu_reset.py  ——  ECUReset (SID 0x11)
#
# 测试项：
#   1. HardReset (0x01)            → 正响应 + ECU 重启后重新上线
#   2. SoftReset (0x03)            → 正响应（KeyOffOnReset/SoftReset）
#   3. 无效复位类型                 → NRC 0x12
#
# 注意：HardReset 后需等待 ECU 重启完成（ECU_REBOOT_WAIT_S），
#       然后重新发送 TesterPresent 或 DefaultSession 确认在线。
# ============================================================

import time
import pytest
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

ECU_REBOOT_WAIT_S = 5.0  # ECU 硬复位后等待时间（按实际 ECU 启动时间调整）

pytestmark = pytest.mark.ecu_reset


def _wait_ecu_online(uds_client, timeout: float = 10.0) -> bool:
    """轮询 TesterPresent，等待 ECU 重启上线，超时返回 False。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            uds_client.tester_present(suppress_positive_response=False)
            return True
        except (NegativeResponseException, TimeoutException):
            time.sleep(0.5)
    return False


def test_hard_reset(uds_client):
    """
    HardReset：ECU 应答后断电重启，等待重新上线后确认正常工作。
    """
    try:
        response = uds_client.ecu_reset(services.ECUReset.ResetType.hardReset)
    except NegativeResponseException as e:
        pytest.fail(f"HardReset NRC 0x{e.response.code:02X} ({e.response.code_name})")
    except TimeoutException:
        pytest.fail("HardReset 无响应（超时）")

    assert response.positive, "HardReset 响应标志为非正响应"

    # 等待 ECU 重启
    time.sleep(ECU_REBOOT_WAIT_S)

    # 确认 ECU 重新上线
    assert _wait_ecu_online(uds_client), (
        f"HardReset 后 ECU 在 {ECU_REBOOT_WAIT_S + 10.0:.0f}s 内未重新上线"
    )


def test_soft_reset(uds_client):
    """
    SoftReset：ECU 应答后执行软复位，复位完成后 ECU 保持在线。
    """
    try:
        response = uds_client.ecu_reset(services.ECUReset.ResetType.softReset)
    except NegativeResponseException as e:
        pytest.fail(f"SoftReset NRC 0x{e.response.code:02X} ({e.response.code_name})")
    except TimeoutException:
        pytest.fail("SoftReset 无响应（超时）")

    assert response.positive, "SoftReset 响应标志为非正响应"

    time.sleep(2.0)
    assert _wait_ecu_online(uds_client), "SoftReset 后 ECU 未在 12s 内重新上线"


@pytest.mark.negative
def test_reset_invalid_type(uds_client):
    """无效复位类型（0x7F）应收到 NRC 0x12 (subFunctionNotSupported)。"""
    INVALID_RESET = 0x7F
    try:
        uds_client.ecu_reset(INVALID_RESET)
        pytest.fail("期望 NRC，但收到了正响应")
    except NegativeResponseException as e:
        assert e.response.code in (0x12, 0x31), (
            f"期望 NRC 0x12 或 0x31，实际 0x{e.response.code:02X}"
        )
    except TimeoutException:
        pytest.fail("ECU 无响应（超时）")
