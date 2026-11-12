#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spec_tool.py —— 三层真相源（change -> spec）的确定性工具

存在的理由：/workflow archive 的 delta 合并过去只是「提示词里的步骤」，
执行者是人或 AI，合并规则含糊会导致两类稳定缺陷：
  1) ADDED 条目的前缀被带进 spec，得到 "## ADDED R3" 这种脏标题；
  2) MODIFIED 之后看不出这条能力被改过。
以及三类工程隐患：无原子性、无并发锁、validate 无实现。

本脚本把 validate / merge / archive 变成可执行、可测试、失败可回滚的操作。

子命令
  validate     校验 _tmp/07-spec-delta.md 与 spec/{module}.md 的一致性（C1-C8）
  merge        计算 delta -> spec 合并结果；--dry-run 只打印，--apply 原子写入
  archive      归档事务：加锁 -> validate -> merge -> 移文档 -> 更新索引 -> 清空 _tmp
  check-spec   只体检 spec 自身（C4 / C8），用于存量基线

用法
  python spec_tool.py validate   --module economy
  python spec_tool.py merge      --module economy --version v0.2.0 [--apply]
  python spec_tool.py archive    --module economy --version v0.2.0 --subcategory purchase [--apply]
  python spec_tool.py check-spec --module economy

退出码
  0 通过    1 校验失败    2 用法/环境错误    3 缺基线或锁冲突
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timezone

try:  # 让 Windows 控制台按实际代码页输出，避免中文变乱码；仍以 utf-8 读写文件
    if os.name == "nt":
        import ctypes

        _cp = ctypes.windll.kernel32.GetConsoleOutputCP()
        _enc = {65001: "utf-8", 936: "gbk", 932: "cp932", 949: "cp949"}.get(_cp)
        if _enc:
            sys.stdout.reconfigure(encoding=_enc, errors="replace")
            sys.stderr.reconfigure(encoding=_enc, errors="replace")
    else:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

SPEC_H2 = re.compile(r"^##\s+R(\d+)\s*[—–-]\s*(.+?)\s*$")
DELTA_H2 = re.compile(r"^##\s+(ADDED|MODIFIED|REMOVED)\s+R(\d+)\s*[—–-]\s*(.+?)\s*$")
BAD_SPEC_H2 = re.compile(r"^##\s+(ADDED|MODIFIED|REMOVED)\s+R\d+")
ANY_H2 = re.compile(r"^##\s+")
SCEN = re.compile(r"^###\s*场景\s*[:：]")
STAMP = re.compile(r"^>\s*由\s*change/")

CLIENT_WORDS = ("客户端", "UI", "界面", "UMG", "蓝图", "Widget", "显示", "本地")
AUTH_WORDS = ("服务端", "服务器", "HasAuthority", "Gameplay", "Application", "写入口", "权威")

LOCK_NAME = ".archive.lock"
LOCK_STALE_SEC = 30 * 60


# ---------------------------------------------------------------- 基础设施
def die(msg, code=2):
    print("[ERROR] " + msg)
    sys.exit(code)


def ok(msg):
    print("[OK]    " + msg)


def fail(msg):
    print("[FAIL]  " + msg)


def warn(msg):
    print("[WARN]  " + msg)


def read(path):
    # utf-8-sig：容忍 BOM。带 BOM 的文件若不剥离，首行标题正则失配，
    # 会导致整条需求被静默跳过（validate 假通过）。
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def read_lines(path):
    return read(path).splitlines()


def write_atomic(path, text):
    """同目录临时文件 + os.replace，保证不会写出半个文件。"""
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)  # 首次归档时 spec/ 可能还不存在
    tmp = os.path.join(d, ".tmp_" + os.path.basename(path))
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
    os.replace(tmp, path)


class Section(object):
    def __init__(self, rid, title, body, raw_head):
        self.id = rid
        self.title = title
        self.body = body          # list[str]，不含标题行
        self.raw_head = raw_head  # 原始标题行


def split_sections(lines, pattern):
    """按 `## R{n}` / `## OP R{n}` 切段。返回 (preamble, [Section])。"""
    preamble, sections = [], []
    cur = None
    for line in lines:
        m = pattern.match(line)
        if m:
            if cur is not None:
                sections.append(cur)
            if pattern is SPEC_H2:
                cur = Section(int(m.group(1)), m.group(2), [], line)
            else:
                cur = Section(int(m.group(2)), m.group(3), [], line)
                cur.op = m.group(1)
            continue
        if cur is None:
            preamble.append(line)
        else:
            cur.body.append(line)
    if cur is not None:
        sections.append(cur)
    return preamble, sections


