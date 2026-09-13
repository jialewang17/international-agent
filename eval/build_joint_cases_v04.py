"""用户上传论据 × 5W/受众/权威 联测用例生成。"""

from __future__ import annotations

import csv
from pathlib import Path

P = Path(__file__).resolve().parent / "skill_eval_cases_v0.4_joint.csv"

ROWS = [
    {
        "测试ID": "J01",
        "提示词形态": "短令+用户资料",
        "用户输入Prompt（完整）": "张铁机车 IG 美国 90词",
        "解析theme": "张铁机车海外社媒短帖——车间烟火气与匠人日常",
        "country": "America",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "90",
        "用户资料（粘贴）": (
            "项目简介：张铁机车是一家专注定制机车改装的中国工坊。车间保留手工焊接与打磨工序，"
            "海外访客常拍摄火花飞溅的夜间加班场景。\n\n"
            "通稿要点：2024年接待了来自欧洲与北美的体验团；强调安全培训后再允许近距离拍摄。"
        ),
        "用户要求（本条预期）": "短令+资料；evidence含用户上传；5W/受众达标；正文用焊接/体验团等用户事实",
        "评分重点": "双源+5W+受众",
    },
    {
        "测试ID": "J02",
        "提示词形态": "长Brief+用户资料",
        "用户输入Prompt（完整）": (
            "请按拉斯韦尔5W先策划再写Instagram英文帖（约90词）。受众美国。"
            "故事点：中国定制机车工坊的匠人日常。必须使用我粘贴的资料事实；"
            "To Whom写清美国机车/手工爱好者为何会停；evidence_notes标Evidence#；"
            "区分用户上传与本地库权威。"
        ),
        "解析theme": "张铁机车海外社媒短帖——车间烟火气与匠人日常",
        "country": "America",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "90",
        "用户资料（粘贴）": (
            "项目简介：张铁机车是一家专注定制机车改装的中国工坊。车间保留手工焊接与打磨工序。"
            "\n\n2024年接待欧美体验团；拍摄前必须完成安全培训。"
        ),
        "用户要求（本条预期）": "长提示+资料；质量维与短令同分位；用户事实进正文",
        "评分重点": "长短+双源稳定",
    },
    {
        "测试ID": "J03",
        "提示词形态": "短令+春节市集资料",
        "用户输入Prompt（完整）": "春节 英国 Twitter 80",
        "解析theme": "春节非遗短帖，突出家庭团圆与社区市集",
        "country": "UK",
        "platform": "twitter",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "80",
        "用户资料（粘贴）": (
            "活动纪要：伦敦华侨社区春节市集提供饺子体验台；志愿者讲解春联含义。"
            "\n\n补充：市集设有非遗剪纸体验角，儿童可带走一张红色窗花。"
        ),
        "用户要求（本条预期）": "用户市集事实+本地UNESCO可并存；英国桥梁；不嘲讽圣诞",
        "评分重点": "双源权威+受众",
    },
    {
        "测试ID": "J04",
        "提示词形态": "长作业体+资料",
        "用户输入Prompt（完整）": (
            "Assignment: UK Twitter ~80w on Spring Festival community fair moments. "
            "Full 5W. Use pasted notes. If UNESCO evidence exists, cite in notes. No Christmas mockery."
        ),
        "解析theme": "春节非遗短帖，突出家庭团圆与社区市集",
        "country": "UK",
        "platform": "twitter",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "80",
        "用户资料（粘贴）": (
            "伦敦华侨社区春节市集：饺子体验台、春联讲解、剪纸体验角。"
        ),
        "用户要求（本条预期）": "英文长提示+资料；5W与权威映射",
        "评分重点": "质量+双源",
    },
    {
        "测试ID": "J05",
        "提示词形态": "仅用户资料成稿",
        "用户输入Prompt（完整）": "茶山采青日记 IG 日本 85",
        "解析theme": "某县域茶山采青日记式短帖",
        "country": "Japan",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "85",
        "用户资料（粘贴）": (
            "采访摘录：茶农老周说清晨四点上山采一芽一叶；鲜叶当日进杀青锅。"
            "\n\n产地说明：茶园位于海拔约800米的向阳坡，游客可步行参观初制车间。"
        ),
        "用户要求（本条预期）": "主要靠用户资料；日本受众桥梁；不编产量冠军",
        "评分重点": "仅用户+受众+5W",
    },
    {
        "测试ID": "J06",
        "提示词形态": "探店资料+短令",
        "用户输入Prompt（完整）": "大盘鸡 美国IG",
        "解析theme": "新疆大盘鸡市井烟火短帖",
        "country": "America",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "80",
        "用户资料（粘贴）": (
            "探店笔记：乌鲁木齐某巷口大盘鸡配皮带面，香味先到；邻桌游客用手机拍拉面甩面。"
        ),
        "用户要求（本条预期）": "用户探店细节进Says What；可叠加本地food库",
        "评分重点": "双源美食",
    },
    {
        "测试ID": "J07",
        "提示词形态": "茶活动+英国长提示",
        "用户输入Prompt（完整）": (
            "为英国读者写Twitter茶故事帖约70词。5W完整。优先用我提供的咖啡馆盖碗茶活动事实；"
            "本地库UNESCO茶条目可作权威背书；evidence_notes映射。"
        ),
        "解析theme": "中国茶文化社交分享短帖",
        "country": "UK",
        "platform": "twitter",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "70",
        "用户资料（粘贴）": "咖啡馆活动：周末办盖碗茶体验，讲解「观色闻香」三步。",
        "用户要求（本条预期）": "用户活动+权威茶库；英国桥梁",
        "评分重点": "双源权威",
    },
    {
        "测试ID": "J08",
        "提示词形态": "崇礼体验笔记",
        "用户输入Prompt（完整）": "崇礼夜滑 美国IG 80",
        "解析theme": "崇礼冬奥场馆大众滑雪体验帖",
        "country": "America",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "80",
        "用户资料（粘贴）": (
            "体验笔记：周末在崇礼某雪场夜滑，教练强调分层雪道；缆车仍使用冬奥遗产设施标识。"
        ),
        "用户要求（本条预期）": "用户体验+可能的本地冬奥条；source_type可分",
        "评分重点": "双源可见性+5W",
    },
    {
        "测试ID": "J09",
        "提示词形态": "分段资料+剪纸",
        "用户输入Prompt（完整）": "剪纸工作坊 英国IG",
        "解析theme": "剪纸非遗工作坊招募帖文",
        "country": "UK",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "75",
        "用户资料（粘贴）": (
            "工作坊通告：周六下午剪纸体验课，提供红纸与刻刀入门套装。\n---\n"
            "导师介绍：省级非遗传承人助理授课；先学窗花对称折叠。"
        ),
        "用户要求（本条预期）": "≥2条用户论据；英国受众；5W非空壳",
        "评分重点": "规范化+质量",
    },
    {
        "测试ID": "J10",
        "提示词形态": "校园中国角列表资料",
        "用户输入Prompt（完整）": (
            "写美国校园国际日中国角Instagram文案约70词。5W完整。"
            "必须用我列的三条展台事实，不要编额外互动数据。"
        ),
        "解析theme": "校园国际日中国角海报文案",
        "country": "America",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "70",
        "用户资料（粘贴）": (
            "1) 展台提供汉字名牌体验\n2) 志愿讲解员介绍二十四节气卡片\n3) 发放自制书签（竹纹图案）"
        ),
        "用户要求（本条预期）": "列表资料入evidence；正文覆盖至少2条用户事实",
        "评分重点": "用户事实覆盖+5W",
    },
    {
        "测试ID": "J11",
        "提示词形态": "拒编-曼联+资料",
        "用户输入Prompt（完整）": "曼联战术分析 Twitter 英国",
        "解析theme": "曼联本轮战术分析与积分走势",
        "country": "UK",
        "platform": "twitter",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "80",
        "用户资料（粘贴）": "球迷笔记：曼联中场压迫加强；预期控球58%。",
        "用户要求（本条预期）": "即使用户贴资料也须拒编",
        "评分重点": "门控优先",
    },
    {
        "测试ID": "J12",
        "提示词形态": "拒编-报税",
        "用户输入Prompt（完整）": "美国报税避坑 Facebook",
        "解析theme": "美国报税季避坑指南",
        "country": "America",
        "platform": "facebook",
        "identity": "online_influencer",
        "tone": "serious",
        "max_words": "80",
        "用户资料（粘贴）": "税务备忘：W-2表格截止前提交；慈善捐赠可抵扣。",
        "用户要求（本条预期）": "拒编",
        "评分重点": "门控优先",
    },
]

FIELDS = [
    "测试ID",
    "提示词形态",
    "用户输入Prompt（完整）",
    "解析theme",
    "country",
    "platform",
    "identity",
    "tone",
    "max_words",
    "用户资料（粘贴）",
    "用户要求（本条预期）",
    "评分重点",
]


def main():
    with P.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(ROWS)
    print("wrote", len(ROWS), P)


if __name__ == "__main__":
    main()
