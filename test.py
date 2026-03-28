import matplotlib.font_manager as fm

# 获取所有 Matplotlib 能够找到的字体
fonts = fm.fontManager.ttflist

# 挑选出名字里带有常见中文字体拼音或缩写的字体
chinese_keywords = ['Hei', 'Song', 'Kai', 'Ming', 'CJK', 'WenQuanYi']

print("Matplotlib 检测到的可能支持中文的字体有：")
for font in fonts:
    for kw in chinese_keywords:
        if kw in font.name:
            print(f"字体名称: '{font.name}'  |  文件路径: {font.fname}")
            break