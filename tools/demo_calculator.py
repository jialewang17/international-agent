"""计算工具：执行基本的数学运算。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from langchain_core.tools import tool

from utils.path import ensure_task_dirs
from utils.task_context import get_task_id


def _calculate(value1: float, value2: float, operation: str) -> float:
    """
    执行计算操作
    
    Args:
        value1: 第一个数值
        value2: 第二个数值
        operation: 运算类型（add/subtract/multiply/divide）
    
    Returns:
        计算结果
    """
    operation = operation.lower().strip()
    
    if operation == "add" or operation == "+" or operation == "加":
        return value1 + value2
    elif operation == "subtract" or operation == "-" or operation == "减":
        return value1 - value2
    elif operation == "multiply" or operation == "*" or operation == "乘":
        return value1 * value2
    elif operation == "divide" or operation == "/" or operation == "除":
        if value2 == 0:
            raise ValueError("除数不能为零")
        return value1 / value2
    else:
        raise ValueError(f"不支持的运算类型: {operation}")


def _generate_result_filename() -> str:
    """生成结果文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"calculator_result_{timestamp}.json"


@tool
def demo_calculator(
    value1: float,
    value2: float,
    operation: str
) -> str:
    """
    描述：执行基本的数学运算计算工具。根据提供的两个数值和运算类型（加、减、乘、除），执行相应的数学运算并保存结果。
    使用时机：当需要进行数学运算时调用本工具。
    输入：
    - value1（必填）：第一个数值，浮点数类型。
    - value2（必填）：第二个数值，浮点数类型。
    - operation（必填）：运算类型，支持以下值：
        - "add" 或 "+" 或 "加"：加法运算
        - "subtract" 或 "-" 或 "减"：减法运算
        - "multiply" 或 "*" 或 "乘"：乘法运算
        - "divide" 或 "/" 或 "除"：除法运算
    输出：JSON字符串，包含以下字段：
    - result：计算结果（浮点数）
    - value1：第一个输入值
    - value2：第二个输入值
    - operation：运算类型
    - calculation：计算表达式（例如 "10 + 5 = 15"）
    - result_file_path：结果文件保存路径（保存在任务目录中，JSON格式）
    """
    import json as json_module
    
    # 执行计算
    try:
        result = _calculate(value1, value2, operation)
    except ValueError as e:
        return json_module.dumps({
            "error": str(e),
            "result": None,
            "value1": value1,
            "value2": value2,
            "operation": operation,
            "calculation": "",
            "result_file_path": ""
        }, ensure_ascii=False)
    except Exception as e:
        return json_module.dumps({
            "error": f"计算失败: {str(e)}",
            "result": None,
            "value1": value1,
            "value2": value2,
            "operation": operation,
            "calculation": "",
            "result_file_path": ""
        }, ensure_ascii=False)
    
    # 构建计算表达式
    operation_symbols = {
        "add": "+",
        "subtract": "-",
        "multiply": "*",
        "divide": "/",
        "+": "+",
        "-": "-",
        "*": "*",
        "/": "/",
        "加": "+",
        "减": "-",
        "乘": "*",
        "除": "/"
    }
    symbol = operation_symbols.get(operation.lower().strip(), operation)
    calculation = f"{value1} {symbol} {value2} = {result}"
    
    # 构建结果
    result_data: Dict[str, Any] = {
        "result": result,
        "value1": value1,
        "value2": value2,
        "operation": operation,
        "calculation": calculation,
        "timestamp": datetime.now().isoformat()
    }
    
    # 获取任务ID并保存结果文件
    task_id = get_task_id()
    result_file_path = ""
    
    if task_id:
        try:
            # 确保任务目录存在
            task_dir = ensure_task_dirs(task_id)
            
            # 生成文件名
            filename = _generate_result_filename()
            result_file = task_dir / filename
            
            result_file_path = str(result_file)
            
            # 在保存前添加文件路径到结果中
            result_data["result_file_path"] = result_file_path
            
            # 保存JSON文件
            with open(result_file, 'w', encoding='utf-8', errors='replace') as f:
                json_module.dump(result_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            result_data["save_error"] = f"保存结果文件失败: {str(e)}"
            result_data["result_file_path"] = ""
    else:
        result_data["save_error"] = "未找到任务ID，无法保存结果文件"
        result_data["result_file_path"] = ""
    
    return json_module.dumps(result_data, ensure_ascii=False)
