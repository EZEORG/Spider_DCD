import os
import pytest
import subprocess
from pathlib import Path

# 定义 app 文件夹路径
APP_DIR = Path(__file__).resolve().parent.parent / 'app'

# 定义测试生成文件的文件夹
REVIEWS_DIR = Path(__file__).resolve().parent.parent / 'autohome_reviews'
DATA_DIR = Path(__file__).resolve().parent.parent / 'dcd_data'

# 捕获控制台输出
@pytest.fixture
def capture_console_output():
    from io import StringIO
    import sys

    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    yield captured_output
    sys.stdout = old_stdout

# 运行项目根目录下的 clear.py 脚本
def run_clear_script():
    clear_script = Path(__file__).resolve().parent.parent / 'clear.py'
    subprocess.run(["python", clear_script], check=True)

# 运行 app 文件夹中的所有 Python 脚本
def run_all_scripts():
    for script in APP_DIR.glob("*.py"):
        subprocess.run(["python", script], check=True)

# 测试控制台输出
@pytest.mark.timeout(120)  # 设置超时时间为120秒
def test_console_output(capture_console_output):
    run_clear_script()  # 运行清理脚本
    run_all_scripts()
    output = capture_console_output.getvalue()
    assert "数据已保存到" in output  # 检查控制台输出是否包含“数据已保存到”
    run_clear_script()  # 测试结束后再次运行清理脚本

# 测试生成的 CSV 文件
@pytest.mark.timeout(120)  # 设置超时时间为120秒
def test_generated_csv_files():
    run_clear_script()  # 运行清理脚本
    run_all_scripts()

    # 确认生成了 autohome_reviews 中的 CSV 文件
    reviews_csv_files = list(REVIEWS_DIR.glob("*.csv"))
    assert len(reviews_csv_files) > 0, "autohome_reviews 文件夹中没有生成 CSV 文件"

    # 确认生成了 dcd_data 中的 CSV 文件
    data_csv_files = list(DATA_DIR.glob("*.csv"))
    assert len(data_csv_files) > 0, "dcd_data 文件夹中没有生成 CSV 文件"
    
    run_clear_script()  # 测试结束后再次运行清理脚本

# 运行所有测试
if __name__ == "__main__":
    pytest.main()
