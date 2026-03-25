from __future__ import annotations

import json
import os

from novel_app.graph_main import graph


def main() -> None:
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
    context = {
        "project_id": os.getenv("NOVEL_STUDIO_PROJECT_ID", "demo-book"),
        "operator_id": os.getenv("NOVEL_STUDIO_OPERATOR_ID", "local-dev"),
        "model_name": os.getenv("NOVEL_STUDIO_MODEL", "gpt-5-nano"),
    }
    result = graph.invoke(sample_input, context=context)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
