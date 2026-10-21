# -*- coding: utf-8 -*-
"""演示：中文注释与 Unicode 字符串。"""
from dataclasses import dataclass

@dataclass
class 文件:
    名称: str
    大小: int

    def 描述(self) -> str:
        return f"{self.名称}（{self.大小} 字节）"

def 斐波那契(n: int) -> list[int]:
    结果 = [0, 1]
    while len(结果) < n:
        结果.append(结果[-1] + 结果[-2])
    return 结果[:n]

if __name__ == "__main__":
    print(斐波那契(10))
    print(文件("验收文档.docx", 72410).描述())
