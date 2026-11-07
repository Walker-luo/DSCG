# AgentDyn／Qwen Chat消息角色兼容修复（2026-10-19）

用户批准的公共客户端适配、受限API诊断及离线验证已完成。没有修改conda包、用户模型凭据或原失败结果；没有真实模型请求、远端恢复或效用/安全收益结论。恢复测试使用新run名。

## 定位与修复

原目录`results/partial_benchmark/agentdyn/qwen3.7-flash_test`含9个攻击/场景组合，均在首个GOAL预检的首个generation请求失败。L2授权成功、L3零调用，没有81条有效计分轨迹。旧记录只保存BadRequestError类型，未保留400正文，不能完全排除其他服务端错误。

本机同消息离线捕获：AgentDojo适配器发送system/user，AgentDyn对qwen3.7-flash发送developer/user（只有精确qwen3-max例外）。与[百炼Chat系统消息要求](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions/)和失败位置相符；MockTransport可复现原请求被拒绝、适配后通过。模拟服务只证明序列化兼容契约，不证明真实API恢复。

- 公共create_openai_client对实际provider=dashscope启用dashscope-system-v1，将developer→system；保留正文/顺序/其他角色、工具schema及请求参数，不原地修改历史对象。不硬编码模型名称、不增加fallback/重试；其他provider返回原客户端。
- baseline、DSCG、GOAL预检、独立screen和Dashboard共用此入口。同步chat.completions.create是本轮验证路径，不替换上游原生工具循环和评分。
- chat_request_adapter加入DashScope公开主/审计模型设置，进入既有manifest/cohort/router身份；旧缺失/不兼容配置不能静默续跑或复用校准。旧记录/名单不修改；新预检或新的匹配cohort另行准备。
- 新api_error字段仅保存schema、http_status、受限code/param和实际发送角色计数，不保存请求/响应message、凭据或SDK异常正文。phase保存last_api_error；CLI执行/manifests/失败JSONL、screen的attempt及Dashboard SSE/log接线。Dashboard终态先发送，再尽力保存execution_error.json，写盘失败不能掩盖原API错误。

默认模型、提示候选、三层策略、shadow模式、阈值、权限与重试参数均保持。客户端请求适配改变身份，不降低安全边界；预检成本和有效错误分母沿用原语义。

## 验证与证据

基点45b4acd（完整revision见manifest）；开始工作树干净，交付为未提交改动，无自动commit。新证据在`workshop/artifacts/20261019_agentdyn_qwen_roles/`。任务前SHA256清单保护原目录27文件及两套conda原生适配器，共29文件；结束逐文件核对0变化。

| 命令（DSCG目录执行） | 退出码 | 结果/日志 |
| --- | --- | --- |
| conda run -n ipi-agentdyn python -B -m unittest discover -s tests -p test_request_compatibility.py -v | 1→0 | 最终13/13；red、wiring_red/green、review_red/green等日志 |
| conda run -n ipi python -B -m unittest discover -s tests -v | 0 | 557项：556通过/1后端跳过；ipi_final.log |
| conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v | 0 | 561项：560通过/1后端跳过；agentdyn_final.log |
| /Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs | 0 | 45/45；node_final.log |
| python -B workshop/artifacts/20261019_agentdyn_qwen_roles/verify_delivery.py | 0 | 原始字节、最终文件hash和新文档链接；validation.json |
| git diff --check | 0 | 无空白错误 |

Shell PATH中node缺失（初次退出127，node_path_missing.log保留），使用桌面内置Node v24.19.0完成检查，不安装/更改依赖。Python均现有3.10环境。初始目录fixture错误使用了不存在的register_functions辅助API，修正为真实FunctionsRuntime构造后，两环境的当前目录请求测试通过；原始失败日志保留，不把它当作服务行为证据。

13项新测试涵盖源消息不变、其他provider不变、版本身份/旧缓存拒绝与路由hash变化、真实四/三场景工具目录首轮和工具返回后续请求、baseline/DSCG/审计客户端共享适配、400单次失败无fallback、受限诊断/费用、CLI组失败与完整索引、screen尝试、Dashboard隐私及写盘错误终态。真实工具状态/原生评分和防御边界由现有完整回归继续覆盖。

独立复核发现P2：写错误文件失败可跳过网页终态。新增RED→GREEN回归修正，独立重查AgentDyn13/13，无剩余Important问题。最后完整两环境回归在修正后重跑。

## 恢复与限制

[服务器恢复命令](../../docs/model_tool_configuration.md#dashscope消息角色兼容与400排错)：先在ipi-agentdyn用新名运行baseline/DSCG partial clean（各9项），确认请求级400消失，再恢复typical攻击。不要覆盖原test目录；部署后重启Dashboard。

本轮真实模型调用0、真实rollout0、新效用/安全样本0；MockTransport没有套接字请求。实际服务是否接受全部工具schema、JSON模式及后续上下文仍需服务器复测；不能把模拟通过称为TSR恢复。新字段可能使旧cohort/路由artifact不兼容，应按新身份重新准备，不手工补字段。E0 pending、I3 partial24valid/8scope、I2 locked保持。

下一步：执行两个新名partial clean，若仍400，依据受限状态/code/param/角色统计定位具体协议字段，保留错误分母。
