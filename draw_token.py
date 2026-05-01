import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

# ================= 1. 环境与字体设置 =================
font_path = './font/SimHei.ttf'  # 替换为您的字体路径
try:
    font_manager.fontManager.addfont(font_path)
    zh_font_name = font_manager.FontProperties(fname=font_path).get_name()
    plt.rcParams['font.sans-serif'] = ['Times New Roman', zh_font_name] 
except:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Times New Roman'] # 备用字体

plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'sans-serif'

# ================= 2. 数据准备 =================
models = ['Qwen3-Max', 'Repeat\nPrompt', 'Spotlighting', 'CaMeL', 'DSCG\n(本文框架)']

# Workspace 场景数据
ws_eq_in = np.array([4.89, 4.36, 4.94, 12.00, 5.68])
ws_eq_out = np.array([0.10, 0.09, 0.10, 0.73, 0.21])
ws_cost = np.array([13.23, 11.80, 13.35, 37.30, 16.32])

# Travel 场景数据 (包含 CaMeL 的异常数据)
tr_eq_in = np.array([3.71, 5.33, 3.54, 12.97, 3.88])
tr_eq_out = np.array([0.08, 0.09, 0.07, 1.11, 0.11])
tr_cost = np.array([10.08, 14.23, 9.55, 43.53, 10.84])

# 配色方案
color_in = '#A9B8C6'   # 浅灰蓝 (代表便宜的输入 Token)
color_out = '#C44E52'  # 砖红色 (代表昂贵的输出 Token)
color_line = '#E6A11D' # 明黄色 (代表金钱成本)

# ================= 3. 核心绘图函数 =================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), dpi=300)
x = np.arange(len(models))
width = 0.55

def plot_combo_chart(ax, eq_in, eq_out, cost, title, is_travel=False):
    # 1. 绘制堆叠柱状图 (左轴)
    bar1 = ax.bar(x, eq_in, width, label='等效输入 Token (M)', color=color_in, edgecolor='black', linewidth=0.8)
    bar2 = ax.bar(x, eq_out, width, bottom=eq_in, label='等效输出 Token (M)', color=color_out, edgecolor='black', linewidth=0.8)
    
    ax.set_ylabel('等效 Token 总量 (M)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=11, fontweight='bold')
    ax.set_ylim(0, max(eq_in + eq_out) * 1.3) # 给左侧柱子留出空间
    
    # 隐藏上方边框
    ax.spines['top'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    # 2. 绘制折线图 (右轴)
    ax_twin = ax.twinx()
    line = ax_twin.plot(x, cost, color=color_line, marker='D', markersize=8, linewidth=2.5, 
                        markeredgecolor='black', markeredgewidth=1, label='实际换算成本 (RMB)')
    
    ax_twin.set_ylabel('单场景评测总成本 (RMB)', fontsize=12, fontweight='bold', color='#B8860B')
    ax_twin.tick_params(axis='y', colors='#B8860B')
    
    # 【修改点】：将右侧 Y 轴上限拉高到 1.45 倍，防止文字顶到天花板
    ax_twin.set_ylim(0, max(cost) * 1.45) 
    ax_twin.spines['top'].set_visible(False)
    
    # 3. 添加数值标签 (仅在折线节点上方显示)
    for i, txt in enumerate(cost):
        # 【修改点】：去掉了 ¥ 符号，只保留数字
        label = f'{txt:.2f}'
        if is_travel and i == 3: label += '*' # 给 CaMeL 的 Travel 场景打星号
        
        # 【修改点】：添加 bbox 参数，给文字加上白色半透明遮罩，完美解决重叠问题
        ax_twin.annotate(label, (x[i], cost[i]), textcoords="offset points", xytext=(0, 12),
                         ha='center', va='bottom', fontsize=11, fontweight='bold', color='#A67B00',
                         bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
                         
    ax.set_title(title, fontsize=15, fontweight='bold', pad=15)
    
    # 4. 合并图例
    lines_1, labels_1 = ax.get_legend_handles_labels()
    lines_2, labels_2 = ax_twin.get_legend_handles_labels()
    # 仅在左侧图表显示图例，避免重复
    if not is_travel:
        # 将图例背景设置为白色半透明，防止遮挡背后的网格和柱子
        ax.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left', fontsize=10, framealpha=0.9)

# 绘制两个子图
plot_combo_chart(ax1, ws_eq_in, ws_eq_out, ws_cost, 'Workspace 场景等效开销与成本对比')
plot_combo_chart(ax2, tr_eq_in, tr_eq_out, tr_cost, 'Travel 场景等效开销与成本对比', is_travel=True)

# 添加全局脚注
plt.figtext(0.5, -0.05, "* 注：CaMeL 框架在 Travel 场景中因通信死锁仅完成 11/20 评测任务，其实际归一化单任务成本更高。", 
            ha="center", fontsize=11, color='#666666', style='italic')

plt.tight_layout()
plt.savefig('./img/Cost_Analysis_Combo.png', dpi=300, bbox_inches='tight')
plt.close()
print("✅ 经济成本双轴图已生成: ./img/Cost_Analysis_Combo.png")