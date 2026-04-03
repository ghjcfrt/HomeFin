"""
支付宝账单导入解析服务。

此模块提供了解析支付宝账单 CSV 文件的功能，包括解析金额、日期和分类。
"""

from __future__ import annotations

import csv  # 修复未定义问题
import hashlib  # 修复未定义问题
from datetime import datetime
from typing import Any

from ..core.constants import EXPENSE_CATEGORIES, INCOME_CATEGORIES
from .import_common import ImportValidationError, make_issue

# 支付宝账单导入指南链接
ALIPAY_GUIDE_URL = "https://b.alipay.com/page/mbillexprod/account/detail"

# 支付宝账单 CSV 解析函数
REQUIRED_HEADERS_DISPLAY = [
    "入账时间",
    "支付宝交易号",
    "支付宝流水号",
    "收入（+元）",
    "支出（-元）",
]


# 规范化表头
def _normalize_header(value: str) -> str:
    """
    规范化 CSV 表头。

    Args:
        value (str): 原始表头字符串。

    Returns:
        str: 规范化后的表头字符串。
    """
    # 去除全角空格和特殊字符，替换为半角，并去除两端空白
    table = str.maketrans({"（": "(", "）": ")", "＋": "+", "－": "-", " ": ""})
    return value.strip().translate(table)


