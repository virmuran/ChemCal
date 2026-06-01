"""
批量迁移计算器报告导出：TXT→DOCX, PDF→DOCX2PDF
以 heat_exchanger_calculator.py 为标准参考。
"""
import re
import ast
from pathlib import Path

CALC_DIR = Path(r"C:\Users\Administrator\Desktop\ChemCal\modules\chemical_calculations\calculators")
SKIP = {"heat_exchanger_calculator.py", "__init__.py"}

# 新增的导入块
NEW_IMPORTS = """import sys
from pathlib import Path

# DOCX 报告导出
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.docx_utils import ReportExporter
"""


def get_class_name(content: str) -> str:
    """从文件中提取类名（中文类名）"""
    m = re.search(r'class\s+(\w+)', content)
    return m.group(1) if m else "计算书"


def add_imports(content: str) -> str:
    """在 from modules.combo_box_utils 之前插入新导入"""
    if 'from utils.docx_utils import ReportExporter' in content:
        return content  # 已处理

    # 在 ComboBoxWheelBlocker 导入之后插入
    marker = 'from modules.combo_box_utils import ComboBoxWheelBlocker'
    if marker in content:
        return content.replace(marker, marker + '\n' + NEW_IMPORTS)

    # 降级：在最后一个 from 导入后插入
    lines = content.split('\n')
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('from ') or line.startswith('import '):
            last_import_idx = i

    if last_import_idx > 0:
        lines.insert(last_import_idx + 1, NEW_IMPORTS.rstrip('\n'))
        return '\n'.join(lines)

    return content


def replace_buttons(content: str) -> str:
    """替换按钮相关文本"""
    content = content.replace('download_txt_btn', 'download_docx_btn')
    content = content.replace('self.download_txt_report', 'self.download_docx_report')
    content = content.replace('"下载计算书(TXT)"', '"下载计算书(DOCX)"')
    content = content.replace("'下载计算书(TXT)'", "'下载计算书(DOCX)'")
    return content


def replace_txt_method(content: str, class_name: str) -> str:
    """替换 download_txt_report 方法"""
    new_method = f'''    def download_docx_report(self):
        """生成DOCX格式计算书"""
        ReportExporter.export_docx(self, "{class_name}")'''

    # 匹配从 def download_txt_report 到下一个 def 或 class 的方法体
    pattern = r'    def download_txt_report\(self\):.*?(?=\n    def |\nclass |\nif __name__|\Z)'
    content = re.sub(pattern, new_method, content, count=1, flags=re.DOTALL)

    # 清理多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content


def replace_pdf_method(content: str, class_name: str) -> str:
    """替换 download_pdf_report 方法"""
    new_method = f'''    def download_pdf_report(self):
        """生成PDF格式计算书"""
        ReportExporter.export_pdf(self, "{class_name}")'''

    # 匹配从 def download_pdf_report 到下一个 def 或 class 或 end
    pattern = r'    def download_pdf_report\(self\):.*?(?=\n    def (?!_download_pdf)|(?=\n    def process_content)|(?=\nclass )|(?=\nif __name__)|\Z)'
    content = re.sub(pattern, new_method, content, count=1, flags=re.DOTALL)

    # 清理多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content


def process_file(filepath: Path) -> bool:
    """处理单个文件"""
    try:
        content = filepath.read_text(encoding='utf-8')

        # 跳过已处理
        if 'def download_docx_report' in content:
            print(f"  跳过(已处理): {filepath.name}")
            return True

        # 跳过没有 download_txt_report 的文件
        if 'def download_txt_report' not in content and 'download_txt_btn' not in content:
            print(f"  跳过(无TXT导出): {filepath.name}")
            return True

        class_name = get_class_name(content)
        original = content

        # 1. 添加导入
        content = add_imports(content)

        # 2. 替换按钮引用
        content = replace_buttons(content)

        # 3. 替换 download_txt_report 方法
        if 'def download_txt_report' in content:
            content = replace_txt_method(content, class_name)

        # 4. 替换 download_pdf_report 方法
        if 'def download_pdf_report' in content:
            content = replace_pdf_method(content, class_name)

        # 验证语法
        try:
            ast.parse(content)
        except SyntaxError as e:
            print(f"  语法错误({filepath.name} l{e.lineno}): {e.msg}")
            # 恢复原文件
            filepath.write_text(original, encoding='utf-8')
            return False

        # 写回
        filepath.write_text(content, encoding='utf-8')
        print(f"  完成: {filepath.name} ({class_name})")
        return True

    except Exception as e:
        print(f"  异常: {filepath.name} - {e}")
        return False


def main():
    files = sorted(CALC_DIR.glob("*.py"))
    total = 0
    success = 0
    failed = []

    for f in files:
        if f.name in SKIP:
            continue
        if f.name.startswith('__'):
            continue
        total += 1
        if process_file(f):
            success += 1
        else:
            failed.append(f.name)

    print(f"\n===== 结果: {success}/{total} =====")
    if failed:
        print(f"失败: {failed}")


if __name__ == "__main__":
    main()
