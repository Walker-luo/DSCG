
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

# ================= 1. 环境与字体设置 =================
# 加载您的本地中文字体
font_path = './font/SimHei.ttf'  
font_manager.fontManager.addfont(font_path)
zh_font_name = font_manager.FontProperties(fname=font_path).get_name()

# 设置全局字体列表：英文/数字优先使用 Times New Roman，中文回退使用 SimHei
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Times New Roman', zh_font_name] 
plt.rcParams['axes.unicode_minus'] = False  # 正常显示负号
# =====================================================

# ================= 2. 数据准备 (已重排顺序) =================
scenarios = ['Workspace', 'Travel', 'Banking', 'Slack']
models = ['Qwen3-Max', 'Repeat Prompt', 'Spotlighting', 'CaMeL', 'DSCG']

data_vanilla = [
    [44.76, 37.62, 4989381.0, 0], # Workspace
    [39.00, 42.00, 3794454.0, 0], # Travel
    [77.50, 86.25, 940133.0, 0],  # Banking
    [27.62, 93.33, 2340980.0, 0]  # Slack
]

data_repeat = [
    [58.57, 23.33, 4456513.0, 0], # Workspace
    [34.00, 34.00, 5416679.0, 0], # Travel
    [73.75, 75.00, 1063797.0, 0], # Banking
    [28.75, 93.33, 2427924.0, 0]  # Slack
]

data_spotlight = [
    [44.29, 36.19, 5042512.0, 0], # Workspace
    [45.00, 27.00, 3609994.0, 0], # Travel
    [78.75, 76.25, 854492.0, 0],  # Banking
    [35.24, 81.90, 1539853.0, 0]  # Slack
]

data_camel = [
    [60.48, 0.00, 12734600.0, 0], # Workspace
    [3.60, 0.00, 14082900, 0],    # Travel (存在异常的数据)
    [np.nan, np.nan, np.nan, 0],  # Banking
    [np.nan, np.nan, np.nan, 0]   # Slack
]

data_dscg = [
    [67.14, 0.00, 5110672.0, 2359542.0], # Workspace
    [49.00, 7.00, 3867297.0, 380101.0],  # Travel
    [50.00, 1.25, 1070844.0, 366361.0],  # Banking
    [10.48, 20.00, 2174970.0, 1476238.0] # Slack
]

all_data = [data_vanilla, data_repeat, data_spotlight, data_camel, data_dscg]

colors = ['#A9B8C6', '#D4B483', '#C18C81', '#7EB09B', '#C44E52']

# ================= 3. 核心绘图函数 =================
def draw_bar_chart(metric_idx, title, ylabel, filename, is_token=False):
    fig, ax = plt.subplots(figsize=(14, 6.5), dpi=300)
    x = np.arange(len(scenarios))
    width = 0.16  
    
    offsets = [-2*width, -width, 0, width, 2*width]
    
    rects_list = []
    for i, model_data in enumerate(all_data):
        if is_token:
            y_values = [(scene[2] + scene[3]) / 1_000_000 if not np.isnan(scene[2]) else np.nan for scene in model_data]
        else:
            y_values = [scene[metric_idx] for scene in model_data]
            
        rects = ax.bar(x + offsets[i], y_values, width, label=models[i], 
                       color=colors[i], edgecolor='black', linewidth=0.8, alpha=0.95)
        rects_list.append(rects)

    ax.set_ylabel(ylabel, fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=13, fontweight='bold')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)

    max_val = 0
    for rects in rects_list:
        for rect in rects:
            if not np.isnan(rect.get_height()) and rect.get_height() > max_val:
                max_val = rect.get_height()
                
    ax.set_title(title, fontsize=16, fontweight='bold', pad=40) 
    ax.legend(fontsize=11.5, loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=5, frameon=False)
    ax.set_ylim(0, max_val * 1.15)
    
    # 【核心修改区：添加异常星号标注】
    # 使用 enumerate 获取模型索引(i) 和 场景索引(j)
    for i, rects in enumerate(rects_list):
        for j, rect in enumerate(rects):
            height = rect.get_height()
            if np.isnan(height) or (height == 0.0 and is_token):
                continue  
            
            label_text = f'{height:.1f}M' if is_token else f'{height:.1f}%'
            if height == 0.0 and not is_token:
                label_text = '0.0%'
                
            # 当模型是 CaMeL (索引3) 且 场景是 Travel (索引1) 时，在数字后追加星号
            if i == 3 and j == 1:
                label_text += '*'
                
            # 微调星号标签的颜色和字体粗细以引起注意
            font_color = '#d32f2f' if '*' in label_text else 'black'
                
            ax.annotate(label_text,
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 4),  
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=10, 
                        fontweight='bold', color=font_color, rotation=0)

    # 【核心修改区：添加底部脚注】
    # 使用坐标定位在图表的左下方
    ax.text(0, -0.12, "* 注：CaMeL 框架在 Travel 场景中因通信死锁仅完成 11/20 评测任务，此为非全量测试异常数据。", 
            transform=ax.transAxes, fontsize=11, color='#666666', style='italic')

    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 图表已生成: {filename}")

# ================= 4. 执行生成 =================
draw_bar_chart(metric_idx=0, 
               title='不同防御框架在四大核心场景下的任务可用性 (TSR) 对比', 
               ylabel='任务可用性 TSR (%)', 
               filename='./img/TSR_comparison.png', 
               is_token=False)

draw_bar_chart(metric_idx=1, 
               title='不同防御框架在四大核心场景下的攻击成功率 (ASR) 对比', 
               ylabel='定向攻击成功率 ASR (%)', 
               filename='./img/ASR_comparison.png', 
               is_token=False)

draw_bar_chart(metric_idx=2, 
               title='不同防御框架的全局算力总开销对比 (Tokens)', 
               ylabel='Token 消耗总量 (Millions)', 
               filename='./img/Token_comparison.png', 
               is_token=True)