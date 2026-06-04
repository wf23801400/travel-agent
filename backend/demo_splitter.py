"""对比：手工切割 vs RecursiveCharacterTextSplitter。

跑一次就明白两种方式的差别。
"""

# ── 先装依赖（如果没装） ──────────────────────────
# pip install langchain-text-splitters  或者  pip install langchain

from langchain_text_splitters import RecursiveCharacterTextSplitter

# ════════════════════════════════════════════════════════
# 模拟一篇攻略文档
# ════════════════════════════════════════════════════════

DOC = """
# 北京三日游攻略

## 第一天：故宫天安门

早上8点到达天安门广场看升旗仪式。天安门广场是世界上最大的城市广场，
可以容纳100万人集会。广场中央矗立着人民英雄纪念碑，南面是毛主席纪念堂。

随后步行前往故宫博物院。故宫又称紫禁城，是明清两代的皇家宫殿，
始建于明朝永乐四年（1406年），历时14年建成。故宫占地72万平方米，
有大小宫殿70多座，房屋9000余间。建议游览时间3-4小时，
重点参观太和殿、中和殿、保和殿三大殿，以及乾清宫、坤宁宫等后三宫。

中午在故宫附近用餐，推荐尝试老北京炸酱面和豆汁儿。

下午游览景山公园，登上万春亭可以俯瞰故宫全貌和北京中轴线。
随后前往北海公园，欣赏白塔和湖光山色。晚上可以去南锣鼓巷逛胡同，
感受老北京风情。

## 第二天：长城

早上7点出发前往八达岭长城，车程约1.5小时。八达岭长城是明长城中
保存最完好的一段，海拔1015米。建议乘坐缆车上山，徒步下山。
游览时间约3-4小时，记得穿舒适的鞋子，带足水。

八达岭长城分为南城和北城，北城较为陡峭但景色更壮观。
好汉坡是北城的最高点，海拔888米。南城相对平缓，适合体力一般的游客。

中午在长城脚下的农家院用餐，推荐虹鳟鱼和贴饼子。

下午返回市区，可以顺路游览明十三陵。定陵是唯一被发掘的明代皇陵，
地下宫殿深27米，由前、中、后、左、右五个殿堂组成。游览时间约1.5小时。

## 第三天：颐和园

上午游览颐和园，这是中国现存最大的皇家园林，占地约290公顷。
主要景点包括万寿山、昆明湖、佛香阁、长廊、十七孔桥等。
长廊全长728米，绘有14000余幅彩画，被列入吉尼斯世界纪录。

从颐和园出来可以去圆明园遗址公园，感受历史的沧桑。
圆明园曾被誉为"万园之园"，1860年被英法联军焚毁。

下午前往清华大学或北京大学参观（需提前预约），感受中国顶尖学府的氛围。

晚上可以去三里屯或国贸商圈逛街购物，体验北京的现代都市生活。
"""

# ════════════════════════════════════════════════════════
# 方式1：现有手工切割
# ════════════════════════════════════════════════════════

import re

def manual_split(text: str) -> list[str]:
    """和 knowledge_retriever.py 中 _split_chunks 一样的逻辑。"""
    chunks = []
    sections = re.split(r"\n(?=## )", text)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        paragraphs = section.split("\n\n")
        buffer = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(buffer) + len(para) < 500:
                buffer += "\n" + para if buffer else para
            else:
                if buffer:
                    chunks.append(buffer.strip())
                buffer = para
        if buffer:
            chunks.append(buffer.strip())
    return chunks


# ════════════════════════════════════════════════════════
# 方式2：RecursiveCharacterTextSplitter
# ════════════════════════════════════════════════════════

def langchain_split(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        # 分隔符优先级：段落 → 换行 → 中文句号 → 中文逗号 → 空格 → 字符
        separators=["\n\n", "\n", "。", "，", " ", ""],
        chunk_size=300,      # 每个 chunk 最大 300 字
        chunk_overlap=50,    # 相邻 chunk 重叠 50 字，保证上下文连续
        length_function=len, # 按字符数算长度
        is_separator_regex=False,
    )
    return [doc.page_content for doc in splitter.create_documents([text])]


# ════════════════════════════════════════════════════════
# 对比例子
# ════════════════════════════════════════════════════════

print("=" * 70)
print("📦 手工切割结果（现有方式）")
print("=" * 70)

manual = manual_split(DOC)
print(f"总 chunk 数: {len(manual)}")
for i, chunk in enumerate(manual):
    start = chunk[:50].replace("\n", "\\n")
    print(f"  [{i}] 长度={len(chunk):4d} | {start}...")

print()
print("=" * 70)
print("🧩 RecursiveCharacterTextSplitter 切割结果")
print("=" * 70)

lc = langchain_split(DOC)
print(f"总 chunk 数: {len(lc)}")
for i, chunk in enumerate(lc):
    start = chunk[:50].replace("\n", "\\n")
    print(f"  [{i}] 长度={len(chunk):4d} | {start}...")

# ════════════════════════════════════════════════════════
# 展示重叠效果
# ════════════════════════════════════════════════════════
print()
print("=" * 70)
print("🔗 重叠效果（chunk_overlap=50）")
print("=" * 70)
for i in range(min(3, len(lc) - 1)):
    a, b = lc[i], lc[i + 1]
    # 找 b 的结尾和 a 的重叠部分
    overlap = a[-60:] if len(a) > 60 else a
    print(f"\n  chunk[{i}] 末尾:  ...{overlap[-60:]}")
    print(f"  chunk[{i+1}] 开头:  {b[:60]}")
