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
    mnn = re.search(r"第\s*0*(\d+)\s*篇", base + meta.get("篇号", ""))
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

    return {"nn": nn, "title": title, "short": short_title(title),
            "module": module_of(meta), "has_quickref": bool(quickref)}


def main():
    os.makedirs(ART_OUT, exist_ok=True)
    os.makedirs(IMG_OUT, exist_ok=True)
    # 清空旧产物
    for p in glob.glob(os.path.join(ART_OUT, "*.md")):
        os.remove(p)
    for p in glob.glob(os.path.join(IMG_OUT, "*")):
        shutil.rmtree(p, ignore_errors=True)

    folders = sorted(glob.glob(os.path.join(ROOT, "第*篇*")))
    items = []
    for f in folders:
        if os.path.isdir(f):
            r = process_one(f)
            if r:
                items.append(r)
                print(f"  收录 {r['nn']} · {r['title']}  (速查层={r['has_quickref']})")
    items.sort(key=lambda x: x["nn"])

    # 侧边栏：按模块分组，保持首次出现顺序
    groups, order = {}, []
    for it in items:
        g = it["module"]
        if g not in groups:
            groups[g] = []
            order.append(g)
        groups[g].append({"text": f"{it['nn']} · {it['short']}",
                          "link": f"/articles/{it['nn']}"})
    sidebar = [{"text": g, "collapsed": False, "items": groups[g]} for g in order]
    json.dump(sidebar, open(os.path.join(SITE, ".vitepress", "sidebar.json"),
              "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 首页（home 布局：Hero + Features 卡片 + 订阅入口）
    BILI_URL = "https://space.bilibili.com/1817350057"   # B 站空间

    def icon_of(name):
        table = [("基础", "🧰"), ("电源", "⚡"), ("PI", "⚡"), ("信号", "📡"),
                 ("SI", "📡"), ("时序", "⏱"), ("时钟", "⏱"), ("总线", "🔌"),
                 ("接口", "🚄"), ("高速", "🚄"), ("功耗", "🔋"), ("电池", "🔋"),
                 ("EMC", "📶"), ("EMI", "📶"), ("ESD", "⚡"), ("热", "🌡"),
                 ("无线", "📶"), ("射频", "📶"), ("防护", "🛡"), ("可靠", "🛡"),
                 ("产测", "🏭")]
        for k, v in table:
            if k in name:
                return v
        return "📄"

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
           "      text: 🔧 工程师速查篇",
           "      link: /articles/13",
           "",
           "features:"]
    for g in order:
        arts = [x for x in items if x["module"] == g]
        shorts = " / ".join(a["short"] for a in arts[:3])
        det = f"{len(arts)} 篇 · {shorts}"
        out += [f"  - icon: {icon_of(g)}",
                f"    title: {g}",
                f"    details: {det}",
                f"    link: /articles/{arts[0]['nn']}",
                "    linkText: 进入模块"]
    out += ["---", "",
            '<div class="subscribe-row">',
            '  <a class="site" href="/articles/01">📚 全部文章</a>',
            f'  <a class="bili" href="{BILI_URL}" target="_blank" rel="noreferrer">📺 B 站追更</a>',
            '  <a class="wechat" href="/about">💚 公众号「硬件研发测试」</a>',
            "</div>", "",
            "## 🆕 最新更新", ""]
    for it in sorted(items, key=lambda x: x["nn"], reverse=True)[:5]:
        tag = " 🔧" if it["has_quickref"] else ""
        out.append(f"- [{it['nn']} · {it['title']}](/articles/{it['nn']}){tag}")
    out += ["",
            f"> 📈 已收录 **{len(items)}** 篇 · **{len(order)}** 个模块，持续更新中。"
            " 🔧 = 含工程师速查（判据表 / 规格 / 设备设置 / 踩坑）。"]
    open(os.path.join(SITE, "index.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")

    print(f"\n完成：收录 {len(items)} 篇，模块 {len(order)} 个。")
    print("sidebar.json + index.md 已生成。")


if __name__ == "__main__":
    main()