def scenario_blocks(body_lines):
    blocks, cur = [], None
    for line in body_lines:
        if SCEN.match(line):
            if cur is not None:
                blocks.append(cur)
            cur = [line]
        elif cur is not None:
            cur.append(line)
    if cur is not None:
        blocks.append(cur)
    return blocks


SPEC_DIR = "spec"
CHANGE_DIR = "change"


def paths(root, module):
    return (
        os.path.join(root, CHANGE_DIR, module, "_tmp"),
        os.path.join(root, SPEC_DIR, module + ".md"),
        os.path.join(root, CHANGE_DIR, module, "version.json"),
    )


# ---------------------------------------------------------------- validate
def load_delta(tmp_dir):
    p = os.path.join(tmp_dir, "07-spec-delta.md")
    if not os.path.exists(p):
        return None
    return split_sections(read_lines(p), DELTA_H2), p


def check_delta_shape(lines):
    """C1：delta 里所有 `## ` 标题都必须是 ADDED/MODIFIED/REMOVED R{n}。"""
    errs = []
    for i, line in enumerate(lines, 1):
        if ANY_H2.match(line) and not DELTA_H2.match(line):
            errs.append("C1 第 %d 行标题不合法: %s" % (i, line.strip()))
    return errs


def cmd_validate(args):
    root, module = args.root, args.module
    tmp_dir, spec_path, _ = paths(root, module)

    if not os.path.isdir(tmp_dir):
        die("找不到迭代目录: " + tmp_dir, 2)

    dl = load_delta(tmp_dir)
    if dl is None:
        fail("C0 缺少 change/%s/_tmp/07-spec-delta.md（若本次无行为变更，请显式声明）" % module)
        return 1
    (delta_pre, delta_secs), delta_path = dl

    errors, warnings = [], []
    errors += check_delta_shape(read_lines(delta_path))

    spec_exists = os.path.exists(spec_path)
    spec_secs = []
    if spec_exists:
        spec_pre, spec_secs = split_sections(read_lines(spec_path), SPEC_H2)
        ids = [s.id for s in spec_secs]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            errors.append("C4 spec 内 R 编号重复: %s" % ", ".join("R%d" % d for d in dup))
        for i, line in enumerate(read_lines(spec_path), 1):
            if BAD_SPEC_H2.match(line):
                errors.append("C8 spec 第 %d 行标题含操作前缀（应剥离）: %s" % (i, line.strip()))
    else:
        ids = []
        warn("spec/%s.md 不存在：本次归档将生成基线" % module)

    ids_set = set(ids)
    seen = {}
    for s in delta_secs:
        if s.id in seen:
            errors.append("C1 delta 内重复定义 R%d（%s 与 %s）" % (s.id, seen[s.id], s.op))
        seen[s.id] = s.op

        if s.op in ("MODIFIED", "REMOVED") and spec_exists and s.id not in ids_set:
            errors.append("C2 %s R%d 在 spec 中不存在（防改/删幽灵需求）" % (s.op, s.id))
        if s.op == "ADDED" and s.id in ids_set:
            errors.append("C3 ADDED R%d 与现存 spec 冲突" % s.id)

        blocks = scenario_blocks(s.body)
        if s.op in ("ADDED", "MODIFIED") and not blocks:
            errors.append("C5 %s R%d 缺少 `### 场景:`" % (s.op, s.id))
        for b in blocks:
            text = "\n".join(b)
            if "当" not in text:
                errors.append("C6 R%d 某场景缺「当」(第 %s)" % (s.id, b[0].strip()))
            if "则" not in text:
                errors.append("C6 R%d 某场景缺「则」(第 %s)" % (s.id, b[0].strip()))
            else:
                then_part = "".join(l for l in b if l.strip().startswith("- 则"))
                hit_c = any(w in then_part for w in CLIENT_WORDS)
                hit_a = any(w in then_part for w in AUTH_WORDS)
                if hit_c and not hit_a:
                    warnings.append("C7 R%d 的「则」疑似只落在表现层: %s" % (s.id, then_part.strip()))

    # C9（warning）：设计文档应记录"在途契约终检"（跨模块并行时的人工结论）
    _design = os.path.join(tmp_dir, "02-design.md")
    if os.path.exists(_design) and "在途契约终检" not in read(_design):
        warnings.append("C9 02-design.md 缺少「在途契约终检」记录（无跨模块契约变更时可忽略）")

    for e in errors:
        fail(e)
    for w in warnings:
        warn(w)
    if errors:
        print("\n校验失败：%d 个 error / %d 个 warning" % (len(errors), len(warnings)))
        return 1
    ok("C1-C9 通过（%d 条 delta 条目，%d 个 warning）" % (len(delta_secs), len(warnings)))
    return 0


