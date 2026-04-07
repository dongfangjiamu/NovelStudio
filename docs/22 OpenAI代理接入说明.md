# 22 OpenAI代理接入说明

## 1. 当前结论

NovelStudio 当前不是直接写死调用 OpenAI 官方地址，而是通过 `OPENAI_BASE_URL` 把 `openai` Python SDK 指向一个 OpenAI 兼容代理，再由代理转发到上游模型服务。

当前线上配置位于仓库根目录的 `.env.compose`：

- `NOVEL_STUDIO_STUB_MODE=false`
- `NOVEL_STUDIO_MODEL=gpt-5.4`
- `OPENAI_BASE_URL=https://claude.tvc-mall.com/openai`
- `OPENAI_API_KEY=<已配置，文档不记录明文>`

这意味着当前线上运行时实际走的是：

1. 应用读取环境变量
2. 将 `OPENAI_BASE_URL` 写入运行时上下文
3. `openai.OpenAI(base_url=...)` 初始化客户端
4. 通过 `responses.stream()` 发起请求
5. 代理再把请求转发到上游模型

## 2. 代码链路

### 2.1 配置读取

文件：`novel_studio/novel_app/config.py`

- `load_config()` 从环境变量读取：
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `NOVEL_STUDIO_OPENAI_BASE_URL`
  - `NOVEL_STUDIO_MODEL`
- `validate_config()` 在非 stub 模式下要求必须有 `OPENAI_API_KEY`

### 2.2 运行时上下文传递

文件：`novel_studio/novel_app/services/workflow.py`

工作流执行时会构造 `RuntimeContext`，把下面两项传进去：

- `model_name=self._config.model_name`
- `openai_base_url=self._config.openai_base_url`

### 2.3 LLM 客户端初始化

文件：`novel_studio/novel_app/utils/llm.py`

关键逻辑：

- `_resolve_base_url(runtime_context)` 优先取 `runtime_context.openai_base_url`
- 若运行时没带，再回退到：
  - `OPENAI_BASE_URL`
  - `NOVEL_STUDIO_OPENAI_BASE_URL`
- `invoke_structured()` 中实际初始化：

```python
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=_resolve_base_url(runtime_context),
    timeout=_resolve_timeout_seconds(runtime_context),
    max_retries=1,
)
```

随后通过：

```python
client.responses.stream(...)
```

发起模型请求。

## 3. 这套接法的本质

本项目里的“代理接入”不是应用自己写 HTTP 转发层，而是直接利用 OpenAI 官方 SDK 提供的 `base_url` 能力，把 SDK 请求根地址改为代理地址。

所以代理只要满足 OpenAI 兼容接口即可接入，应用代码本身不需要再改调用协议。

## 4. 后续修改方式

如果后续要切换代理或改回官方地址，优先改环境变量，不要先改业务代码。

推荐修改点：

- 代理地址：修改 `.env.compose` 中的 `OPENAI_BASE_URL`
- 模型名：修改 `.env.compose` 中的 `NOVEL_STUDIO_MODEL`
- 密钥：修改 `.env.compose` 中的 `OPENAI_API_KEY`

修改后需要重启应用容器使配置生效。

## 5. 排查建议

如果模型调用异常，优先检查：

1. `NOVEL_STUDIO_STUB_MODE` 是否为 `false`
2. `OPENAI_API_KEY` 是否已配置
3. `OPENAI_BASE_URL` 是否可访问
4. 代理是否兼容 `responses` 接口
5. 当前配置的模型名是否被代理支持

当前项目使用的是 `responses.stream()`，因此如果代理只兼容旧式 chat/completions，而不兼容 Responses API，就会出现调用失败或流式事件不完整的问题。
