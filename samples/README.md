# 万象查看器 · Markdown 验收

> 把每一种文件，还原成它本来的样子。

## 支持的排版

- **粗体**、*斜体*、`行内代码`、~~删除线~~
- [链接](https://example.com)
- 表格：

| 格式 | 引擎 | 保真度 |
| --- | --- | --- |
| PDF | PDFium | 原生 |
| DOCX | WPS | 原版式 |
| 图片 | Pillow / Photoshop | 像素级 |

## 代码

```python
def hello(name: str) -> str:
    # 中文注释：你好，世界
    return f"你好，{name}！"

print(hello("万象"))
```

## 数学

行内公式 $E = mc^2$，块级公式：

$$\int_0^1 x^2 dx = \frac{1}{3}$$

## 图片

![示例](sample.png)
