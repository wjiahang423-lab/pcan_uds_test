# ============================================================
# config.py  ——  PCAN UDS 诊断测试工程全局配置
# ============================================================

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

# RDBI 测试用例：DID -> 期望最小数据长度（字节）
# 若 expected_raw 不为 None，则同时比对原始字节内容
RDBI_TEST_CASES = [
    {'name': 'VIN',            'did': DID_VIN,            'min_len': 17, 'expected_raw': None},
    {'name': 'SW_Version',     'did': DID_ECU_SW_VERSION, 'min_len': 1,  'expected_raw': None},
    {'name': 'HW_Version',     'did': DID_ECU_HW_VERSION, 'min_len': 1,  'expected_raw': None},
    {'name': 'ECU_SerialNum',  'did': DID_ECU_SERIAL_NUM, 'min_len': 4,  'expected_raw': None},
]

# ---- RoutineControl 测试用例 ----
# routine_id -> {'name', 'session', 'start_data', 'expect_result_len'}
ROUTINE_TEST_CASES = [
    {
        'name':              'CheckProgrammingDependencies',
        'routine_id':        0xFF01,
        'session':           'extended',
        'start_data':        b'',
        'expect_result_len': 0,   # 0 = 不验证结果长度
    },
]

# ---- DTC 状态掩码 ----
DTC_STATUS_MASK_ALL = 0xFF

# ---- 会话类型枚举（与 udsoncan 对应）----
SESSION_DEFAULT    = 0x01
SESSION_PROGRAMMING = 0x02
SESSION_EXTENDED   = 0x03
