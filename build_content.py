# -*- coding: utf-8 -*-
"""把各篇 第NN篇/*.md 转成 VitePress 网站版（articles/ + public/images/）。

转换规则（服务"自用速查"百科）：
  - 去 front-matter，取「标题」；正文标题用 H1。
  - 剥离开头「> 📚 系列徽章」、结尾「留个互动 / 下期见」预告（公众号味）。
  - 保留 `📌` 交叉引用（wiki 里有用）。
  - 保留两层：正文 + <!--QUICKREF--> 速查层（速查层完整收录，是自用速查主体）。
  - 图片路径 images/x.png -> /images/NN/x.png，并把图片拷到 public/images/NN/。
  - 生成 .vitepress/sidebar.json（按模块分组）+ 首页 index.md。
用法：python build_content.py
"""
import os, re, glob, shutil, json

SITE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SITE)
ART_OUT = os.path.join(SITE, "articles")
IMG_OUT = os.path.join(SITE, "public", "images")


def parse_front_matter(text):
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    body = text
    if m:
        for ln in m.group(1).split("\n"):
            mm = re.match(r"\s*([^：:]+)[：:]\s*(.+)", ln)
            if mm:
                meta[mm.group(1).strip()] = mm.group(2).strip()
        body = text[m.end():]
    return meta, body


def strip_badge(body):
    """删掉 H1 之后第一处含 📚 的引用块（系列徽章）。"""
    lines = body.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        if ln.lstrip().startswith(">") and "📚" in ln:
            # 跳过这一整段引用块
            while i < n and (lines[i].lstrip().startswith(">") or lines[i].strip() == ""):
                # 仅在仍处于引用块时吞掉空行：遇到下一段正文就停
                if lines[i].strip() == "":
                    i += 1
                    break
                i += 1
            continue
        out.append(ln)
        i += 1
    return "\n".join(out)


def strip_interaction(pre):
    """删掉「留个互动」整段（到 pre 结尾）及其前面的分隔线。"""
    m = re.search(r"\n[^\n]*留个互动", pre)
    if not m:
        return pre
    cut = m.start()
    head = pre[:cut].rstrip()
    # 去掉互动段前残留的 '---' 分隔线
    head = re.sub(r"\n+---\s*$", "", head)
    return head + "\n"


def drop_teaser_paras(pre):
    """删掉含「下期见」的预告段落。"""
    paras = re.split(r"\n\s*\n", pre)
    keep = [p for p in paras if "下期见" not in p]
    return "\n\n".join(keep)


def fix_images(text, nn):
    return re.sub(r"\]\(images/", f"](/images/{nn}/", text)


def module_of(meta):
    s = meta.get("篇号", "")
    m = re.search(r"（(.+?)）", s)
    if m:
        return re.sub(r"\s*·\s*系列开篇$", "", m.group(1)).strip()
    return "其他"


# ===== 知识地图：权威模块骨架（含尚未开发的置灰占位）=====
CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
          "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11}
NUM_CN = {v: k for k, v in CN_NUM.items()}

# num, 显示名, icon, 规划说明（未开发时显示在置灰卡片上）
MODULE_SKELETON = [
    (1,  "测试基础与方法论", "🧰", ""),
    (2,  "电源完整性 PI",    "⚡", ""),
    (3,  "信号完整性 SI",    "📡", ""),
    (4,  "时序与时钟",       "⏱", ""),
    (5,  "低速总线",         "🔌", "I2C / SPI / UART 等低速总线读写与一致性"),
    (6,  "高速总线 / 接口",   "🚄", ""),
    (7,  "功耗与电池",       "🔋", "静态 / 动态功耗 · 续航 · 快充 · 电量计"),
    (8,  "EMC / EMI / ESD",  "📶", "辐射 / 传导 · 静电防护 · 浪涌（决定能否上市）"),
    (9,  "热设计与热测试",   "🌡", "温升 / 热阻 / 热成像 · 降频与热保护"),
    (10, "无线与射频",       "📶", "功率 / 频偏 / EVM · WiFi / 蓝牙 · 天线 OTA"),
    (11, "整机 · 可靠性 · 产测", "🛡", "跌落 / 高低温 / 振动 / 老化 · 量产 DFT"),
]
# key, 显示名, icon, 说明
EXTRA_SKELETON = [
    ("bonus", "实战番外", "🧭", "技术之外、同样决定专业度的实战功夫"),
    ("quick", "速查地图", "🗺", "把某类测试项编成一张速查矩阵"),
]
# 个别篇的模块归属修正（篇号写法历史遗留）：nn -> 模块号
MODULE_OVERRIDE = {"10": 11, "12": 11}


