# ============================================================
# tests/test_ecu_reset.py  ——  ECUReset (SID 0x11)
# 数据来源：UDS_TestCases_Template.xlsx → ECUReset sheet
# ============================================================

import re
import time
import pytest
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.excel_reader import load_ecu_reset_cases

pytestmark = pytest.mark.ecu_reset

_ALL_CASES = load_ecu_reset_cases()

_DEFAULT_REBOOT_WAIT = 5.0   # 默认硬复位等待秒数
_DEFAULT_SOFT_WAIT   = 2.0   # 默认软复位等待秒数


def _parse_wait_seconds(note: str, default: float) -> float:
    """从 note 字段中提取等待秒数，如 '等待 5s' → 5.0，未找到则返回 default。"""
    m = re.search(r'(\d+(?:\.\d+)?)\s*s', note)
    return float(m.group(1)) if m else default


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


@pytest.mark.parametrize('case', _ALL_CASES, ids=[c['id'] for c in _ALL_CASES])
def test_ecu_reset(case, uds_client):
    """统一参数化 ECU 复位测试，正/负响应由 expected 字段控制。"""
    reset_type   = case['reset_type']
    name         = case['name']
    expected     = case['expected']
    expected_nrc = case['nrc']
    note         = case['note']

    if expected == 'Positive':
        try:
            response = uds_client.ecu_reset(reset_type)
        except NegativeResponseException as e:
            pytest.fail(f"[{name}] 期望正响应，收到 NRC 0x{e.response.code:02X} ({e.response.code_name})")
        except TimeoutException:
            pytest.fail(f"[{name}] ECU 无响应（超时）")

        assert response.positive, f"[{name}] 响应标志为非正响应"

        # 根据 note 提取等待时间后轮询上线
        wait_s = _parse_wait_seconds(note, _DEFAULT_REBOOT_WAIT)
        time.sleep(wait_s)
        assert _wait_ecu_online(uds_client), (
            f"[{name}] 复位后 ECU 在 {wait_s + 10:.0f}s 内未重新上线"
        )

    else:  # Negative
        try:
            uds_client.ecu_reset(reset_type)
            pytest.fail(f"[{name}] 期望 NRC，但收到了正响应")
        except NegativeResponseException as e:
            if expected_nrc:
                assert e.response.code in expected_nrc, (
                    f"[{name}] 期望 NRC {[hex(n) for n in expected_nrc]}，"
                    f"实际 0x{e.response.code:02X} ({e.response.code_name})"
                )
        except TimeoutException:
            pytest.fail(f"[{name}] ECU 无响应（超时）")
