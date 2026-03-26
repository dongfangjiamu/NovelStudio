from __future__ import annotations

import json

from novel_app.config import load_config
from novel_app.graph_main import graph


def main() -> None:
    config = load_config()
    sample_input = {
        "user_brief": {
            "title": "长夜炉火",
            "genre": "东方玄幻",
            "platform": "起点中文网",
            "hook": "一个被逐出山门的外门弟子，靠偷听禁地炉火中的古老对话逆天改命。",
            "must_have": ["稳步升级", "师门阴谋", "章末钩子强"],
            "must_not_have": ["后宫泛滥", "无代价外挂"]
        },
        "target_chapters": 2,
    }
    context = config.to_runtime_context()
    result = graph.invoke(sample_input, context=context)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
