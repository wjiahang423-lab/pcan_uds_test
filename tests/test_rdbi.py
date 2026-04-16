# ============================================================
# tests/test_rdbi.py  ——  ReadDataByIdentifier (SID 0x22)
#
# 测试项：
#   1. 读取各 DID（参数化），验证响应长度 >= min_len
#   2. 若配置了 expected_raw，同时验证原始字节
#   3. 无效 DID → NRC 0x31 (requestOutOfRange)
#   4. 在默认会话中读取仅限扩展会话的 DID → NRC 0x31/0x22
# ============================================================

import pytest
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import RDBI_TEST_CASES

pytestmark = pytest.mark.rdbi


# ---- 正响应：读取已知 DID ----

@pytest.mark.parametrize(
    'case',
    RDBI_TEST_CASES,
    ids=[c['name'] for c in RDBI_TEST_CASES],
)
def test_rdbi_positive(case, extended_session):
    """
    在扩展诊断会话中读取 DID，验证：
      - 收到正响应
      - 数据长度 >= min_len
      - （若配置）原始字节与期望值一致
    """
    uds_client = extended_session
    did      = case['did']
    min_len  = case['min_len']
    expected = case.get('expected_raw')

    try:
        response = uds_client.read_data_by_identifier(didlist=[did])
    except NegativeResponseException as e:
        pytest.fail(
            f"[DID 0x{did:04X}] 期望正响应，收到 NRC 0x{e.response.code:02X} ({e.response.code_name})"
        )
    except TimeoutException:
        pytest.fail(f"[DID 0x{did:04X}] ECU 无响应（超时）")

    assert response.positive, f"[DID 0x{did:04X}] 响应标志非正响应"

    values = response.service_data.values
    assert did in values, f"[DID 0x{did:04X}] 响应中未包含请求的 DID"

    raw_data = values[did].raw_data
    assert len(raw_data) >= min_len, (
        f"[DID 0x{did:04X}] 数据长度 {len(raw_data)} < 期望最小长度 {min_len}"
    )

    if expected is not None:
        assert raw_data == expected, (
            f"[DID 0x{did:04X}] 原始数据不符: 期望={expected.hex()}, 实际={raw_data.hex()}"
        )


# ---- 负响应：无效 DID ----

@pytest.mark.negative
def test_rdbi_invalid_did(extended_session):
    """读取无效 DID (0xFFFF) 应收到 NRC 0x31 (requestOutOfRange)。"""
    INVALID_DID = 0xFFFF
    try:
        extended_session.read_data_by_identifier(didlist=[INVALID_DID])
        pytest.fail("期望 NRC，但收到了正响应")
    except NegativeResponseException as e:
        assert e.response.code in (0x31, 0x22), (
            f"期望 NRC 0x31 或 0x22，实际 0x{e.response.code:02X} ({e.response.code_name})"
        )
    except TimeoutException:
        pytest.fail("ECU 无响应（超时）")


# ---- 负响应：默认会话中读取扩展会话专属 DID ----

@pytest.mark.negative
def test_rdbi_wrong_session(uds_client):
    """
    在默认会话中读取需要扩展会话的 DID，应收到 NRC 0x31 或 0x22。
    （具体 DID 按项目调整，此处以 DID_FINGERPRINT 为例）
    """
    from config import DID_FINGERPRINT

    # 确保在默认会话
    uds_client.change_session(services.DiagnosticSessionControl.Session.defaultSession)

    try:
        uds_client.read_data_by_identifier(didlist=[DID_FINGERPRINT])
        # 若项目中此 DID 在默认会话也可读，则跳过此测试
        pytest.skip("此 DID 在默认会话亦可读，跳过负响应验证")
    except NegativeResponseException as e:
        assert e.response.code in (0x31, 0x22, 0x33), (
            f"期望 NRC 0x22/0x31/0x33，实际 0x{e.response.code:02X}"
        )
    except TimeoutException:
        pytest.fail("ECU 无响应（超时）")