# 规范化日期字符串
def _decode_csv(content: bytes) -> str:
    # 尝试使用多种常见编码解码 CSV 内容，直到成功或所有选项都失败
    for encoding in ("gb2312", "gb18030", "gbk", "utf-8-sig", "utf-8"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    # 如果所有编码都无法解码，抛出导入验证错误，提示用户检查 CSV 编码格式
    raise ImportValidationError(
        code="ALIPAY_ENCODING_UNSUPPORTED",
        message="CSV 编码无法识别，请确认使用支付宝导出的 GB2312/GBK/GB18030/UTF-8 CSV",
        field="file",
    )


# 解析金额字符串，去除逗号并转换为浮点数
def _parse_amount(raw: str) -> float:
    value = (raw or "").strip().replace(",", "")
    if not value:
        return 0.0
    return float(value)


# 解析入账时间字符串，支持多种日期格式
def _parse_txn_date(raw: str):
    # 去除两端空白后，如果入账时间为空，抛出 ValueError 异常，提示用户入账时间不能为空
    value = (raw or "").strip()
    # 如果入账时间为空，抛出 ValueError 异常，提示用户入账时间不能为空
    if not value:
        raise ValueError("入账时间为空")
    # 尝试使用多种常见的日期时间格式解析入账时间字符串，支持 "YYYY-MM-DD HH:MM:SS" 和 "YYYY-MM-DD" 两种格式
    for fmt, slice_len in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(value[:slice_len], fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析入账时间: {raw}")


# 根据文本内容推断交易类型和分类
def _infer_category(txn_type: str, text: str) -> str:
    # 将文本转换为小写，方便后续关键词匹配
    lowered = text.lower()
    # 定义收入和支出的关键词规则，包含常见的交易类型和对应的分类名称
    income_rules = {
        "工资": ["工资", "薪", "salary"],
        "奖金": ["奖金", "bonus"],
        "红包": ["红包"],
        "理财收益": ["收益", "分红", "利息", "理财"],
    }
    # 定义支出的关键词规则，包含常见的交易类型和对应的分类名称
    expense_rules = {
        "餐饮": ["餐", "奶茶", "咖啡", "外卖", "美团", "饿了么"],
        "交通": ["地铁", "公交", "滴滴", "打车", "高铁", "机票"],
        "购物": ["淘宝", "天猫", "京东", "拼多多", "闲鱼", "超市", "商城"],
        "日用": ["纸巾", "洗衣", "清洁", "日用"],
        "水电煤": ["电费", "水费", "燃气", "煤气"],
        "通讯": ["话费", "流量", "宽带", "通信"],
        "娱乐": ["电影", "游戏", "会员", "娱乐", "音乐"],
        "医疗": ["医院", "药", "诊所", "医疗", "医保"],
        "教育": ["学费", "培训", "课程", "教育"],
        "旅行": ["酒店", "住宿", "旅行", "旅游"],
        "房租": ["房租", "租金", "物业"],
    }
    # 根据交易类型选择对应的关键词规则和默认分类，收入默认分类为 "其他收入"，支出默认分类为 "其他支出"
    rules = income_rules if txn_type == "income" else expense_rules
    default_category = "其他收入" if txn_type == "income" else "其他支出"
    valid_categories = INCOME_CATEGORIES if txn_type == "income" else EXPENSE_CATEGORIES
    # 根据规则匹配文本中的关键词，返回对应的分类名称，如果匹配到的分类不在有效分类列表中，则返回默认分类
    for category, keywords in rules.items():
        if any(keyword in lowered for keyword in keywords):
            return category if category in valid_categories else default_category

    return default_category


# 解析支付宝 CSV 内容，返回可导入的交易记录列表和解析过程中遇到的问题列表
def parse_alipay_csv(
    content: bytes,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # 首先尝试使用多种常见编码解码 CSV 内容，确保能够正确解析支付宝导出的 CSV 文件
    decoded = _decode_csv(content)
    issues: list[dict[str, Any]] = []
    filtered_lines = []
    # 过滤掉空行和注释行（以 # 开头），保留有效的 CSV 行进行后续解析
    for line in decoded.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        filtered_lines.append(line)
    # 如果过滤后没有有效的 CSV 行，抛出导入验证错误，提示用户 CSV 内容为空或不包含账单数据
    if not filtered_lines:
        raise ImportValidationError(
            code="IMPORT_EMPTY_FILE",
            message="CSV 内容为空或不包含账单数据",
            field="file",
        )

    # 使用 csv.reader 解析过滤后的 CSV 行，获取表头和数据行
    reader = csv.reader(filtered_lines)
    rows = list(reader)
    # 如果没有任何行，抛出导入验证错误，提示用户 CSV 内容无法解析
    if not rows:
        raise ImportValidationError(
            code="ALIPAY_CSV_PARSE_FAILED",
            message="CSV 内容无法解析",
            field="file",
        )

    # 规范化表头并验证必须的表头是否存在，如果缺少必须的表头，抛出导入验证错误，提示用户缺少哪些表头
    raw_headers = rows[0]
    header_map = {_normalize_header(name): idx for idx, name in enumerate(raw_headers)}

    required_headers = [_normalize_header(name) for name in REQUIRED_HEADERS_DISPLAY]
    missing = [
        REQUIRED_HEADERS_DISPLAY[idx]
        for idx, normalized_name in enumerate(required_headers)
        if normalized_name not in header_map
    ]
    if missing:
        raise ImportValidationError(
            code="ALIPAY_MISSING_HEADERS",
            message=f"缺少必须表头: {', '.join(missing)}",
            field="headers",
        )

    optional_aliases = {
        "账务类型": ["账务类型"],
        "对方名称": ["对方名称"],
        "商品名称": ["商品名称"],
        "业务描述": ["业务描述"],
        "备注": ["备注"],
        "付款备注": ["付款备注"],
        "商户订单号": ["商户订单号"],
    }

    # 定义一个内部函数，根据表头名称获取对应列的值，如果该列不存在或超出范围，返回空字符串
    def get_value(row: list[str], header: str) -> str:
        idx = header_map.get(_normalize_header(header))
        if idx is None or idx >= len(row):
            return ""
        return (row[idx] or "").strip()

    # 定义一个内部函数，根据可选字段的多个别名获取对应列的值，按照优先级顺序查找，如果都不存在或超出范围，返回空字符串
    def get_optional(row: list[str], key: str) -> str:
        for alias in optional_aliases[key]:
            idx = header_map.get(_normalize_header(alias))
            if idx is not None and idx < len(row):
                return (row[idx] or "").strip()
        return ""

    results: list[dict[str, Any]] = []
    # 从第二行开始逐行解析数据行，提取金额、日期、交易类型和分类等信息，并根据文本内容推断分类，如果解析过程中遇到错误，记录到 issues 列表中
    for row_idx, row in enumerate(rows[1:], start=2):
        if not row:
            continue
        try:
            # 解析收入和支出金额，去除逗号并转换为浮点数，如果收入和支出金额都不大于 0，记录一个警告级别的问题并跳过该行
            income = _parse_amount(get_value(row, "收入（+元）"))
            expense = _parse_amount(get_value(row, "支出（-元）"))
            # 如果收入和支出金额都不大于 0，记录一个警告级别的问题并跳过该行
            if income <= 0 and expense <= 0:
                issues.append(
                    make_issue(
                        code="ALIPAY_ROW_SKIPPED_NO_AMOUNT",
                        message="收入和支出均为空或不大于 0，已跳过",
                        row=row_idx,
                        field="amount",
                    )
                )
                continue
            # 根据收入和支出金额确定交易类型，收入金额大于 0 则为 "income"，否则为 "expense"，并根据交易类型选择对应的金额值
            txn_type = "income" if income > 0 else "expense"
            amount = income if txn_type == "income" else expense
            txn_date = _parse_txn_date(get_value(row, "入账时间"))
            trade_no = get_value(row, "支付宝交易号")
            flow_no = get_value(row, "支付宝流水号")
            # 根据文本内容推断分类，提取多个可选字段构建备注信息，并生成一个唯一的导入键，确保同一笔交易不会被重复导入
            biz_type = get_optional(row, "账务类型")
            counterparty = get_optional(row, "对方名称")
            product_name = get_optional(row, "商品名称")
            biz_desc = get_optional(row, "业务描述")
            memo = get_optional(row, "备注")
            pay_memo = get_optional(row, "付款备注")
            merchant_order = get_optional(row, "商户订单号")
            # 构建备注信息，包含多个可选字段的内容，并用 " | " 分隔，如果没有任何可用字段，则备注为 None，备注长度限制为 200 字符
            note_parts = [
                part
                for part in [
                    biz_type,
                    counterparty,
                    product_name,
                    biz_desc,
                    memo,
                    pay_memo,
                ]
                if part
            ]
            note = " | ".join(note_parts)[:200] if note_parts else None
            # 构建分类文本，包含多个可选字段的内容，并用空格分隔，用于推断分类，分类长度限制为 50 字符
            category_text = " ".join(note_parts)
            category = _infer_category(txn_type, category_text)
            # 生成导入键，包含一个固定的来源标识和多个交易相关字段的值，通过 SHA-256 哈希算法生成一个唯一的字符串，确保同一笔交易不会被重复导入
            import_source = "alipay_csv"
            fingerprint = "|".join(
                [
                    import_source,
                    trade_no,
                    flow_no,
                    merchant_order,
                    str(txn_date),
                    f"{amount:.2f}",
                    txn_type,
                ]
            )
            import_key = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
            # 将解析结果添加到 results 列表中，包含交易类型、分类、金额、日期、备注、外部 ID、来源和导入键等信息，供后续导入使用
            results.append(
                {
                    "selected": True,
                    "type": txn_type,
                    "category": category,
                    "amount": amount,
                    "txn_date": txn_date,
                    "note": note,
                    "external_id": trade_no or flow_no or import_key[:12],
                    "source": import_source,
                    "import_key": import_key,
                }
            )
        # 如果解析过程中遇到任何异常，记录一个错误级别的问题，提示用户第几行解析失败以及具体的错误信息
        except ValueError as exc:
            issues.append(
                make_issue(
                    code="ALIPAY_ROW_PARSE_FAILED",
                    message=f"第 {row_idx} 行解析失败: {exc}",
                    severity="error",
                    row=row_idx,
                )
            )

    if not results:
        issues.append(
            make_issue(
                code="ALIPAY_NO_VALID_ROWS",
                message="未解析到可导入记录",
                severity="error",
            )
        )

    return results, issues
