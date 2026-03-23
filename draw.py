import matplotlib.pyplot as plt
import numpy as np

# 1. 准备数据
metrics = ['Utility Rate', 'Attack Success Rate\n(ASR)', 'Defense Success Rate']

# 原始模型数据 (qwen3-max 裸奔)
original_scores = [46.25, 34.17, 65.83]

# benchmark defense
repeat_user_prompt = [56.25, 24.58, 75.42]
spotlighting_with_delimiting = [42.08, 35.83, 64.17]

# OurFrame 框架数据
ourframe_scores = [54.58, 0.00, 100.00]

# 2. 图表样式设置 (学术风)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['axes.unicode_minus'] = False
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

x = np.arange(len(metrics))  # 指标的标签位置
width = 0.35  # 柱子的宽度

# 颜色设置
color_original = '#4C72B0'
color_defense_1 = '#C44E52'
color_defense_2 = '#8172B3'
color_ourframe = '#CCB974'


# 绘制柱状图
rects1 = ax.bar(x - width/2, original_scores, width, label='Original (qwen3-max)', color=color_original, edgecolor='black', linewidth=1)
rects2 = ax.bar(x + width/2, ourframe_scores, width, label='OurFrame (Dual-Layer Funnel)', color=color_ourframe, edgecolor='black', linewidth=1)

# ==========================================
# 3. 细节美化与标注
# ==========================================
# 添加标题和轴标签
ax.set_ylabel('Percentage (%)', fontsize=13, fontweight='bold')
ax.set_title('Performance Comparison: Original vs. OurFrame (Workspace Suite)', fontsize=15, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(metrics, fontsize=12, fontweight='bold')
ax.set_ylim(0, 115) # 留出顶部空间显示数据标签

# 隐藏顶部和右侧的边框线 (学术图表惯用做法)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# 添加水平网格线，使对比更清晰
ax.yaxis.grid(True, linestyle='--', alpha=0.7)
ax.set_axisbelow(True)

# 图例设置
ax.legend(fontsize=12, loc='upper left')

# ==========================================
# 4. 自动添加数值标签的函数
# ==========================================
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

# ==========================================
# 5. 保存与展示
# ==========================================
plt.tight_layout()
plt.savefig('ourframe_comparison_results.png', dpi=300, bbox_inches='tight')
print("图表已成功生成并保存为 'ourframe_comparison_results.png'")
# plt.show() # 如果在 Jupyter Notebook 中运行可以取消注释import matplotlib.pyplot as plt
