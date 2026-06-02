

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
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Times New Roman']

plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'sans-serif'

# ================= 2. 数据准备 =================
models = ['Qwen3-Max', 'Repeat\nPrompt', 'Spotlighting', 'CaMeL', 'DSCG\n(本文框架)']

ws_eq_in = np.array([4.89, 4.36, 4.94, 12.00, 5.68])
ws_eq_out = np.array([0.10, 0.09, 0.10, 0.73, 0.21])
ws_cost = np.array([13.23, 11.80, 13.35, 37.30, 16.32])

tr_eq_in = np.array([3.71, 5.33, 3.54, 12.97, 3.88])
tr_eq_out = np.array([0.08, 0.09, 0.07, 1.11, 0.11])
tr_cost = np.array([10.08, 14.23, 9.55, 43.53, 10.84])

color_in = '#A9B8C6'   
color_out = '#C44E52'  
color_line = '#E6A11D' 

# ================= 3. 核心拆分绘图函数 =================
def plot_single_combo_chart(eq_in, eq_out, cost, title, filename, is_travel=False):
    # 建立独立大画布 (10, 8)，提供极为充裕的排版空间
    fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
    x = np.arange(len(models))
    width = 0.45  # 稍微收窄一点柱子，让画面呼吸感更强
    
    # 1. 绘制堆叠柱状图 (左侧数据)
    bar1 = ax.bar(x, eq_in, width, label='等效输入 Token (M)', color=color_in, edgecolor='black', linewidth=1)
    bar2 = ax.bar(x, eq_out, width, bottom=eq_in, label='等效输出 Token (M)', color=color_out, edgecolor='black', linewidth=1)
    
    # 坐标轴与刻度设置
    ax.set_ylabel('等效 Token 总量 (M)', fontsize=24, fontweight='bold', labelpad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=20, fontweight='bold')
    ax.tick_params(axis='y', labelsize=18)
    
    # 极大地拉高 Y 轴上限，防止柱子和上方的折线打架 (拉高到 1.8 倍)
    ax.set_ylim(0, max(eq_in + eq_out) * 1.8) 
    ax.spines['top'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    # 2. 绘制折线图 (右侧数据)
    ax_twin = ax.twinx()
    # zorder=5 确保折线和数据点绝对渲染在柱子上方
    line = ax_twin.plot(x, cost, color=color_line, marker='D', markersize=12, linewidth=4, 
                        markeredgecolor='black', markeredgewidth=1.5, label='实际换算成本 (RMB)', zorder=5)
    
    ax_twin.set_ylabel('单场景评测总成本 (RMB)', fontsize=24, fontweight='bold', color='#B8860B', labelpad=20)
    ax_twin.tick_params(axis='y', colors='#B8860B', labelsize=18)
    
    # 极大地拉高右侧 Y 轴上限，给数值标签留下充足天空 (拉高到 1.6 倍)
    ax_twin.set_ylim(0, max(cost) * 1.6) 
    ax_twin.spines['top'].set_visible(False)
    
    # 3. 添加数值标签 (保证在折线外，且带白色背景防遮挡)
    for i, txt in enumerate(cost):
        label = f'{txt:.2f}'
        if is_travel and i == 3: label += '*' 
        
        # xytext=(0, 22) 确保文字完全悬浮在数据点上方，绝不遮挡折线
        ax_twin.annotate(label, (x[i], cost[i]), textcoords="offset points", xytext=(0, 22),
                         ha='center', va='bottom', fontsize=18, fontweight='bold', color='#A67B00',
                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9), zorder=6)
                         
    # 4. 标题与图例
    ax.set_title(title, fontsize=28, fontweight='bold', pad=35)
    
    lines_1, labels_1 = ax.get_legend_handles_labels()
    lines_2, labels_2 = ax_twin.get_legend_handles_labels()
    # 将图例统一放置在左上角，进一步放大字体，避免占用右侧空间
    ax.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left', fontsize=18, framealpha=0.95, edgecolor='black')

    # 添加底部脚注 (仅在 Travel 场景添加)
    if is_travel:
        plt.figtext(0.5, -0.05, "* 注：CaMeL 框架在 Travel 场景中仅完成 11/20 评测任务，实际归一化成本更高。", 
                    ha="center", fontsize=18, color='#666666', style='italic')

    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 图表已生成: {filename}")

# ================= 4. 执行生成 =================
plot_single_combo_chart(ws_eq_in, ws_eq_out, ws_cost, 
                        'Workspace 场景等效开销与成本对比', 
                        './img/Cost_Analysis_Workspace.png', is_travel=False)

plot_single_combo_chart(tr_eq_in, tr_eq_out, tr_cost, 
                        'Travel 场景等效开销与成本对比', 
                        './img/Cost_Analysis_Travel.png', is_travel=True)