# ============================================================
# utils/uds_client.py  ——  UDS 客户端工厂
#
# 封装 python-can + python-can-isotp + udsoncan 的初始化过程。
# 对外只暴露 build_uds_client()，返回已连接的 udsoncan.Client。
#
# 依赖：
#   pip install python-can can-isotp udsoncan
#   PCAN 驱动：PEAK PCAN Basic / PCAN-USB Driver
# ============================================================

import threading
import can
import isotp
from udsoncan.client import Client
from udsoncan import configs as uds_configs
from udsoncan.connections import PythonIsoTpConnection

from utils.seed_key import security_algo_v1


def build_uds_client(
    channel: str,
    bitrate: int,
    tx_id: int,
    rx_id: int,
    p2_timeout: float = 5.0,
    p2_star_timeout: float = 10.0,
    request_timeout: float = 5.0,
    isotp_params: dict = None,
) -> Client:
    """
    创建并返回一个已连接的 udsoncan.Client。

    调用方负责在使用完毕后调用 client.close()，
    或通过 with 语句使用（udsoncan.Client 支持上下文管理器）。

    参数
    ----
    channel         : PCAN 通道，e.g. 'PCAN_USBBUS1'
    bitrate         : CAN 波特率，e.g. 500000
    tx_id           : 物理寻址发送 ID（上位机 -> ECU）
    rx_id           : ECU 响应 ID
    p2_timeout      : 普通请求超时 (s)
    p2_star_timeout : pendingResponse 后超时 (s)
    request_timeout : udsoncan 全局超时 (s)
    isotp_params    : dict，覆盖 ISO-TP 默认参数

    返回
    ----
    udsoncan.Client  （未进入任何会话，调用方决定是否 change_session）
    """
    _isotp_params = {'stmin': 0, 'blocksize': 0, 'tx_padding': 0xAA}
    if isotp_params:
        _isotp_params.update(isotp_params)

    # 1. 打开 PCAN CAN 总线
    bus = can.Bus(interface='pcan', channel=channel, bitrate=bitrate)

    # 2. 建立 ISO-TP 传输栈
    addr = isotp.Address(
        isotp.AddressingMode.Normal_11bits,
        txid=tx_id,
        rxid=rx_id,
    )
    notifier = can.Notifier(bus, [])
    stack = isotp.NotifierBasedCanStack(
        bus=bus,
        notifier=notifier,
        address=addr,
        params=_isotp_params,
    )

    # 3. 创建 udsoncan 连接
    conn = PythonIsoTpConnection(stack)

    # 4. UDS 客户端配置
    uds_config = uds_configs.default_client_config.copy()
    uds_config.update({
        'request_timeout':  request_timeout,
        'p2_timeout':       p2_timeout,
        'p2_star_timeout':  p2_star_timeout,
        'security_algo':    security_algo_v1,
        'security_algo_params': None,
        'standard_version': 2020,  # ISO 14229-1:2020
    })

    client = Client(conn, config=uds_config)

    # 保存底层对象引用，便于 conftest 清理
    client._pcan_bus      = bus
    client._can_notifier  = notifier

    return client


def close_uds_client(client: Client) -> None:
    """完整释放 UDS 客户端及底层 CAN 资源。"""
    try:
        client.close()
    except Exception:
        pass
    notifier = getattr(client, '_can_notifier', None)
    if notifier:
        notifier.stop()
    bus = getattr(client, '_pcan_bus', None)
    if bus:
        try:
            bus.shutdown()
        except Exception:
            pass
