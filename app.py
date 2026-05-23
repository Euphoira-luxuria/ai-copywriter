import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# 加载配置文件
CONFIG_FILE = Path(__file__).parent / "config.json"
CONFIG = {}
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)

# 预设文案模板
TEMPLATES = {
    "redbook": {
        "name": "小红书种草文案",
        "styles": ["活泼种草", "真实测评", "干货分享", "vlog 风"],
        "prompt": """你是小红书资深博主，请根据以下要求生成一篇高质量的小红书种草文案：

【产品/主题】{topic}
【风格】{style}
【核心卖点】{keywords}

要求：
- 标题带 emoji，控制在 20 字以内，要有吸引力
- 正文分点清晰，每段不超过 3 行
- 加入真实使用感受，不要像硬广
- 结尾带 3-5 个相关标签
- 全文控制在 300-500 字""",
    },
    "wechat": {
        "name": "朋友圈营销文案",
        "styles": ["温情走心", "幽默风趣", "专业权威", "生活记录"],
        "prompt": """你是朋友圈文案高手，请生成一条高质量的朋友圈营销文案：

【产品/主题】{topic}
【风格】{style}
【核心卖点】{keywords}

要求：
- 像真人分享，不像广告
- 用短句，方便手机阅读
- 引发共鸣或好奇
- 配合适当的 emoji
- 控制在 150 字以内""",
    },
    "script": {
        "name": "短视频脚本",
        "styles": ["口播干货", "剧情带货", "悬念反转", "沉浸体验"],
        "prompt": """你是短视频编导，请生成一份短视频拍摄脚本：

【主题】{topic}
【风格】{style}
【关键元素】{keywords}

要求输出：
1. 视频标题（吸引点击）
2. 前 3 秒钩子（必须让观众停留）
3. 分镜脚本（至少 5 个镜头，每个镜头标注画面描述 + 旁白/台词 + 时长）
4. 结尾引导语（点赞/关注/购买）""",
    },
    "product": {
        "name": "电商详情页文案",
        "styles": ["简洁高级", "功能详尽", "情感营销", "性价比型"],
        "prompt": """你是电商文案策划，请为以下产品撰写详情页文案：

【产品】{topic}
【风格】{style}
【卖点】{keywords}

要求输出：
1. 产品主标题 + 副标题
2. 3 个核心卖点，每个配一句话说明
3. 产品参数清单（规格、材质、尺寸等，根据产品合理推测）
4. 使用场景描述（2-3 个）
5. 售后承诺文案""",
    },
    "resume": {
        "name": "简历优化",
        "styles": ["互联网大厂", "金融行业", "外企英文", "应届生通用"],
        "prompt": """你是资深 HR 和简历顾问，请优化以下简历内容：

【目标岗位】{topic}
【当前经历】{keywords}
【目标风格】{style}

要求：
- 用 STAR 法则重写经历描述
- 量化成果（补充合理的数字）
- 突出与目标岗位匹配的能力
- 删除无价值的描述
- 保持专业简洁""",
    },
    "gzh": {
        "name": "公众号推文",
        "styles": ["深度长文", "轻松随笔", "清单体", "故事叙事"],
        "prompt": """你是公众号资深编辑，请撰写一篇公众号推文：

【主题】{topic}
【风格】{style}
【核心观点】{keywords}

要求：
- 开头 100 字内抓住读者
- 结构清晰：引入 → 正文（2-3 个小标题）→ 总结升华
- 字数 800-1200 字
- 排版建议（用小标题位置标注）""",
    },
}

# 润色操作模板
POLISH_ACTIONS = {
    "expand": "请将以下文案扩展，增加更多细节和感染力，使内容更加丰富。保留原有的风格和语气。",
    "shorten": "请将以下文案精简，删除重复和啰嗦的内容，保留核心信息，使表达更加凝练有力。",
    "rewrite": "请用不同的表达方式重写以下文案，避免重复的句式和词汇，使表达更加新鲜有创意。",
    "urgent": '请为以下文案增加紧迫感和行动号召力，让读者产生「现在就要」的冲动。',
    "formal": '请将以下文案调整为正式商务风格，用语更加专业、得体。',
    "casual": '请将以下文案调整为轻松口语化风格，更像朋友之间的聊天分享。',
}


def get_client():
    """获取 OpenAI 兼容客户端，支持多种 API 提供商"""
    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or CONFIG.get("api_key")
    )
    base_url = (
        os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("DEEPSEEK_BASE_URL")
        or CONFIG.get("base_url")
    )

    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/templates")
def get_templates():
    """返回所有文案模板信息（不含 prompt）"""
    result = {}
    for key, t in TEMPLATES.items():
        result[key] = {"name": t["name"], "styles": t["styles"]}
    return jsonify(result)


@app.route("/api/generate", methods=["POST"])
def generate():
    """生成文案"""
    data = request.json
    template_key = data.get("template", "redbook")
    topic = data.get("topic", "").strip()
    style = data.get("style", "")
    keywords = data.get("keywords", "").strip()
    custom_requirement = data.get("custom", "").strip()

    if not topic and not keywords:
        return jsonify({"error": "请输入产品或主题"}), 400

    template = TEMPLATES.get(template_key, TEMPLATES["redbook"])
    prompt = template["prompt"].format(
        topic=topic or "未指定",
        style=style or template["styles"][0],
        keywords=keywords or "未指定",
    )

    if custom_requirement:
        prompt += f"\n\n额外要求：{custom_requirement}"

    try:
        client = get_client()
        response = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL") or CONFIG.get("model", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "你是一个经验丰富的专业文案撰写专家，认真完成每一次写作任务。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=2048,
        )
        result = response.choices[0].message.content
        return jsonify({"success": True, "content": result})
    except Exception as e:
        return jsonify({"error": f"生成失败：{str(e)}"}), 500


@app.route("/api/polish", methods=["POST"])
def polish():
    """润色已有文案"""
    data = request.json
    content = data.get("content", "").strip()
    action = data.get("action", "rewrite")

    if not content:
        return jsonify({"error": "请输入需要润色的文案"}), 400

    instruction = POLISH_ACTIONS.get(action, POLISH_ACTIONS["rewrite"])

    try:
        client = get_client()
        response = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL") or CONFIG.get("model", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "你是资深文案编辑，擅长润色和优化各种类型的文字内容。",
                },
                {
                    "role": "user",
                    "content": f"{instruction}\n\n原文如下：\n\n{content}",
                },
            ],
            temperature=0.7,
            max_tokens=2048,
        )
        result = response.choices[0].message.content
        return jsonify({"success": True, "content": result})
    except Exception as e:
        return jsonify({"error": f"润色失败：{str(e)}"}), 500


if __name__ == "__main__":
    print("AI Copywriter Tool")
    print("=" * 40)
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or CONFIG.get("api_key")
    if not api_key:
        print("[!] Please set API Key. Options:")
        print("    1) Create config.json with api_key field")
        print("    2) set DEEPSEEK_API_KEY=sk-xxx")
    else:
        print("[OK] API Key configured (source: {})".format(
            "config.json" if CONFIG.get("api_key") and not os.environ.get("DEEPSEEK_API_KEY") and not os.environ.get("OPENAI_API_KEY") else "env"
        ))
    print("=" * 40)
    print("Open http://localhost:5001 in your browser")
    app.run(debug=False, port=5001)