def cmd_check_spec(args):
    spec_path = os.path.join(args.root, SPEC_DIR, args.module + ".md")
    if not os.path.exists(spec_path):
        die("找不到 " + spec_path, 2)
    lines = read_lines(spec_path)
    _, secs = split_sections(lines, SPEC_H2)
    ids = [s.id for s in secs]
    errs = []
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        errs.append("C4 R 编号重复: %s" % ", ".join("R%d" % d for d in dup))
    for i, line in enumerate(lines, 1):
        if BAD_SPEC_H2.match(line):
            errs.append("C8 第 %d 行标题含操作前缀: %s" % (i, line.strip()))
    for e in errs:
        fail(e)
    if errs:
        return 1
    ok("spec 体检通过（%d 条能力）" % len(secs))
    return 0


def cmd_check_modules(args):
    """校验模块分类四处一致：架构.md §6 表 ↔ versions.json ↔ change/ 目录 ↔ knowledge/ 文件。"""
    arch = os.path.join(args.root, "开发规范", "架构.md")
    if not os.path.exists(arch):
        die("找不到 " + arch, 2)
    table = set(re.findall(r"^\|\s*`([A-Za-z0-9_\-]+)`\s*\|", read(arch), re.M))

    gv = load_json(os.path.join(args.root, CHANGE_DIR, "versions.json"), {})
    declared = set(gv.get("modules", {}).keys())

    ch_dir = os.path.join(args.root, CHANGE_DIR)
    change_mods = {d for d in os.listdir(ch_dir)
                   if os.path.isdir(os.path.join(ch_dir, d)) and not d.startswith(".")} if os.path.isdir(ch_dir) else set()

    kn_dir = os.path.join(args.root, "knowledge")
    knowledge_mods = {f[:-3] for f in os.listdir(kn_dir)
                      if f.endswith(".md") and not f.startswith("_") and f != "README.md"} if os.path.isdir(kn_dir) else set()

    sp_dir = os.path.join(args.root, SPEC_DIR)
    spec_mods = {f[:-3] for f in os.listdir(sp_dir)
                 if f.endswith(".md") and not f.startswith("_") and f != "README.md"} if os.path.isdir(sp_dir) else set()

    errs, warns = [], []
    if table and declared != table:
        errs.append("C9 架构.md §6 表 %s 与 versions.json %s 不一致" % (sorted(table), sorted(declared)))
    if not table:
        warns.append("C9 架构.md 未解析到模块表（检查 §6 是否为 `| \\`module\\` | … |` 格式）")
    for name, got in (("change/", change_mods), ("knowledge/", knowledge_mods), ("spec/", spec_mods)):
        extra = got - declared
        if extra:
            errs.append("C9 %s 下存在未登记模块: %s（先更新架构.md §6 与 versions.json）" % (name, ", ".join(sorted(extra))))
    missing = declared - change_mods
    if missing:
        warns.append("C9 已登记但尚未建目录的模块: %s（首次 init 时创建即可）" % ", ".join(sorted(missing)))

    for e in errs:
        fail(e)
    for w in warns:
        warn(w)
    if errs:
        return 1
    ok("模块分类一致（%d 个模块；change %d / knowledge %d / spec %d）"
       % (len(declared), len(change_mods), len(knowledge_mods), len(spec_mods)))
    return 0


# ---------------------------------------------------------------- merge
def already_applied(root, module, version, subcategory):
    """幂等检查：该 delta 是否已经合并进 spec。用于安全重跑。"""
    tmp_dir, spec_path, _ = paths(root, module)
    dl = load_delta(tmp_dir)
    if dl is None or not os.path.exists(spec_path):
        return False
    (_, delta_secs), _ = dl
    _, secs = split_sections(read_lines(spec_path), SPEC_H2)
    by_id = {s.id: s for s in secs}
    for s in delta_secs:
        if s.op == "ADDED" and s.id not in by_id:
            return False
        if s.op == "MODIFIED":
            t = by_id.get(s.id)
            if t is None or ("（MODIFIED %s）" % version) not in t.title:
                return False
        if s.op == "REMOVED" and s.id in by_id:
            return False
    return True


