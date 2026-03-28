import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

# 1. 准备数据
# metrics = ['Utility Rate', 'Attack Success Rate\n(ASR)', 'Defense Success Rate']
metrics = ['效用率', '攻击成功率\n(ASR)', '防御成功率']

# 原始模型数据 (qwen3-max 裸奔)
original_scores = [46.25, 34.17, 65.83]

# benchmark defense
repeat_user_prompt = [56.25, 24.58, 75.42]
spotlighting_with_delimiting = [42.08, 35.83, 64.17]

# OurFrame 框架数据
ourframe_scores = [54.58, 0.00, 100.00]

# 2. 图表样式设置 (学术风)
# plt.rcParams['font.family'] = 'serif'
# plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
# plt.rcParams['axes.unicode_minus'] = False

# 设置使用衬线字体--中文
font_path = './font/SimHei.ttf'  # 替换成你实际的字体文件名
font_manager.fontManager.addfont(font_path)
prop = font_manager.FontProperties(fname=font_path)
font_name = prop.get_name()

# 4. 全局设置使用这个字体
plt.rcParams['font.family'] = font_name
plt.rcParams['axes.unicode_minus'] = False  # 正常显示负号

fig, ax = plt.subplots(figsize=(12, 6), dpi=300) # 加宽图表以容纳更多柱子

x = np.arange(len(metrics))  # 指标的标签位置
width = 0.15 # 减小柱子宽度以便更好地分隔不同的组

# 颜色设置
color_original = '#4C72B0'
color_defense_1 = '#C44E52'
color_defense_2 = '#8172B3'
color_ourframe = '#CCB974'

# 绘制柱状图
rects1 = ax.bar(x - width*1.5, original_scores, width, label='原始模型(qwen3-max)', color=color_original, edgecolor='black', linewidth=1)
rects2 = ax.bar(x - width/2, repeat_user_prompt, width, label='repeat_user_prompt', color=color_defense_1, edgecolor='black', linewidth=1)
rects3 = ax.bar(x + width/2, spotlighting_with_delimiting, width, label='spotlighting_with_delimiting', color=color_defense_2, edgecolor='black', linewidth=1)
# rects4 = ax.bar(x + width*1.5, ourframe_scores, width, label='Dual-Layer Funnel', color=color_ourframe, edgecolor='black', linewidth=1)
rects4 = ax.bar(x + width*1.5, ourframe_scores, width, label='双层漏斗框架', color=color_ourframe, edgecolor='black', linewidth=1)

# ... （其余美化部分保持不变）
ax.set_ylabel('百分比 (%)', fontsize=13, fontweight='bold')
# ax.set_title('Performance Comparison(Workspace Suite)', fontsize=15, fontweight='bold', pad=20)
ax.set_title('效果对比(Workspace Suite)', fontsize=15, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(metrics, fontsize=12, fontweight='bold')
ax.set_ylim(0, 115) # 留出顶部空间显示数据标签

# 隐藏顶部和右侧的边框线 (学术图表惯用做法)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# 图例设置
ax.legend(fontsize=12, loc='upper left')


# 添加数值标签的函数也需要更新以处理所有柱子
def autolabel(rects):
    """在每个柱子顶部添加具体的百分比数值"""
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.2f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 5),  # 垂直偏移 5 个像素
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, fontweight='bold')

autolabel(rects1)
autolabel(rects2)
autolabel(rects3)
autolabel(rects4)

# 保存与展示
plt.tight_layout()
plt.savefig('results_zh.png', dpi=300, bbox_inches='tight')
print("图表已成功生成并保存为 'results_zh.png'")
