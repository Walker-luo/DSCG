# 有限真实诊断采集器（2026-10-21）

工程已完成；真实模型诊断待明确授权。用户要求按上一阶段交付继续，拟执行audit最多96次、authorization最多48次，不执行工具、source或37项clean。本地默认已为DeepSeek，本轮按历史Qwen实验公开配置显式选用qwen3.7-flash/DashScope，不改本地默认配置。

## 采集行为

新入口 `python -m experiments.diagnostics.utility_collect` 必须显式提供`--execute`、固定阶段次数上限、参考manifest和全新artifact目录。复用公共provider适配器；模型和reasoning设置来自真实公开配置，SDK重试为0。按case/重复交替两个版本顺序，串行发送一次请求；无工具循环、自动补权、参数修复、回退模型或默认候选晋升。

每次调用前先记录started并fsync，responses.json原子保存；保留模板hash、实际调用参数hash、响应content、结束原因/拒答标记、已知usage、延迟。错误只保留受限API诊断，不保存凭据或SDK异常文本。首次接口错误/中断即停止；超时/中断仍占尝试预算，禁止盲目重跑。协议失败原样保留并继续固定样例。空choices在本地回放保持NO_CHOICES，不误归为空文本。比较说明已区分“离线重放不调用模型”和“导入响应可能来自付费请求”。

## 审批状态

首次96次请求命令被自动审批在进程创建前拒绝。理由：“继续执行”未明确授权具体模型、端点、次数和发送内容，并涉及外部传输和费用。没有改用其他传输、间接执行或其他目录绕过；实际API请求0，audit_run未创建。

已通过异步问题请求用户明确授权：qwen3.7-flash、历史DashScope端点、人工合成banking/Slack任务/事实/攻击片段，最多96+48次；可选仅96次或暂不调用。批准前不发送请求。此拒绝不是模型接口失败，也不是候选效果结果。

## 验证与保护

基点99d2117647d0e3b0ed8b5ad038891df7eb790013，workshop分支；起始已有utility_stages阶段未提交改动，本次保留并在其上添加collector，未提交。新证据 `workshop/artifacts/20261021_utility_live/`。

| 命令（DSCG根目录） | 退出码 | 结果 |
| --- | --- | --- |
| `conda run -n ipi python -B workshop/artifacts/20261021_utility_live/run_offline_tests.py --pattern test_utility_collect.py` | 1→0 | 缺模块RED；最终5/5，含空choices分类RED→GREEN；green_final.log |
| `conda run -n ipi python -B workshop/artifacts/20261021_utility_live/run_offline_tests.py` | 0 | 616项：607通过、9跳过；ipi.log |
| `conda run -n ipi-agentdyn python -B workshop/artifacts/20261021_utility_live/run_offline_tests.py` | 0 | 620项：619通过、1跳过；agentdyn.log |
| `python -B workshop/artifacts/20261021_utility_live/verify_delivery.py` | 0 | 原始结果/导出保护及未创建真实调用目录；validation.json |
| `git diff --check` | 0 | 无空白错误 |

全部模型相关离线测试有socket连接硬隔离，network_attempts=0。覆盖次数上限/非法预算/旧目录启动前拒绝、SDK重试关闭、模板不变、真实模型和reasoning参数透传、首次API错误停止、响应/attempt记录、敏感异常不落盘、非法输出不重试及NO_CHOICES保真。独立只读复核无Important/Critical剩余问题；真实服务兼容性尚未验证。

## 下一步

取得上述明确授权后执行一次新目录采集，先audit96，完整有效完成后再进行已授权的authorization48；出现接口错误停下报告，不自动加预算。根据真实比较结果决定是否有候选可进入37项clean。source96、37/97项clean及攻击对照不自动启动。

本轮真实模型调用0、工具执行0、效用/安全样本0；没有TSR、ASR、Token收益或候选优越性结论。原默认防御、原始任务/评分及研究闸门不变。E0 pending、I3 partial24valid/8scope、I2 locked。用法见[当前指南](../../docs/qwen_utility.md#真实响应采集须明确授权预算模型与发送内容)。
