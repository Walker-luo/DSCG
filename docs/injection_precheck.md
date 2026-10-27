# 注入目标筛选与冻结名单

Screen 直接请求每个注入 GOAL，给每个目标一次完整原生轨迹：成功保留，失败排除，错误/中断单列跳过。不进行同轮、同名续跑或历史证据中的第二次机会。GOAL 不是用户×注入的计分任务，不能进入 TSR/ASR 分母。

## 创建名单

从 BaseIntent 根目录激活目标环境，核对配置后执行；本命令会调用真实模型：

```bash
python -m experiments.run_injection_precheck screen --suites banking slack \
  --model-config config/models.local.toml --name screen_01 \
  --results-dir artifacts/20261027_screen
```

默认分类根为 `results/injection_precheck`，新路径为 `<results-dir>/<backend>/<model>_<name>/`，实际 `cohort.json` 路径由命令输出。只读历史复用可显式加 `--reuse-from PATH`，选择第一份兼容证据，不自动重试失败。来源、模型/provider、后端、任务及筛选证据按创建协议校验，不改写原文件。

<a id="2-中断和错误后续跑"></a>

## 中断和错误后续跑

保留同一 screen 命令和 name 再运行，仅开始未启动目标，已完成失败/错误不重试。旧证据和冻结名单保持原字节/语义。即使有错误仍可冻结 success-only 名单，错误保留且退出码为 1；不能把跳过或连接失败算作排除成功。

## 消费名单

Full 使用 `python -m experiments.run_benchmark --cohort PATH --name NEW_NAME`；partial 使用相同选项，但只过滤原注册前缀，不补位。完整命令见[评测指南](benchmark.md)。

消费时只验证主模型 ID/provider、实际后端、所选场景、任务 ID/顺序和名单自身摘要，读取/摘要化一次。不重读筛选轨迹/manifest、不比较 GOAL 或适配器、不重新认证筛选判断。screen 创建/恢复/证据复用仍保留自身严格检查。模型/后端不兼容应拒绝，不能通过改名单或迁移旧缓存绕过。