def build_merged(root, module, version, subcategory, today):
    tmp_dir, spec_path, _ = paths(root, module)
    dl = load_delta(tmp_dir)
    if dl is None:
        return None, None, ["缺少 07-spec-delta.md"]
    (delta_pre, delta_secs), _ = dl

    exists = os.path.exists(spec_path)
    if exists:
        spec_lines = read_lines(spec_path)
        pre, secs = split_sections(spec_lines, SPEC_H2)
    else:
        pre, secs = [], []

    added = [s for s in delta_secs if s.op == "ADDED"]
    modified = {s.id: s for s in delta_secs if s.op == "MODIFIED"}
    removed = {s.id for s in delta_secs if s.op == "REMOVED"}

    out = []
    stamp = "> 由 change/%s/%s %s 的 07-spec-delta.md 归档合并生成（%s）。" % (
        module, subcategory, version, today)
    # 源包 archive.json step 6 要求的机器可读归档戳（真实产物里没写，两者都保留）
    stamp2 = "> 最后归档 %s @ %s" % (version, today)
    readonly = "> 本文件是当前真相源（what）；只读——更新唯一入口是 /workflow archive 的 delta 合并。"

    if exists:
        pre = list(pre)
        replaced = False
        for i, line in enumerate(pre):
            if STAMP.match(line):
                pre[i] = stamp
                replaced = True
                break
        if not replaced:
            pre.insert(1, stamp)
        hit2 = False
        for i, line in enumerate(pre):
            if line.startswith("> 最后归档 "):
                pre[i] = stamp2
                hit2 = True
                break
        if not hit2:
            idx = next((i for i, l in enumerate(pre) if STAMP.match(l)), 0)
            pre.insert(idx + 1, stamp2)
        out.extend([l for l in pre])
    else:
        out.append("# %s 模块规格（活规格基线）" % module)
        out.append("")
        out.append(stamp)
        out.append(stamp2)
        out.append(readonly)
        out.append("")
        out.append("---")
        out.append("")

    while out and out[-1].strip() == "":
        out.pop()

    def emit(section, title_suffix=""):
        out.append("")
        out.append("## R%d — %s%s" % (section.id, section.title, title_suffix))
        for line in section.body:
            out.append(line)
        while len(out) >= 2 and out[-1].strip() == "":
            out.pop()

    for s in secs:
        if s.id in removed:
            continue
        if s.id in modified:
            emit(modified.pop(s.id), "（MODIFIED %s）" % version)
        else:
            emit(s)

    for s in added:
        emit(s)

    out.append("")
    return "\n".join(out) + "\n", spec_path, []


def update_spec_index(root, module, sub, version, description, spec_path):
    """首次生成 spec 时在 spec/README.md 索引追加一行（源包 archive.json step 6 的要求）。"""
    idx = os.path.join(root, SPEC_DIR, "README.md")
    _, secs = split_sections(read_lines(spec_path), SPEC_H2)
    rng = ""
    if secs:
        lo, hi = min(s.id for s in secs), max(s.id for s in secs)
        rng = "，R%d" % lo if lo == hi else "，R%d-R%d" % (lo, hi)
    row = "| %s | [%s.md](%s.md) | change/%s/%s %s（%s%s） |" % (
        module, module, module, module, sub, version, description or sub, rng)

    if not os.path.exists(idx):
        with open(idx, "w", encoding="utf-8", newline="\n") as f:
            f.write("# spec 索引\n\n"
                    "> 活规格层（当前真相源）。禁止手改——唯一更新入口是 archive 的 delta 合并。\n\n"
                    "| 模块 | 规格 | 基线来源 |\n|------|------|---------|\n" + row + "\n")
        return True

    lines = read_lines(idx)
    if any(re.match(r"^\|\s*%s\s*\|" % re.escape(module), l) for l in lines):
        return False
    last_tbl = max((i for i, l in enumerate(lines) if l.startswith("|")), default=None)
    if last_tbl is None:
        lines += ["", "| 模块 | 规格 | 基线来源 |", "|------|------|---------|", row]
    else:
        lines.insert(last_tbl + 1, row)
    write_atomic(idx, "\n".join(lines) + "\n")
    return True


