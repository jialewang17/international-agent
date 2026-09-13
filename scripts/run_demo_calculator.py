"""运行 demo_calculator 工具并显示结果的脚本。"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from tools.demo_calculator import demo_calculator
from utils.task_context import set_task_id
from utils.path import ensure_task_dirs
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def main():
    """主函数：运行 demo_calculator 工具并显示结果"""
    # 创建临时任务ID用于保存结果
    task_id = str(uuid.uuid4())
    set_task_id(task_id)
    ensure_task_dirs(task_id)
    
    console.print("[bold cyan]运行 Demo Calculator 工具[/bold cyan]")
    console.print()
    
    # 测试用例
    test_cases = [
        {"value1": 10, "value2": 5, "operation": "add"},
        {"value1": 20, "value2": 8, "operation": "subtract"},
        {"value1": 6, "value2": 7, "operation": "multiply"},
        {"value1": 100, "value2": 4, "operation": "divide"},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        console.print(f"[bold yellow]测试用例 {i}:[/bold yellow]")
        console.print(f"  输入: value1={test_case['value1']}, value2={test_case['value2']}, operation={test_case['operation']}")
        
        try:
            # 调用工具
            result_json = demo_calculator.invoke(test_case)
            
            # 解析结果
            result = json.loads(result_json)
            
            # 显示结果
            if "error" in result:
                console.print(f"[red]错误: {result['error']}[/red]")
            else:
                console.print(f"[green]计算结果: {result.get('calculation', 'N/A')}[/green]")
                console.print(f"[green]结果值: {result.get('result', 'N/A')}[/green]")
                
                if result.get("result_file_path"):
                    console.print(f"[dim]结果文件: {result['result_file_path']}[/dim]")
                
                # 显示完整的 JSON 结果
                result_str = json.dumps(result, ensure_ascii=False, indent=2)
                console.print()
                console.print(Panel(
                    Syntax(result_str, "json", theme="monokai", line_numbers=False),
                    title="[bold]完整结果[/bold]",
                    border_style="green"
                ))
        
        except Exception as e:
            console.print(f"[red]执行失败: {str(e)}[/red]")
            import traceback
            traceback.print_exc()
        
        console.print()
        console.print("[dim]" + "─" * 60 + "[/dim]")
        console.print()
    
    console.print(f"[dim]任务ID: {task_id}[/dim]")
    console.print(f"[dim]结果保存在: sandbox/{task_id}/[/dim]")


if __name__ == "__main__":
    main()
