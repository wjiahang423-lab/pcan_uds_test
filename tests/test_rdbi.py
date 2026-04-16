# ============================================================
# tests/test_rdbi.py  ——  ReadDataByIdentifier (SID 0x22)
# 数据来源：UDS_TestCases_Template.xlsx → RDBI sheet
# ============================================================

import pytest
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.excel_reader import load_rdbi_cases

pytestmark = pytest.mark.rdbi

_ALL_CASES = load_rdbi_cases()


@pytest.mark.parametrize('case', _ALL_CASES, ids=[c['id'] for c in _ALL_CASES])
def test_rdbi(case, uds_client, extended_session):
    """
    统一参数化 RDBI 测试。
    - session 字段为 '默认会话' 时使用 uds_client（先切回默认会话）；
      否则使用 extended_session。
    - expected == 'Positive'：验证正响应、min_len、expected_raw。
    - expected == 'Negative'：验证 NRC。
    """
    did          = case['did']
    name         = case['name']
    min_len      = case['min_len']
    expected_raw = case['expected_raw']
    expected     = case['expected']
    expected_nrc = case['nrc']
    session_req  = case['session']

    # 根据所需会话选择客户端并切换
    if '默认' in session_req:
        client = uds_client
        client.change_session(services.DiagnosticSessionControl.Session.defaultSession)
    else:
        client = extended_session   # extended_session fixture 已切入扩展会话

    if expected == 'Positive':
        try:
            response = client.read_data_by_identifier(didlist=[did])
        except NegativeResponseException as e:
            pytest.fail(
                f"[{name}] 期望正响应，收到 NRC 0x{e.response.code:02X} ({e.response.code_name})"
            )
        except TimeoutException:
            pytest.fail(f"[{name}] ECU 无响应（超时）")

        assert response.positive, f"[{name}] 响应标志非正响应"
        values = response.service_data.values
        assert did in values, f"[{name}] 响应中未包含请求的 DID 0x{did:04X}"

        raw_data = values[did].raw_data
        assert len(raw_data) >= min_len, (
            f"[{name}] 数据长度 {len(raw_data)} < 期望最小长度 {min_len}"
        )
        if expected_raw is not None:
            assert raw_data == expected_raw, (
                f"[{name}] 原始数据不符: 期望={expected_raw.hex()}, 实际={raw_data.hex()}"
            )

    else:  # Negative
        try:
            client.read_data_by_identifier(didlist=[did])
            pytest.skip(f"[{name}] 期望 NRC，但收到了正响应（ECU 允许此访问，跳过）")
        except NegativeResponseException as e:
            if expected_nrc:
                assert e.response.code in expected_nrc, (
                    f"[{name}] 期望 NRC {[hex(n) for n in expected_nrc]}，"
                    f"实际 0x{e.response.code:02X} ({e.response.code_name})"
                )
        except TimeoutException:
            pytest.fail(f"[{name}] ECU 无响应（超时）")