def cmd_merge(args):
    today = args.date or date.today().isoformat()
    if already_applied(args.root, args.module, args.version, args.subcategory):
        warn("该 delta 已合并进 spec（幂等）：无需重复合并")
        return 0
    text, spec_path, errs = build_merged(
        args.root, args.module, args.version, args.subcategory, today)
    if errs:
        for e in errs:
            fail(e)
        return 1
    if not args.apply:
        print("----- DRY RUN: 以下为合并结果（未写入） -----")
        print(text)
        print("----- 共 %d 行；加 --apply 才会写入 %s -----" % (len(text.splitlines()), spec_path))
        return 0
    write_atomic(spec_path, text)
    ok("已写入 " + spec_path + "（旧版备份为 .bak）")
    return 0


# ---------------------------------------------------------------- archive
class Lock(object):
    def __init__(self, root, module):
        self.dir = os.path.join(root, CHANGE_DIR)
        self.path = os.path.join(self.dir, LOCK_NAME)
        self.module = module
        self.held = False

    def acquire(self):
        os.makedirs(self.dir, exist_ok=True)
        if os.path.exists(self.path):
            age = datetime.now(timezone.utc).timestamp() - os.path.getmtime(self.path)
            if age < LOCK_STALE_SEC:
                warn("已存在归档锁（%.0fs 前）：%s" % (age, read(self.path).strip()))
                return False
            warn("归档锁已过期（>30min），接管")
            os.remove(self.path)
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("%s pid=%d at=%s\n" % (self.module, os.getpid(), datetime.now().isoformat()))
        self.held = True
        return True

    def release(self):
        if self.held and os.path.exists(self.path):
            os.remove(self.path)
        self.held = False


def load_json(path, default):
    if not os.path.exists(path):
        return default
    return json.loads(read(path))


