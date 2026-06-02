import matplotlib.pyplot as plt
import numpy as np

# 设置整体字体和绘图风格
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Times New Roman', 'SimHei'] 
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.alpha'] = 0.6

# ================= 数据准备 =================
labels = ['DSCG (Ours)', 'w/o SandBox', 'w/o SecurityChecker']
tsr_scores = [67.14, 68.10, 67.14]    
asr_scores = [0.00, 0.48, 5.24]       
tokens_in = [5687.2, 6081.6, 5179.7]  
tokens_out = [208.9, 179.1, 106.5]    

# 统一定义点样式
colors = ['#E74C3C', '#3498DB', '#F39C12'] 
markers = ['*', 'o', 'o']
sizes = [1500, 700, 700] # 🚀 散点再次极限放大

# ================= 创建画布 =================
# 🚀 核心改变：2行1列，上下排版，纵向画幅加大到 (11, 14)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 14), dpi=300) 

# 🚀 核心改变：设置全局唯一的超大主标题
fig.suptitle('Ablation Study: Security, Utility, and Computational Overhead', 
             fontsize=26, fontweight='bold', y=0.94)

# ----------------- 上图: TSR vs ASR 散点图 -----------------
for i in range(3):
    ax1.scatter(tsr_scores[i], asr_scores[i], s=sizes[i], marker=markers[i], 
                c=colors[i], edgecolors='black', label=labels[i], zorder=5)

ax1.annotate('', xy=(tsr_scores[1], asr_scores[1]), xytext=(tsr_scores[0], asr_scores[0]),
             arrowprops=dict(arrowstyle="->", color="gray", lw=3, ls='--'))
ax1.annotate('', xy=(tsr_scores[2], asr_scores[2]), xytext=(tsr_scores[0], asr_scores[0]),
             arrowprops=dict(arrowstyle="->", color="gray", lw=3, ls='--'))

# 🚀 轴标签和刻度数字全面放大
ax1.set_xlabel('Utility (TSR %)', fontsize=22, fontweight='bold')
ax1.set_ylabel('Attack Success Rate (ASR %)', fontsize=22, fontweight='bold')
ax1.tick_params(axis='both', which='major', labelsize=18) 

# 上图文本标签
for i in range(3):
    offset_y = 0.6 if i != 0 else -0.5 
    va_align = 'bottom' if i != 0 else 'top'
    # 🚀 将详细的数据拼接在名称下方，字号放大至 16
    label_text = f'{labels[i]}\n(TSR: {tsr_scores[i]}%, ASR: {asr_scores[i]}%)'
    
    # 🚀 增加白底 bbox 防止与网格线交叉影响阅读
    ax1.text(tsr_scores[i], asr_scores[i] + offset_y, label_text, 
             ha='center', va=va_align, fontsize=16, fontweight='bold', zorder=6,
             bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.85))

# 稍微拉宽 Y 轴以容纳放大的文本
ax1.set_xlim(66.7, 68.5)
ax1.set_ylim(-1.5, 7.5)


# ----------------- 下图: Token 开销二维散点图 -----------------
for i in range(3):
    ax2.scatter(tokens_in[i], tokens_out[i], s=sizes[i], marker=markers[i], 
                c=colors[i], edgecolors='black', label=labels[i], zorder=5)

ax2.annotate('', xy=(tokens_in[1], tokens_out[1]), xytext=(tokens_in[0], tokens_out[0]),
             arrowprops=dict(arrowstyle="->", color="gray", lw=3, ls='--'))
ax2.annotate('', xy=(tokens_in[2], tokens_out[2]), xytext=(tokens_in[0], tokens_out[0]),
             arrowprops=dict(arrowstyle="->", color="gray", lw=3, ls='--'))

# 🚀 轴标签和刻度数字全面放大
ax2.set_xlabel('Equivalent Input Tokens (K)', fontsize=22, fontweight='bold')
ax2.set_ylabel('Equivalent Output Tokens (K)', fontsize=22, fontweight='bold')
ax2.tick_params(axis='both', which='major', labelsize=18)

# 下图文本标签
for i in range(3):
    offset_y = 10 if i != 2 else -14 
    va_align = 'bottom' if i != 2 else 'top'
    # 🚀 拼接输入输出的具体 Token 数值
    label_text = f'{labels[i]}\n(In: {tokens_in[i]}, Out: {tokens_out[i]})'
    
    ax2.text(tokens_in[i], tokens_out[i] + offset_y, label_text, 
             ha='center', va=va_align, fontsize=16, fontweight='bold', zorder=6,
             bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.85))

ax2.set_xlim(4900, 6400)
ax2.set_ylim(80, 260)


# ================= 全局图例与布局调整 =================
handles, plot_labels = ax1.get_legend_handles_labels()
# 🚀 图例字号放大至 20，并精准控制其位于两图的正下方
fig.legend(handles, plot_labels, loc='lower center', bbox_to_anchor=(0.5, 0.02), 
           ncol=3, fontsize=20, frameon=True, shadow=True, borderpad=1.0)

# 🚀 调整子图间距：为中间留出呼吸空间 (hspace=0.25)，为底部图例留出空间 (bottom=0.12)
plt.subplots_adjust(hspace=0.25, bottom=0.12, top=0.88) 

plt.savefig('ablation_vertical_large.png', dpi=300, bbox_inches='tight')
plt.show()
print("✅ 上下双子图大字版生成完毕！")