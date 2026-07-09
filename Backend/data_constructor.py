import random
import string
from openpyxl import Workbook

def generate_password():
    """生成一个包含数字、大小写字母和符号的随机密码"""
    digits = string.digits
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?/~"
    all_chars = lowercase + uppercase

    length = random.randint(10)

    # 至少包含四种类型各一个
    password = [
        random.choice(symbols)
    ]
    # 填充剩余部分
    for _ in range(5):
        password.append(random.choice(all_chars))
    for _ in range(4):
        password.append(random.choice(digits))
    random.shuffle(password)
    return ''.join(password)


def main():
    # 生成100个密码
    passwords = [generate_password() for _ in range(630)]

    # 控制台打印预览
    print("=" * 60)
    print("             随机密码生成器（100个密码）")
    print("=" * 60)
    for i, pwd in enumerate(passwords, 1):
        print(f"{i:3d}. {pwd}")
    print("-" * 60)

    # 写入 Excel 文件
    wb = Workbook()
    ws = wb.active
    ws.title = "密码列表"

    # 添加表头
    ws.append(["序号", "密码", "长度"])

    # 逐行写入
    for idx, pwd in enumerate(passwords, 1):
        ws.append([idx, pwd, len(pwd)])

    # 保存文件
    filename = "stu_passwords.xlsx"
    wb.save(filename)
    print(f"✅ 已自动导出到 Excel 文件：{filename}")


if __name__ == "__main__":
    main()