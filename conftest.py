# ============================================================
# conftest.py  ——  pytest 全局 fixtures
# ============================================================

import time
import threading
import pytest
import udsoncan
from udsoncan import services
from udsoncan.exceptions import NegativeResponseException, TimeoutException

from config import (
    PCAN_CHANNEL, PCAN_BITRATE,
    ECU_TX_ID, ECU_RX_ID,
    ISOTP_PARAMS,
    P2_TIMEOUT, P2_STAR_TIMEOUT, REQUEST_TIMEOUT,
    TESTER_PRESENT_INTERVAL,
    SESSION_DEFAULT, SESSION_EXTENDED,
)
from utils.uds_client import build_uds_client, close_uds_client


# ------------------------------------------------------------------ #
#  session 级：CAN 总线 + UDS 客户端（整个测试会话共用一个连接）
# ------------------------------------------------------------------ #

@pytest.fixture(scope='session')
def uds_client():
    """
    创建 udsoncan.Client，进入默认会话，整个 pytest session 共用。
    teardown 时关闭连接并释放 PCAN 资源。
    """
    client = build_uds_client(
        channel=PCAN_CHANNEL,
        bitrate=PCAN_BITRATE,
        tx_id=ECU_TX_ID,
        rx_id=ECU_RX_ID,
        p2_timeout=P2_TIMEOUT,
        p2_star_timeout=P2_STAR_TIMEOUT,
        request_timeout=REQUEST_TIMEOUT,
        isotp_params=ISOTP_PARAMS,
    )
    client.open()

    # 上电后等待 ECU 就绪
    time.sleep(0.5)

    # 确认 ECU 在线（默认会话）
    try:
        client.change_session(services.DiagnosticSessionControl.Session.defaultSession)
    except (NegativeResponseException, TimeoutException) as e:
        client.close()
        pytest.exit(f"ECU 无响应，无法开始测试: {e}", returncode=3)

    yield client

    # 恢复默认会话再断开
    try:
        client.change_session(services.DiagnosticSessionControl.Session.defaultSession)
    except Exception:
        pass
    close_uds_client(client)


# ------------------------------------------------------------------ #
#  TesterPresent 保活线程（在需要保持非默认会话的测试模块中使用）
# ------------------------------------------------------------------ #

class _TesterPresentKeepAlive:
    """后台线程，每隔 interval 秒发送一次 TesterPresent(suppressPosRspMsgIndicationBit)。"""

    def __init__(self, client: udsoncan.Client, interval: float):
        self._client   = client
        self._interval = interval
        self._stop_evt = threading.Event()
        self._thread   = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_evt.set()
        self._thread.join(timeout=self._interval + 1)

    def _run(self):
        while not self._stop_evt.wait(self._interval):
            try:
                self._client.tester_present(suppress_positive_response=True)
            except Exception:
                pass  # 测试结束后连接已关闭，忽略


@pytest.fixture
def keep_alive(uds_client):
    """
    函数级 fixture：在测试期间后台发送 TesterPresent 保活。
    适用于需要超过 5s 操作的测试（如 HBRI、编程等）。
    """
    ka = _TesterPresentKeepAlive(uds_client, TESTER_PRESENT_INTERVAL)
    ka.start()
    yield
    ka.stop()


# ------------------------------------------------------------------ #
#  扩展会话 fixture（模块级，进入/退出扩展诊断会话）
# ------------------------------------------------------------------ #

@pytest.fixture(scope='module')
def extended_session(uds_client):
    """
    模块级 fixture：进入扩展诊断会话，模块测试完成后恢复默认会话。
    """
    uds_client.change_session(services.DiagnosticSessionControl.Session.extendedDiagnosticSession)
    yield uds_client
    try:
        uds_client.change_session(services.DiagnosticSessionControl.Session.defaultSession)
    except Exception:
        pass