def module_num_of(meta, nn):
    """返回该篇所属模块键：整数 1-11 / 'bonus' / 'quick' / 99(兜底未归类)。"""
    if nn.startswith("b"):
        return "bonus"
    if nn.startswith("q"):
        return "quick"
    if nn in MODULE_OVERRIDE:
        return MODULE_OVERRIDE[nn]
    s = meta.get("篇号", "")
    m = re.search(r"模块\s*([一二三四五六七八九十]+)", s)
    if m and m.group(1) in CN_NUM:
        return CN_NUM[m.group(1)]
    return 99


def short_title(t):
    # 取主词做侧边栏短标题
    t = re.split(r"[：:？！?!]", t)[0]
    t = re.split(r"——|，|、", t)[0]
    return t.strip()


def process_one(folder):
    mds = [p for p in glob.glob(os.path.join(folder, "*.md"))
           if not os.path.basename(p).lower().startswith("readme")]
    if not mds:
        return None
    md = max(mds, key=os.path.getsize)
    text = open(md, encoding="utf-8").read()
    if "TODO：正文" in text:           # 跳过 new_article 生成的未完成 stub
        print("  跳过(未完成):", os.path.basename(folder))
        return None
    meta, body = parse_front_matter(text)
    base = os.path.basename(folder)
    key = base + meta.get("篇号", "")
    bx = re.search(r"番外\s*0*(\d+)", key)
    qx = re.search(r"速查\s*0*(\d+)", key)
    if bx:                                  # 实战番外：独立编号 b01/b02…
        nn = "b" + bx.group(1).zfill(2)
    elif qx:                                # 速查地图/索引篇：独立编号 q01/q02…
        nn = "q" + qx.group(1).zfill(2)
    else:
        mnn = re.search(r"第\s*0*(\d+)\s*篇", key)
        nn = mnn.group(1).zfill(2) if mnn else "00"
    title = meta.get("标题", "").strip() or base

    # 拆速查层
    parts = re.split(r"<!--\s*QUICKREF\s*-->", body, maxsplit=1)
    pre = parts[0]
    quickref = parts[1] if len(parts) > 1 else ""

    pre = strip_badge(pre)
    pre = strip_interaction(pre)
    pre = drop_teaser_paras(pre)
    pre = fix_images(pre, nn).strip()
    quickref = fix_images(quickref, nn).strip()

    page = pre
    if quickref:
        page += "\n\n---\n\n" + quickref

    # 顶部徽章条：模块 / 阅读时长 / 速查层
    modname = module_of(meta)
    plain = re.sub(r"\s+", "", re.sub(r"!\[[^\]]*\]\([^)]*\)", "", page))
    minutes = max(1, round(len(plain) / 380))
    qr_badge = '<span class="badge qr">🔧 含工程师速查</span>' if quickref else ""
    meta_bar = ('<div class="article-meta">'
                f'<span class="badge">📘 {modname}</span>'
                f'<span class="badge">⏱ 约 {minutes} 分钟</span>'
                f'{qr_badge}</div>\n')
    page, n_ins = re.subn(r"^(#\s+.+)$",
                          lambda m: m.group(1) + "\n\n" + meta_bar,
                          page, count=1, flags=re.M)
    if n_ins == 0:
        page = meta_bar + page

    # VitePress front-matter
    fm = f"---\ntitle: {title}\noutline: [2,3]\n---\n\n"
    out_md = os.path.join(ART_OUT, f"{nn}.md")
    open(out_md, "w", encoding="utf-8").write(fm + page + "\n")

    # 拷图（所有图片类型，仅 images/ 顶层，不含 covers 子目录）
    src_img = os.path.join(folder, "images")
    if os.path.isdir(src_img):
        dst = os.path.join(IMG_OUT, nn)
        os.makedirs(dst, exist_ok=True)
        for ext in ("png", "jpg", "jpeg", "gif", "webp", "svg"):
            for p in glob.glob(os.path.join(src_img, f"*.{ext}")):
                shutil.copy2(p, dst)

    fshort = re.sub(r"^(第\s*\d+\s*篇|番外\s*\d+|速查\s*\d+)[ _\-]*", "", base).strip()
    return {"nn": nn, "title": title, "short": short_title(title),
            "fshort": fshort or short_title(title),
            "module": module_of(meta), "modkey": module_num_of(meta, nn),
            "has_quickref": bool(quickref)}


