# ============================================================
# tests/test_dtc.py  ——  DTC 相关服务测试
#
# 覆盖服务：
#   SID 0x19  ReadDTCInformation
#     - 0x02 reportDTCByStatusMask
#     - 0x0A reportSupportedDTCs
#   SID 0x14  ClearDiagnosticInformation
#
# 测试项：
#   1. 读取当前激活的 DTC（statusMask = 0x09: confirmed + testFailed）
#   2. 读取所有支持的 DTC（0x0A）
#   3. 清除全部 DTC（groupOfDTC = 0xFFFFFF）→ 正响应
#   4. 清除后再读取，已清除的 DTC 不再出现
# ============================================================

import time
import pytest
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import DTC_STATUS_MASK_ALL

pytestmark = pytest.mark.dtc

# DTC 状态掩码定义（ISO 14229 Table D.1）
STATUS_TEST_FAILED              = 0x01
STATUS_CONFIRMED_DTC            = 0x08
STATUS_TEST_FAILED_OR_CONFIRMED = STATUS_TEST_FAILED | STATUS_CONFIRMED_DTC


def test_read_dtc_by_status_mask(extended_session):
    """
    reportDTCByStatusMask (0x19 0x02)：
    读取所有激活（confirmed + testFailed）DTC，
    验证响应格式正确，打印 DTC 列表供人工检查。
    """
    uds_client = extended_session

    try:
        response = uds_client.get_dtc_by_status_mask(STATUS_TEST_FAILED_OR_CONFIRMED)
    except NegativeResponseException as e:
        pytest.fail(f"ReadDTCInfo(0x02) NRC 0x{e.response.code:02X} ({e.response.code_name})")
    except TimeoutException:
        pytest.fail("ReadDTCInfo(0x02) 无响应（超时）")

    assert response.positive
    dtcs = response.service_data.dtcs
    print(f"\n  当前激活 DTC 数量: {len(dtcs)}")
    for dtc in dtcs:
        print(f"    DTC 0x{dtc.id:06X}  状态字节: 0x{dtc.status.byte:02X}")


def test_read_supported_dtcs(extended_session):
    """
    reportSupportedDTCs (0x19 0x0A)：
    读取 ECU 支持的所有 DTC，验证响应成功且不为空。
    """
    uds_client = extended_session

    try:
        response = uds_client.get_supported_dtc()
    except NegativeResponseException as e:
        pytest.fail(f"ReadDTCInfo(0x0A) NRC 0x{e.response.code:02X} ({e.response.code_name})")
    except TimeoutException:
        pytest.fail("ReadDTCInfo(0x0A) 无响应（超时）")

    assert response.positive
    dtcs = response.service_data.dtcs
    print(f"\n  ECU 支持 DTC 数量: {len(dtcs)}")
    assert len(dtcs) > 0, "ECU 未返回任何支持的 DTC，请确认 ECU 软件配置"


def test_clear_dtc(extended_session):
    """
    ClearDiagnosticInformation (0x14)：
    清除全部 DTC (groupOfDTC = 0xFFFFFF)，应收到正响应。
    """
    uds_client = extended_session

    try:
        response = uds_client.clear_dtc(group=0xFFFFFF)
    except NegativeResponseException as e:
        pytest.fail(f"ClearDTC NRC 0x{e.response.code:02X} ({e.response.code_name})")
    except TimeoutException:
        pytest.fail("ClearDTC 无响应（超时）")

    assert response.positive, "ClearDTC 响应标志非正响应"


def test_read_dtc_after_clear(extended_session):
    """
    清除 DTC 后再读取，verified DTC（confirmed 位）数量应为 0。
    （需先运行 test_clear_dtc，或在 fixture 中先执行清除）
    """
    uds_client = extended_session

    # 执行清除
    try:
        uds_client.clear_dtc(group=0xFFFFFF)
    except (NegativeResponseException, TimeoutException) as e:
        pytest.skip(f"前置清除 DTC 失败，跳过验证: {e}")

    time.sleep(0.5)

    # 读取 confirmed DTC
    try:
        response = uds_client.get_dtc_by_status_mask(STATUS_CONFIRMED_DTC)
    except (NegativeResponseException, TimeoutException) as e:
        pytest.fail(f"清除后读取 DTC 失败: {e}")

    confirmed_dtcs = [d for d in response.service_data.dtcs
                      if d.status.confirmed_dtc]

    assert len(confirmed_dtcs) == 0, (
        f"清除 DTC 后仍有 {len(confirmed_dtcs)} 个 Confirmed DTC: "
        + ', '.join(f"0x{d.id:06X}" for d in confirmed_dtcs)
    )
