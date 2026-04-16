# ============================================================
# config.py  ——  PCAN UDS 诊断测试工程全局配置
# ============================================================

import os

# ---- 测试用例 Excel 数据源 ----
EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'UDS_TestCases_Template.xlsx')

# ---- PCAN 硬件 ----
PCAN_CHANNEL = 'PCAN_USBBUS1'   # Peak PCAN USB 通道
PCAN_BITRATE = 500000            # CAN 波特率 (bps)

# ---- ECU 物理寻址（11-bit Normal Addressing）----
ECU_TX_ID = 0x7E0    # 上位机 -> ECU  (物理寻址)
ECU_RX_ID = 0x7E8    # ECU -> 上位机
FUNC_TX_ID = 0x7DF   # 功能寻址（广播），仅部分测试需要

# ---- ISO-TP 参数 ----
ISOTP_PARAMS = {
    'stmin':      0,      # 最小帧间隔 (ms)，0 = 无延迟
    'blocksize':  0,      # 流控块大小，0 = 无限制
    'tx_padding': 0xAA,   # 填充字节（部分 ECU 要求 CAN 帧补齐 8 字节）
}

# ---- UDS 超时配置 (s) ----
P2_TIMEOUT       = 5.0   # 普通请求最大响应时间
P2_STAR_TIMEOUT  = 10.0  # 0x78 pendingResponse 后最大等待时间
REQUEST_TIMEOUT  = 5.0   # udsoncan 请求超时

# ---- TesterPresent 保活间隔 (s) ----
TESTER_PRESENT_INTERVAL = 2.0

# ---- 安全访问级别 ----
SA_LEVEL_DEFAULT_SEED  = 0x01   # 扩展会话种子请求
SA_LEVEL_DEFAULT_KEY   = 0x02   # 扩展会话密钥发送
SA_LEVEL_PROG_SEED     = 0x11   # 编程会话种子请求（各项目不同，按需修改）
SA_LEVEL_PROG_KEY      = 0x12   # 编程会话密钥发送

# ---- DID 定义（按项目替换为实际值）----
DID_VIN             = 0xF190
DID_ECU_SW_VERSION  = 0xF189
DID_ECU_HW_VERSION  = 0xF193
DID_FINGERPRINT     = 0xF15A
DID_ECU_SERIAL_NUM  = 0xF18C
DID_SUPPLIER_ID     = 0xF18A

# ---- DTC 状态掩码 ----
DTC_STATUS_MASK_ALL = 0xFF

# ---- 会话类型枚举（与 udsoncan 对应）----
SESSION_DEFAULT    = 0x01
SESSION_PROGRAMMING = 0x02
SESSION_EXTENDED   = 0x03
