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

    # 首页
    lines = ["---", "layout: doc", "title: 硬件测试科普百科", "---", "",
             "# 硬件测试科普百科", "",
             "> 把消费电子「硬件测试」的知识，做成一套可长期查阅、可全文搜索的完整百科。",
             "> 每篇 = 通俗讲解 + 工程师速查（判据表 / 规格 / 设备设置 / 踩坑）。", ""]
    for g in order:
        lines.append(f"## {g}")
        lines.append("")
        for it in [x for x in items if x["module"] == g]:
            tag = " 🔧" if it["has_quickref"] else ""
            lines.append(f"- [{it['nn']} · {it['title']}](/articles/{it['nn']}){tag}")
        lines.append("")
    open(os.path.join(SITE, "index.md"), "w", encoding="utf-8").write("\n".join(lines))

    print(f"\n完成：收录 {len(items)} 篇，模块 {len(order)} 个。")
    print("sidebar.json + index.md 已生成。")


if __name__ == "__main__":
    main()
