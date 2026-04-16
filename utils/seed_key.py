# ============================================================
# utils/seed_key.py  ——  SecurityAccess 种子-密钥算法
#
# !! 此处为占位实现，请替换为项目实际算法 !!
#
# udsoncan 回调签名（v1.x）：
#   def security_algo(level: int, seed: bytes, params: Any) -> bytes
#
# udsoncan 回调签名（v2.x）：
#   def security_algo(seed_params: SeedAlgoParam) -> bytes
#   其中 seed_params.security_level、seed_params.seed
#
# conftest.py 中将 security_algo 注入 UDS client config。
# ============================================================


def compute_key_level01(seed: bytes) -> bytes:
    """
    扩展会话安全访问密钥计算（Level 0x01/0x02）。

    示例：按字节 XOR 0xFF（请替换为实际算法）。
    """
    return bytes(b ^ 0xFF for b in seed)


def compute_key_level11(seed: bytes) -> bytes:
    """
    编程会话安全访问密钥计算（Level 0x11/0x12）。

    示例：循环左移 + XOR（请替换为实际算法）。
    """
    result = bytearray(len(seed))
    for i, b in enumerate(seed):
        rotated = ((b << 1) | (b >> 7)) & 0xFF
        result[i] = rotated ^ 0x3C
    return bytes(result)


# ---- udsoncan v1.x 兼容回调 ----
def security_algo_v1(level: int, seed: bytes, params) -> bytes:
    """
    udsoncan 1.x 风格的安全算法回调。
    根据 level 分发到对应计算函数。
    """
    if level in (0x01, 0x02):
        return compute_key_level01(seed)
    if level in (0x11, 0x12):
        return compute_key_level11(seed)
    raise ValueError(f"未知安全访问级别: 0x{level:02X}")


# ---- udsoncan v2.x 兼容回调 ----
def security_algo_v2(seed_params) -> bytes:
    """
    udsoncan 2.x 风格的安全算法回调。
    seed_params 包含 .security_level 和 .seed 属性。
    """
    return security_algo_v1(seed_params.security_level, seed_params.seed, None)
