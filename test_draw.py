
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

# ================= 2. 数据准备 =================
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
    [3.60, 0.00, 14082900, 0],    # Travel 
    [np.nan, np.nan, np.nan, 0],  # Banking (空缺)
    [np.nan, np.nan, np.nan, 0]   # Slack (空缺)
]

data_dscg = [
    [67.14, 0.00, 5110672.0, 2359542.0], # Workspace
    [49.00, 7.00, 3867297.0, 380101.0],  # Travel
    [50.00, 1.25, 1070844.0, 366361.0],  # Banking
    [10.48, 20.00, 2174970.0, 1476238.0] # Slack
]

all_data = [data_vanilla, data_repeat, data_spotlight, data_camel, data_dscg]
colors = ['#A9B8C6', '#D4B483', '#C18C81', '#7EB09B', '#C44E52']

# ================= 3. 核心合并绘图函数 =================
def draw_combined_bar_chart(metric_idx, title, ylabel, filename, is_token=False):
    groups = [
        {'name': 'Part1', 'indices': [0, 1]},
        {'name': 'Part2', 'indices': [2, 3]}
    ]
    
    # 🚀 核心改变：1行2列变为2行1列的巨幅上下子图
    fig, axes = plt.subplots(2, 1, figsize=(12, 15), dpi=300)
    
    # 🚀 核心改变：设置唯一的全局超大主标题
    fig.suptitle(title, fontsize=32, fontweight='bold', y=0.96)
    
    for ax_idx, group in enumerate(groups):
        ax = axes[ax_idx]
        indices = group['indices']
        current_scenarios = [scenarios[i] for i in indices]
        
        # 动态剔除 Banking & Slack 中的 CaMeL
        if group['name'] == 'Part2':
            valid_idx = [0, 1, 2, 4]  # 剔除索引为 3 的 CaMeL
        else:
            valid_idx = [0, 1, 2, 3, 4] # 全量保留
            
        current_models = [models[i] for i in valid_idx]
        current_colors = [colors[i] for i in valid_idx]
        current_data = [all_data[i] for i in valid_idx]
        
        x = np.arange(len(current_scenarios))
        width = 0.16  
        
        # 动态计算偏移量，使剩下的柱子完美对称居中
        num_models = len(current_models)
        start_offset = - (num_models - 1) * width / 2
        offsets = [start_offset + i * width for i in range(num_models)]
        
        rects_list = []
        for i, c_data in enumerate(current_data):
            if is_token:
                y_values = [(c_data[idx][2] + c_data[idx][3]) / 1_000_000 if not np.isnan(c_data[idx][2]) else np.nan for idx in indices]
            else:
                y_values = [c_data[idx][metric_idx] for idx in indices]
                
            rects = ax.bar(x + offsets[i], y_values, width, label=current_models[i], 
                           color=current_colors[i], edgecolor='black', linewidth=0.8, alpha=0.95)
            rects_list.append(rects)

        ax.set_ylabel(ylabel, fontsize=24, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(current_scenarios, fontsize=26, fontweight='bold')
        ax.tick_params(axis='y', labelsize=18) 
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.4)
        ax.set_axisbelow(True)

        max_val = 0
        for rects in rects_list:
            for rect in rects:
                if not np.isnan(rect.get_height()) and rect.get_height() > max_val:
                    max_val = rect.get_height()
                    
        # 留出顶部空间给悬浮数字
        ax.set_ylim(0, max_val * 1.25) 
        
        # 标注数据
        for i, rects in enumerate(rects_list):
            for j, rect in enumerate(rects):
                height = rect.get_height()
                if np.isnan(height) or (height == 0.0 and is_token):
                    continue  
                
                label_text = f'{height:.1f}M' if is_token else f'{height:.1f}%'
                if height == 0.0 and not is_token:
                    label_text = '0.0%'
                    
                global_scenario_idx = indices[j]
                
                # 判断当前渲染的模型是否是 CaMeL 且处于 Travel 场景
                if current_models[i] == 'CaMeL' and global_scenario_idx == 1:
                    label_text += '*'
                    
                font_color = '#d32f2f' if '*' in label_text else 'black'
                    
                ax.annotate(label_text,
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 8),  
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=18, 
                            fontweight='bold', color=font_color, rotation=0)

    # 🚀 核心改变：提取全局图例（取上半图拥有5个模型的完整句柄）
    handles, plot_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, plot_labels, loc='upper center', bbox_to_anchor=(0.5, 0.92), 
               ncol=5, fontsize=18, frameon=False) 

    # 添加全局底部脚注
    fig.text(0.5, 0.03, "* 注：CaMeL 框架在 Travel 场景中仅完成 11/20 评测任务。", 
             ha='center', fontsize=18, color='#666666', style='italic')

    # 🚀 调整整体布局间距，给顶部标题/图例、子图之间、底部脚注留出完美空隙
    plt.subplots_adjust(top=0.86, bottom=0.08, hspace=0.3)
    
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 合并图表已生成: {filename}")


# ================= 4. 执行生成 =================
draw_combined_bar_chart(metric_idx=0, 
               title='不同防御框架任务可用性 (TSR) 对比', 
               ylabel='任务可用性 TSR (%)', 
               filename='./img/TSR_comparison_Combined.png', 
               is_token=False)

draw_combined_bar_chart(metric_idx=1, 
               title='不同防御框架攻击成功率 (ASR) 对比', 
               ylabel='定向攻击成功率 ASR (%)', 
               filename='./img/ASR_comparison_Combined.png', 
               is_token=False)

draw_combined_bar_chart(metric_idx=2, 
               title='不同防御框架算力总开销对比 (Tokens)', 
               ylabel='Token 消耗总量 (Millions)', 
               filename='./img/Token_comparison_Combined.png', 
               is_token=True)