def cmd_archive(args):
    root, module = args.root, args.module
    tmp_dir, spec_path, mod_ver = paths(root, module)
    sub = args.subcategory
    version = args.version
    today = args.date or date.today().isoformat()

    if not os.path.isdir(tmp_dir):
        die("找不到迭代目录: " + tmp_dir, 2)
    if not sub:
        die("归档必须指定 --subcategory", 2)
    if not version:
        die("归档必须指定 --version", 2)

    lock = Lock(root, module)
    if not lock.acquire():
        return 3

    backups = []
    moved = []
    try:
        # 1) 幂等短路：合并成功但后续步骤中断时，重跑不应被 C3 挡住
        resumed = already_applied(root, module, version, sub)
        if resumed:
            warn("检测到该 delta 已合并进 spec（幂等）：跳过校验与合并")
        else:
            rc = cmd_validate(argparse.Namespace(root=root, module=module))
            if rc != 0:
                fail("校验未通过，归档中止（未改动任何文件）")
                return rc

        dl = load_delta(tmp_dir)
        has_delta = dl is not None
        has_spec = os.path.exists(spec_path)

        # 2) 缺基线的处理：不偷偷生成假真相
        if not has_spec and not has_delta:
            fail("首次归档既无 spec 基线也无 delta。请二选一：")
            print("   (a) 产出 _tmp/07-spec-delta.md 后重试")
            print("   (b) 人工按 spec/_TEMPLATE.md 回填 spec/%s.md 后重试" % module)
            return 3

        # 3) 先合并 spec（唯一真相源的写入必须最先且可回滚）
        if has_delta and not resumed:
            text, sp, errs = build_merged(root, module, version, sub, today)
            if errs:
                for e in errs:
                    fail(e)
                return 1
            if not args.apply:
                print("----- DRY RUN: 将合并进 %s -----" % sp)
                print(text)
                print("----- 未改动任何文件；加 --apply 执行 -----")
                return 0
            if os.path.exists(sp):
                backups.append((sp, sp + ".bak"))
                shutil.copy2(sp, sp + ".bak")
            write_atomic(sp, text)
            ok("spec 已合并: " + sp)

        # 3b) 索引兜底：spec 已存在但索引缺行时补上（覆盖"合并成功但后续中断"的恢复路径）
        _sp = os.path.join(root, SPEC_DIR, module + ".md")
        if os.path.exists(_sp) and update_spec_index(
                root, module, sub, version, args.description, _sp):
            ok("spec 索引已追加: spec/README.md")

        # 4) 移动文档
        target = os.path.join(root, CHANGE_DIR, module, sub)
        os.makedirs(target, exist_ok=True)
        for name in sorted(os.listdir(tmp_dir)):
            if name.startswith("."):
                continue
            src = os.path.join(tmp_dir, name)
            dst = os.path.join(target, name)
            if os.path.exists(dst):
                backups.append((dst, dst + ".owbak"))
                shutil.copy2(dst, dst + ".owbak")
            shutil.move(src, dst)
            moved.append((src, dst))
        ok("文档已归档到 change/%s/%s/（%d 个文件）" % (module, sub, len(moved)))

        # 5) 更新索引
        # 子分类 version.json：优化迭代时必须「追加」版本记录，不能整体覆盖（否则丢历史）
        sub_ver_path = os.path.join(target, "version.json")
        old_sub = load_json(sub_ver_path, {})
        versions = old_sub.get("versions", [])
        if not any(v.get("version") == version for v in versions):
            versions.append({"version": version, "date": today,
                             "type": args.type or "minor",
                             "description": args.description or sub,
                             "status": "archived"})
        sub_ver = {
            "subCategory": sub,
            "parentModule": module,
            "currentVersion": version,
            "status": "archived",
            "description": args.description or old_sub.get("description") or sub,
            "versions": versions,
        }
        write_atomic(sub_ver_path, json.dumps(sub_ver, ensure_ascii=False, indent=2) + "\n")

        mv = load_json(mod_ver, {"module": module, "currentSubCategory": None,
                                 "status": "idle", "subCategories": {}})
        mv.setdefault("subCategories", {})[sub] = {
            "description": args.description or sub,
            "currentVersion": version,
            "status": "archived",
            "path": "change/%s/%s" % (module, sub),
        }
        mv["currentSubCategory"] = None
        mv["status"] = "idle"
        write_atomic(mod_ver, json.dumps(mv, ensure_ascii=False, indent=2) + "\n")

        gpath = os.path.join(root, CHANGE_DIR, "versions.json")
        gv = load_json(gpath, {"schemaVersion": 1, "modules": {}})
        mod_entry = gv.setdefault("modules", {}).setdefault(
            module, {"currentSubCategory": None, "status": "idle", "subCategories": {}})
        mod_entry["currentSubCategory"] = None
        mod_entry["status"] = "idle"
        mod_entry.setdefault("subCategories", {})[sub] = {
            "currentVersion": version, "status": "archived",
            "path": "change/%s/%s" % (module, sub)}
        gv["updatedAt"] = today
        write_atomic(gpath, json.dumps(gv, ensure_ascii=False, indent=2) + "\n")
        ok("索引已更新（模块 version.json + 全局 versions.json）")

        ok("归档完成: %s/%s %s" % (module, sub, version))
        return 0

    except Exception as ex:
        print("[ERROR] 归档失败，开始回滚: %s" % ex)
        for src, dst in reversed(moved):
            try:
                shutil.move(dst, src)
            except Exception:
                pass
        for orig, bak in reversed(backups):
            if os.path.exists(bak):
                try:
                    shutil.copy2(bak, orig)
                    os.remove(bak)
                except Exception:
                    pass
        print("[ERROR] 已回滚到归档前状态")
        return 2
    finally:
        lock.release()


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(prog="spec_tool.py", description="三层真相源工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--root", default=".", help="项目根（含 change/ spec/）")
        p.add_argument("--module", required=True)
        p.add_argument("--spec-dir", default="spec", help="活规格目录名（默认 spec）")
        p.add_argument("--change-dir", default="change", help="变更档案目录名（默认 change）")

    p = sub.add_parser("validate")
    common(p)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("check-spec")
    common(p)
    p.set_defaults(func=cmd_check_spec)

    p = sub.add_parser("check-modules")
    common(p)
    p.set_defaults(func=cmd_check_modules)

    p = sub.add_parser("merge")
    common(p)
    p.add_argument("--version", required=True)
    p.add_argument("--subcategory", required=True)
    p.add_argument("--date", default=None)
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_merge)

    p = sub.add_parser("archive")
    common(p)
    p.add_argument("--version", required=True)
    p.add_argument("--subcategory", required=True)
    p.add_argument("--description", default=None)
    p.add_argument("--type", default="minor", choices=["major", "minor", "patch"])
    p.add_argument("--date", default=None)
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_archive)

    args = ap.parse_args()
    args.root = os.path.abspath(args.root)

    global SPEC_DIR, CHANGE_DIR
    SPEC_DIR = args.spec_dir
    CHANGE_DIR = args.change_dir

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
