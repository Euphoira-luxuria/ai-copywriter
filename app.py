import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

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

# 场景预设约束（S 级 prompt，积累的优质模板）
SCENE_PRESETS = {
    "beauty": {
        "name": "美妆护肤品测评",
        "icon": "💄",
        "best_for": ["redbook", "script"],
        "constraints": """【场景专属要求】
- 开头说明自己的肤质/发质/肤色，建立可信度
- 写清楚使用前 vs 使用后的具体变化（出油减少xxx、肤色提亮xxx）
- 至少提一个竞品对比（"比 xxx 好用因为..."）
- 标注使用时长（"用了 48 小时/一周后..."）
- 缺点也写 1-2 条（增加真实感）
- 配图建议：用序号标注文中哪个位置该放什么图""",
    },
    "digital": {
        "name": "数码产品开箱",
        "icon": "📱",
        "best_for": ["redbook", "product"],
        "constraints": """【场景专属要求】
- 开头一句话总结：这东西适合谁、不适合谁
- 核心参数用简洁的对比方式呈现（不要罗列）
- 必须写一个"和 xxx 比怎么样"的段落
- 给出购买建议：什么情况下值得买、什么情况下劝退
- 使用场景要具体（"在地铁上单手操作没问题" > "便携"）
- 结尾一句话总结推荐指数（★ 评分更直观）""",
    },
    "food": {
        "name": "探店美食推荐",
        "icon": "🍜",
        "best_for": ["redbook", "wechat"],
        "constraints": """【场景专属要求】
- 开头写清楚：店名、地址（大概位置）、人均消费
- 必点菜写 TOP 3，每道用一句话描述味道
- 环境描写：装修风格、适合几人聚餐、要不要排队
- 写一个"避雷"提示（什么菜不要点/什么时间去人少）
- 语气像安利给最好的朋友，不要像大众点评官方
- 结尾一句话：什么人适合来（约会/聚会/一人食）""",
    },
    "course": {
        "name": "课程/知识付费推荐",
        "icon": "📚",
        "best_for": ["redbook", "wechat", "gzh"],
        "constraints": """【场景专属要求】
- 开头点明：适合什么阶段的人（入门/进阶/转行）
- 写清楚 3 个具体收获："学完后你能xxx"
- 对比自学 vs 上课的区别（击中学费痛点）
- 用个人经历做佐证（"我学之前xxx，学之后xxx"）
- 附一个学习建议：怎么学效果最好
- 结尾引导：想了解更多的评论区问""",
    },
    "fashion": {
        "name": "穿搭/好物分享",
        "icon": "👗",
        "best_for": ["redbook", "wechat"],
        "constraints": """【场景专属要求】
- 标注身高体重/尺码参考，方便读者对照
- 每件单品写：品牌/价格/购买渠道
- 写搭配思路（为什么选这件+怎么搭），不要只放图
- 至少写一个"平替"方案（便宜替代贵价款）
- 适用场景说明（上班/约会/逛街分别怎么配）
- 语气轻松，像闺蜜聊天分享""",
    },
    "travel": {
        "name": "旅游攻略/民宿推荐",
        "icon": "✈️",
        "best_for": ["redbook", "gzh"],
        "constraints": """【场景专属要求】
- 开头写：适合几月去、玩几天、人均预算
- 行程安排用时间线呈现（Day1: xxx → Day2: xxx）
- 每个景点写真实感受，不要复制百科介绍
- 交通攻略：怎么去、要不要包车、滴滴方便吗
- 必吃清单 3-5 个，避开网红店坑
- 写一个"如果重来一次我会xxx"的后悔清单""",
    },
    "home": {
        "name": "家居装修/收纳",
        "icon": "🏠",
        "best_for": ["redbook", "product"],
        "constraints": """【场景专属要求】
- 标注房间面积/户型，方便读者参考
- 每件家居品写：价格、尺寸、使用时长后的真实状态
- 写收纳/布置的"前后对比"，突出改造点
- 给不同预算的方案（贵的方案 vs 省钱方案）
- 避坑指南：装修/购买过程中踩过的坑
- 配图建议标注：哪个角落适合拍照""",
    },
}

# API：返回所有场景预设
@app.route("/api/scenes")
def get_scenes():
    result = {}
    for key, s in SCENE_PRESETS.items():
        result[key] = {
            "name": s["name"],
            "icon": s["icon"],
            "best_for": s["best_for"],
            "constraints": s["constraints"],
        }
    return jsonify(result)


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
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("DEEPSEEK_BASE_URL")
    if not api_key:
        raise RuntimeError("未配置 API Key，请设置环境变量 DEEPSEEK_API_KEY")
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
            model=os.environ.get("LLM_MODEL", "deepseek-chat"),
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
            model=os.environ.get("LLM_MODEL", "deepseek-chat"),
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
    if os.environ.get("VERCEL"):
        pass
    else:
        print("AI Copywriter Tool")
        print("=" * 40)
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            print("[!] 未配置 API Key，请设置环境变量 DEEPSEEK_API_KEY")
        else:
            print("[OK] API Key 已配置")
        print("=" * 40)
        print("Open http://localhost:5001 in your browser")
        app.run(debug=False, port=5001)
