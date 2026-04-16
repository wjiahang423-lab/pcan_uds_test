# ============================================================
# tests/test_dtc.py  ——  DTC 相关服务测试
# 数据来源：UDS_TestCases_Template.xlsx → DTC sheet
# ============================================================

import re
import time
import pytest
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.excel_reader import load_dtc_cases

pytestmark = pytest.mark.dtc

_ALL_CASES = load_dtc_cases()

# DTC 状态掩码常量（ISO 14229 Table D.1）
_STATUS_TEST_FAILED   = 0x01
_STATUS_CONFIRMED_DTC = 0x08


def _parse_status_mask(sub_func: str) -> int:
    """从 sub_func 字符串中提取 statusMask 十六进制值，默认 0xFF。"""
    m = re.search(r'statusMask\s*=\s*(0x[0-9A-Fa-f]+|\d+)', sub_func)
    if m:
        return int(m.group(1), 16) if m.group(1).startswith('0x') else int(m.group(1))
    return 0xFF


def _parse_group_of_dtc(sub_func: str) -> int:
    """从 sub_func 字符串中提取 groupOfDTC 值，默认 0xFFFFFF。"""
    m = re.search(r'groupOfDTC\s*=\s*(0x[0-9A-Fa-f]+)', sub_func)
    return int(m.group(1), 16) if m else 0xFFFFFF


@pytest.mark.parametrize('case', _ALL_CASES, ids=[c['id'] for c in _ALL_CASES])
def test_dtc(case, extended_session):
    """
    统一参数化 DTC 测试，按 sub_func 字段分派：
    - 0x19 0x02  reportDTCByStatusMask
    - 0x19 0x0A  reportSupportedDTCs
    - 0x14       ClearDiagnosticInformation
    - 0x19 0x02（含 confirmed，清除后验证）
    """
    client       = extended_session
    name         = case['name']
    sid          = case['sid']
    sub_func     = case['sub_func']
    expected     = case['expected']
    expected_nrc = case['nrc']

    # ---- SID 0x14：清除 DTC ----
    if sid == 0x14:
        group = _parse_group_of_dtc(sub_func)
        try:
            response = client.clear_dtc(group=group)
        except NegativeResponseException as e:
            if expected == 'Negative' and e.response.code in expected_nrc:
                return
            pytest.fail(f"[{name}] ClearDTC NRC 0x{e.response.code:02X} ({e.response.code_name})")
        except TimeoutException:
            pytest.fail(f"[{name}] ClearDTC 无响应（超时）")
        assert response.positive, f"[{name}] ClearDTC 响应标志非正响应"
        return

    # ---- SID 0x19：ReadDTCInformation ----
    # 清除后验证：先清除再读取（DTC-004 类型）
    if '清除' in case['pre_cond'] or '清除后' in name:
        try:
            client.clear_dtc(group=0xFFFFFF)
        except (NegativeResponseException, TimeoutException) as e:
            pytest.skip(f"[{name}] 前置清除 DTC 失败，跳过: {e}")
        time.sleep(0.5)

    # 子功能分派
    if '0x0A' in sub_func or 'SupportedDTCs' in sub_func:
        try:
            response = client.get_supported_dtc()
        except NegativeResponseException as e:
            pytest.fail(f"[{name}] ReadDTCInfo(0x0A) NRC 0x{e.response.code:02X}")
        except TimeoutException:
            pytest.fail(f"[{name}] ReadDTCInfo(0x0A) 无响应（超时）")
        assert response.positive
        dtcs = response.service_data.dtcs
        print(f"\n  [{name}] ECU 支持 DTC 数量: {len(dtcs)}")
        assert len(dtcs) > 0, f"[{name}] ECU 未返回任何支持的 DTC"

    else:  # 0x02 reportDTCByStatusMask
        status_mask = _parse_status_mask(sub_func)
        try:
            response = client.get_dtc_by_status_mask(status_mask)
        except NegativeResponseException as e:
            pytest.fail(f"[{name}] ReadDTCInfo(0x02) NRC 0x{e.response.code:02X}")
        except TimeoutException:
            pytest.fail(f"[{name}] ReadDTCInfo(0x02) 无响应（超时）")
        assert response.positive
        dtcs = response.service_data.dtcs
        print(f"\n  [{name}] statusMask=0x{status_mask:02X} DTC 数量: {len(dtcs)}")
        for dtc in dtcs:
            print(f"    DTC 0x{dtc.id:06X}  状态字节: 0x{dtc.status.byte:02X}")

        # 清除后读取：confirmed DTC 应为 0
        if '清除' in case['pre_cond'] or '清除后' in name:
            confirmed = [d for d in dtcs if d.status.confirmed_dtc]
            assert len(confirmed) == 0, (
                f"[{name}] 清除后仍有 {len(confirmed)} 个 Confirmed DTC: "
                + ', '.join(f"0x{d.id:06X}" for d in confirmed)
            )
