"""Append Q25-Q40 long/short stability pairs into quality CSV."""

from __future__ import annotations

import csv
from pathlib import Path

P = Path(__file__).resolve().parent / "skill_eval_cases_v0.3.2_quality.csv"

EXTRA = [
    {
        "测试ID": "Q25",
        "提示词形态": "极短-稳定对A",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": "新疆美食 IG 美国 80",
        "解析theme": "新疆美食的多样与烟火气（大盘鸡、拉面、馕）",
        "country": "America",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "80",
        "用户要求（本条预期）": "与Q26同角度；短令仍须完整5W+美国桥梁",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_A",
    },
    {
        "测试ID": "Q26",
        "提示词形态": "超长-稳定对A",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": (
            "【详细Brief】请你作为Instagram美食向博主，面向美国读者，先用拉斯韦尔5W完整策划，"
            "再写约80词英文正文（可少量emoji）。核心故事点只要一个：新疆街头大盘鸡+拉面+馕的烟火气与分享感。"
            "To Whom必须写清美国吃货/旅行爱好者为何会停；Effect=想收藏或想去尝；"
            "evidence_notes用Evidence#映射；禁止空泛口号与假数据。"
        ),
        "解析theme": "新疆美食的多样与烟火气（大盘鸡、拉面、馕）",
        "country": "America",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "80",
        "用户要求（本条预期）": "与Q25同角度；长约束下5W字段更完整且正文一致",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_A",
    },
    {
        "测试ID": "Q27",
        "提示词形态": "极短-稳定对B",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": "春节 英国 Twitter 70",
        "解析theme": "春节作为联合国教科文组织人类非物质文化遗产的当代生活意义",
        "country": "UK",
        "platform": "twitter",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "70",
        "用户要求（本条预期）": "短令；UNESCO有据则点到；英国桥梁",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_B",
    },
    {
        "测试ID": "Q28",
        "提示词形态": "超长-稳定对B",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": (
            "Course assignment style: Write a Twitter/X post (~70 words, English) for UK readers about "
            "Spring Festival as UNESCO-related living heritage in contemporary family/community life. "
            "Fill all five Lasswell Ws with substantive sentences (not labels). If evidence contains UNESCO, "
            "mention it in post or evidence_notes with Evidence# mapping. Do not mock British Christmas. Tone optimistic."
        ),
        "解析theme": "春节作为联合国教科文组织人类非物质文化遗产的当代生活意义",
        "country": "UK",
        "platform": "twitter",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "70",
        "用户要求（本条预期）": "长英文作业体；权威+受众双达标",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_B",
    },
    {
        "测试ID": "Q29",
        "提示词形态": "极短-稳定对C",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": "茶。美国IG。",
        "解析theme": "中国茶文化（UNESCO非遗）在当代社交与日常生活中的分享方式",
        "country": "America",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "75",
        "用户要求（本条预期）": "极简仍成稿；具体分享场景；权威可追溯",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_C",
    },
    {
        "测试ID": "Q30",
        "提示词形态": "超长-稳定对C",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": (
            "我在做国际传播练习账号。请根据5W，为美国Instagram受众写一条关于中国茶（UNESCO相关活态非遗）"
            "在日常分享中的故事帖（约75词）。要求：says_what只保留一个画面；to_whom写美国读者为何关心；"
            "禁止编造咖啡馆品牌名；evidence_notes写Evidence#对应；语气optimistic。"
        ),
        "解析theme": "中国茶文化（UNESCO非遗）在当代社交与日常生活中的分享方式",
        "country": "America",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "75",
        "用户要求（本条预期）": "长中文练习体；与Q29同角质量不崩",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_C",
    },
    {
        "测试ID": "Q31",
        "提示词形态": "极短-稳定对D",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": "崇礼滑雪 美国",
        "解析theme": "北京冬奥会赛后体育文化旅游带（崇礼等场馆遗产与大众参与）",
        "country": "America",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "80",
        "用户要求（本条预期）": "短令出具体体验点；遗产表述有据",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_D",
    },
    {
        "测试ID": "Q32",
        "提示词形态": "超长-稳定对D",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": (
            "Write an IG caption (~80w) for US audience on Chongli post-Olympics public skiing / venue heritage. "
            "Start with full 5W. One concrete scene only. Keep claims evidence-bound. Channel=Instagram. "
            "Effect=curiosity to visit or learn more. Include hashtags and two ops tips."
        ),
        "解析theme": "北京冬奥会赛后体育文化旅游带（崇礼等场馆遗产与大众参与）",
        "country": "America",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "80",
        "用户要求（本条预期）": "英文长提示与短令同分位达标",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_D",
    },
    {
        "测试ID": "Q33",
        "提示词形态": "极短-稳定对E",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": "火锅 TikTok 英国 幽默",
        "解析theme": "四川火锅作为社交餐桌文化（共享与热情）",
        "country": "UK",
        "platform": "tiktok",
        "identity": "online_influencer",
        "tone": "humorous",
        "max_words": "75",
        "用户要求（本条预期）": "短；钩子前置；英国社交桥梁；不踩英",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_E",
    },
    {
        "测试ID": "Q34",
        "提示词形态": "超长-稳定对E",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": (
            "Brief for TikTok: Audience=UK GenZ; Tone=humorous but respectful; Length≈75; "
            "Angle=Sichuan hotpot as social table culture; Must localize why UK readers would care "
            "(e.g. weekend social eating) without UK-bashing; Deliver 5W then caption; no fake stats."
        ),
        "解析theme": "四川火锅作为社交餐桌文化（共享与热情）",
        "country": "UK",
        "platform": "tiktok",
        "identity": "online_influencer",
        "tone": "humorous",
        "max_words": "75",
        "用户要求（本条预期）": "英文Brief与短令稳定",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_E",
    },
    {
        "测试ID": "Q35",
        "提示词形态": "极短-稳定对F",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": "丝路 推特 美国 70",
        "解析theme": "丝绸之路（长安-天山廊道）作为东西方交流的历史与当代连接",
        "country": "America",
        "platform": "twitter",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "70",
        "用户要求（本条预期）": "X短；交流叙事；美国读者动机",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_F",
    },
    {
        "测试ID": "Q36",
        "提示词形态": "超长-稳定对F",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": (
            "运营目标：做一条可收藏的丝路故事短帖（Twitter/X，约70词，美国读者）。"
            "期望Effect是让人想点开地图看看廊道连接。请先写满5W（每项至少一句完整话），再写正文；"
            "Says What只保留一个当代可感知连接点；事实跟论据走。"
        ),
        "解析theme": "丝绸之路（长安-天山廊道）作为东西方交流的历史与当代连接",
        "country": "America",
        "platform": "twitter",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "70",
        "用户要求（本条预期）": "Effect可感知；与短令同分位",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_F",
    },
    {
        "测试ID": "Q37",
        "提示词形态": "极短-稳定对G",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": "剪纸 日本 IG",
        "解析theme": "中国剪纸（UNESCO）在节日装饰与家庭手工中的当代生命力",
        "country": "Japan",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "75",
        "用户要求（本条预期）": "日本受众桥梁；手工/节日场景",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_G",
    },
    {
        "测试ID": "Q38",
        "提示词形态": "超长-稳定对G",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": (
            "我想做留学博主账号，给日本粉丝讲中国剪纸如何进入过节与家庭手工。"
            "请用乐观轻松语气，Instagram约75词英文。5W要完整：Who贴合留学博主；"
            "To Whom写日本读者可能共鸣的季节感或手工兴趣；若论据有UNESCO可点到；不要刻板说教。"
        ),
        "解析theme": "中国剪纸（UNESCO）在节日装饰与家庭手工中的当代生命力",
        "country": "Japan",
        "platform": "instagram",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "75",
        "用户要求（本条预期）": "角色长提示与短令稳定",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_G",
    },
    {
        "测试ID": "Q39",
        "提示词形态": "极短-稳定对H",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": "高铁日常 美国推特",
        "解析theme": "高铁连接多城的日常出行体验（现代中国生活）",
        "country": "America",
        "platform": "twitter",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "70",
        "用户要求（本条预期）": "现代日常场景；无假统计",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_H",
    },
    {
        "测试ID": "Q40",
        "提示词形态": "超长-稳定对H",
        "能力线": "长短稳定性",
        "用户输入Prompt（完整）": (
            "【需求单】平台twitter｜受众美国年轻人｜字数70｜语气optimistic｜任务：5W+正文+hashtags+ops_tips｜"
            "角度：高铁日常出行里的现代中国生活｜禁：假统计、空泛爱国口号｜"
            "To Whom必须写清美国读者为何会停（效率/旅行好奇等）｜Effect=正向理解现代中国出行日常。"
        ),
        "解析theme": "高铁连接多城的日常出行体验（现代中国生活）",
        "country": "America",
        "platform": "twitter",
        "identity": "online_influencer",
        "tone": "optimistic",
        "max_words": "70",
        "用户要求（本条预期）": "需求单长体与短令稳定",
        "评分重点": "短vs长稳定",
        "稳定配对": "PAIR_H",
    },
]


def main():
    rows = list(csv.DictReader(P.open(encoding="utf-8-sig")))
    fields = list(rows[0].keys())
    if "稳定配对" not in fields:
        fields.append("稳定配对")
    by = {}
    for r in rows:
        r = dict(r)
        r.setdefault("稳定配对", "")
        by[r["测试ID"]] = r
    for r in EXTRA:
        by[r["测试ID"]] = r
    ordered = [by[f"Q{i:02d}"] for i in range(1, 41)]
    with P.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(ordered)
    print("wrote", len(ordered), "cases ->", P)


if __name__ == "__main__":
    main()