def main():
    os.makedirs(ART_OUT, exist_ok=True)
    os.makedirs(IMG_OUT, exist_ok=True)
    # 清空旧产物
    for p in glob.glob(os.path.join(ART_OUT, "*.md")):
        os.remove(p)
    for p in glob.glob(os.path.join(IMG_OUT, "*")):
        shutil.rmtree(p, ignore_errors=True)

    folders = sorted(glob.glob(os.path.join(ROOT, "第*篇*"))) \
        + sorted(glob.glob(os.path.join(ROOT, "番外*"))) \
        + sorted(glob.glob(os.path.join(ROOT, "速查*")))
    items = []
    for f in folders:
        if os.path.isdir(f):
            r = process_one(f)
            if r:
                items.append(r)
                print(f"  收录 {r['nn']} · {r['title']}  (速查层={r['has_quickref']})")
    items.sort(key=lambda x: x["nn"])

    # ===== 按权威模块骨架归类，生成知识地图数据 modules.json =====
    def articles_of(modkey):
        arts = sorted((it for it in items if it["modkey"] == modkey),
                      key=lambda x: x["nn"])
        return [{"nn": a["nn"], "name": a["fshort"], "qr": a["has_quickref"]}
                for a in arts]

    modules_json = []
    for num, title, icon, note in MODULE_SKELETON:
        arts = articles_of(num)
        modules_json.append({
            "key": num, "badge": "模块" + NUM_CN[num], "title": title,
            "icon": icon, "status": "active" if arts else "planned",
            "note": note, "articles": arts})
    extra_json = []
    for key, title, icon, note in EXTRA_SKELETON:
        arts = articles_of(key)
        extra_json.append({
            "key": key, "badge": {"bonus": "番外", "quick": "速查"}[key],
            "title": title, "icon": icon,
            "status": "active" if arts else "planned",
            "note": note, "articles": arts})

    classified = sum(len(m["articles"]) for m in modules_json + extra_json)
    if classified != len(items):
        known = {m["key"] for m in modules_json} | {"bonus", "quick"}
        miss = [it["nn"] for it in items if it["modkey"] not in known]
        print("⚠️ 未归类篇（请检查篇号）:", miss)

    active_mods = sum(1 for m in modules_json if m["status"] == "active")
    data = {"modules": modules_json, "extra": extra_json,
            "stats": {"articles": len(items), "modules_active": active_mods}}
    json.dump(data, open(os.path.join(SITE, ".vitepress", "theme", "modules.json"),
              "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ===== 侧边栏：按模块骨架顺序，仅列已上线模块 =====
    sidebar = []
    for m in modules_json + extra_json:
        if m["status"] != "active":
            continue
        sidebar.append({
            "text": m["badge"] + " · " + m["title"], "collapsed": False,
            "items": [{"text": f'{a["nn"]} · {a["name"]}',
                       "link": f'/articles/{a["nn"]}'} for a in m["articles"]]})
    json.dump(sidebar, open(os.path.join(SITE, ".vitepress", "sidebar.json"),
              "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ===== 首页：Hero + 知识地图组件 + 订阅 + 最新更新 =====
    BILI_URL = "https://space.bilibili.com/1817350057"   # B 站空间
    qnn = next((a["nn"] for a in articles_of("quick")), "01")

    out = ["---", "layout: home", "title: 硬件测试科普百科", "",
           "hero:",
           "  name: 硬件测试科普百科",
           "  text: 把硬件测试讲透",
           "  tagline: 消费电子硬件测试知识库 · 通俗讲解 ＋ 工程师速查 · 全文可搜",
           "  image:",
           "    src: /logo.svg",
           "    alt: 硬件测试科普百科",
           "  actions:",
           "    - theme: brand",
           "      text: 📖 从头开始读",
           "      link: /articles/01",
           "    - theme: alt",
           "      text: 🔧 工程师速查",
           f"      link: /articles/{qnn}",
           "---", "",
           "<HomeMap />", "",
           '<div class="subscribe-row">',
           '  <a class="site" href="/articles/01">📚 全部文章</a>',
           f'  <a class="bili" href="{BILI_URL}" target="_blank" rel="noreferrer">📺 B 站追更</a>',
           '  <a class="wechat" href="/about">💚 公众号「硬件研发测试」</a>',
           "</div>", "",
           "## 📥 配套模板下载", "",
           '<div class="download-row">',
           '  <a class="dl-card" href="/downloads/hw_test_plan_template.xlsx" download>'
           '<span class="dl-ico">📊</span>'
           '<span class="dl-body"><strong>硬件测试计划 + 用例模板</strong>'
           '<em>含 TPS54331 范本 · 空白模板换任何 IC 直接套 · .xlsx</em></span></a>',
           '  <a class="dl-card" href="/downloads/hw_material_change_template.xlsx" download>'
           '<span class="dl-ico">🔄</span>'
           '<span class="dl-body"><strong>物料替换 + 回归测试模板</strong>'
           '<em>替代料评估 / 回归清单 · .xlsx</em></span></a>',
           "</div>", "",
           "## 🆕 最新更新", ""]
    for it in sorted(items, key=lambda x: x["nn"], reverse=True)[:6]:
        tag = " 🔧" if it["has_quickref"] else ""
        out.append(f"- [{it['nn']} · {it['title']}](/articles/{it['nn']}){tag}")
    open(os.path.join(SITE, "index.md"), "w",
         encoding="utf-8").write("\n".join(out) + "\n")

    print(f"\n完成：收录 {len(items)} 篇，已上线模块 {active_mods} 个"
          f"（骨架 {len(MODULE_SKELETON)} + 番外/速查）。")
    print("modules.json + sidebar.json + index.md 已生成。")


if __name__ == "__main__":
    main()
