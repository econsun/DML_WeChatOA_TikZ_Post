"""MRG 统一入口：发现期数、编译海报与 combined 封面并导出 PNG。"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pymupdf as fitz

# 项目路径只由脚本位置推导；移动到 iCloud 后无需修改任何绝对路径。
PROJECT_DIR = Path(__file__).resolve().parents[1]
POSTS = PROJECT_DIR
OUTPUT = PROJECT_DIR / "_output" / "MRG_output"
PDF_OUTPUT = OUTPUT / "PDF"
PNG_OUTPUT = OUTPUT / "PNG"
BUILD = PROJECT_DIR / "_build" / "MRG_build"

# 日期前缀仅用于整理文件夹，期数由末尾的 MRG 数字决定。
POST_FOLDER_PATTERN = re.compile(r"^(?:\d{2} +\d{2} +\d{2} +)?MRG(?P<post>[1-9]\d*)$")
SESSION_PATTERN = re.compile(
    r"(\\(?:newcommand|renewcommand)\s*\{\s*\\SessionNumber\s*\}\s*\{)\s*([1-9]\d*)\s*\}"
)
ROOT_PATTERN = re.compile(r"^MRG(?P<post>[1-9]\d*)_(?:01_poster|02_cover)\.tex$")
RECIPE_NAME = "latexmk (XeLaTeX + SyncTeX)"
LATEXMK_FLAGS = [
    "-synctex=1",
    "-interaction=nonstopmode",
    "-file-line-error",
    "-xelatex",
    "-outdir=../_output/MRG_output/PDF",
    "-auxdir=../_build/MRG_build",
]


def post_file_name(post: str, role: str) -> str:
    """入口相邻、内容随后；文件离开目录后也能辨认期数和用途。"""
    order = {"poster": "01", "cover": "02", "content": "03", "layout": "04"}
    return f"MRG{post}_{order[role]}_{role}.tex"


def sync_workspace_settings() -> None:
    """隐藏侧栏中的根目录文件，同时保留 Go to File 和文本搜索入口。"""
    path = PROJECT_DIR / ".vscode" / "settings.json"
    if not path.is_file():
        return
    content = path.read_text(encoding="utf-8")
    settings = json.loads(content)
    excluded = settings.setdefault("files.exclude", {})
    search_excluded = settings.setdefault("search.exclude", {})
    for entry in PROJECT_DIR.iterdir():
        if entry.is_file():
            excluded[entry.name] = True
            # 搜索规则覆盖同名的侧栏规则；Finder 元数据继续排除。
            if entry.name != ".DS_Store":
                search_excluded[entry.name] = False
    updated = json.dumps(settings, ensure_ascii=False, indent=4) + "\n"
    if updated != content:
        path.write_text(updated, encoding="utf-8")


# 期数发现与输入检查
# 同一期出现两个文件夹时直接报错，避免将不同内容写进同一份成品。


def discover_posts() -> dict[str, Path]:
    available: dict[str, Path] = {}

    for folder in sorted(POSTS.iterdir()):
        match = POST_FOLDER_PATTERN.fullmatch(folder.name)
        if not folder.is_dir() or match is None:
            continue

        post = match["post"]
        if post in available:
            raise ValueError(
                f"第 {post} 期有两个文件夹：{available[post].name}、{folder.name}。"
                "请保留唯一的本期文件夹后再编译。"
            )
        available[post] = folder

    return available


def post_ids() -> list[str]:
    return sorted(discover_posts(), key=int)


def select_posts(post: str, all_posts: bool) -> list[str]:
    available = post_ids()
    if not available:
        raise ValueError("根目录中没有 MRG 期数文件夹，例如 MRG41 或 26 09 09 MRG41。")
    if all_posts:
        return available
    if post:
        if post not in available:
            raise ValueError(f"没有找到第 {post} 期文件夹。")
        return [post]
    return [available[-1]]


def post_folder(post: str) -> Path:
    available = discover_posts()
    if post not in available:
        raise ValueError(f"没有找到第 {post} 期文件夹。")
    return available[post]


def validate_post(post: str) -> Path:
    folder = post_folder(post)
    info_path = folder / post_file_name(post, "content")
    if not info_path.is_file():
        raise FileNotFoundError(
            f"缺少 {folder.name}/{info_path.name}；若在 iCloud，请先确保文件已下载。"
        )

    matches = list(SESSION_PATTERN.finditer(info_path.read_text(encoding="utf-8")))
    if len(matches) != 1 or matches[0][2] != post:
        raise ValueError(f"{folder.name}/{info_path.name} 的 SessionNumber 必须唯一定义为 {post}。")
    return folder


# 编辑器根文件与 TeX 编译
# Make 和 LaTeX Workshop 都调用这里：只把安全的相对文件名传给 TeX。


def sync_root_comments(post: str) -> None:
    """重命名日期前缀后，更新共享文件的编辑器根声明；未变化时不写文件。"""
    folder = post_folder(post)
    paths = [*(PROJECT_DIR / "_config").rglob("*.tex"), folder / post_file_name(post, "content")]
    local_layout = folder / post_file_name(post, "layout")
    if local_layout.is_file():
        paths.append(local_layout)

    for path in paths:
        is_cover = path.name in {"mrg_cover.tex", "mrg_cover_layout.tex"}
        root = folder / post_file_name(post, "cover" if is_cover else "poster")
        relative_root = Path(os.path.relpath(root, path.parent)).as_posix()
        content = path.read_text(encoding="utf-8")
        updated = re.sub(
            r"^% !TeX root = .*$",
            lambda _: f"% !TeX root = {relative_root}",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        if updated != content:
            path.write_text(updated, encoding="utf-8")


def compile_pdf(post: str, name: str) -> Path:
    folder = validate_post(post)
    source = folder / f"{name}.tex"
    if not source.is_file():
        raise FileNotFoundError(f"缺少编译入口：{folder.name}/{source.name}")

    PDF_OUTPUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    # 不通过 shell 拼接命令；先保存完整日志，再统一处理非零退出码。
    result = subprocess.run(
        ["latexmk", *LATEXMK_FLAGS, source.name],
        cwd=folder,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    log_path = BUILD / f"{name}-command.log"
    log_path.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(
            f"{name} 编译失败，详见 _build/MRG_build/{log_path.name}\n{result.stdout[-2500:]}"
        )

    for suffix in (".pdf", ".synctex.gz"):
        path = PDF_OUTPUT / f"{name}{suffix}"
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f"编译未生成有效的 {path.name}")
    return PDF_OUTPUT / f"{name}.pdf"


def editor_build(source: str, directory: str) -> None:
    """编辑器传入当前根文件所在目录，日期前缀不会进入 TeX 的命令参数。"""
    folder = Path(directory).resolve()
    match = ROOT_PATTERN.fullmatch(source)
    if match is None:
        raise ValueError("请选择本期 01_poster 或 02_cover 的 TeX 入口。")

    post = match["post"]
    if folder != post_folder(post).resolve():
        raise ValueError("编辑器根文件目录与实际期数目录不一致，请重新打开本期入口。")
    sync_root_comments(post)
    compile_pdf(post, Path(source).stem)


# PNG 导出
# 渲染前限制像素数，保存时再次检查；统一写入实际 DPI。


def safe_render_dpi(page: fitz.Page, dpi: int, max_pixels: int) -> int:
    import pymupdf as fitz

    def fits(value: int) -> bool:
        bounds = (page.rect * fitz.Matrix(value / 72, value / 72)).irect
        return bounds.width * bounds.height <= max_pixels

    if fits(dpi):
        return dpi
    if not fits(1):
        raise ValueError("页面过大，即使 1 DPI 也超过像素上限。")

    low, high = 1, dpi
    while low < high:
        middle = (low + high + 1) // 2
        if fits(middle):
            low = middle
        else:
            high = middle - 1
    return low


def render_png(pdf_path: Path, dpi: int, max_pixels: int) -> None:
    import pymupdf as fitz
    from pymupdf.utils import get_pixmap

    with fitz.open(pdf_path) as doc:
        if doc.page_count != 1:
            raise ValueError(f"{pdf_path.name} 应为单页，请检查版面。")

        page = doc[0]
        actual_dpi = safe_render_dpi(page, dpi, max_pixels)
        # 显式函数与 Page.get_pixmap 行为相同，且能被 Pylance 正确识别。
        pix = get_pixmap(page, dpi=actual_dpi, colorspace=fitz.csRGB, alpha=False)
        if pix.width * pix.height > max_pixels:
            raise RuntimeError("实际像素数超限，未保存图片。")

        PNG_OUTPUT.mkdir(parents=True, exist_ok=True)
        pix.save(PNG_OUTPUT / f"{pdf_path.stem}.png")
        adjusted = f"（由 {dpi} 自动降低）" if actual_dpi != dpi else ""
        print(f"  {pdf_path.stem}.png  {pix.width} × {pix.height}  {actual_dpi} DPI{adjusted}")


# 新建期数
# 只复制内容与轻量编译入口，不复制共享配置、素材、缓存或成品。


def root_document(template: str, post: str) -> str:
    return (
        f"% !TeX LW recipe = {RECIPE_NAME}\n\n"
        "\\documentclass[border=0pt]{standalone}\n"
        f"\\newcommand{{\\PostNumber}}{{{post}}}\n\n"
        "\\input{../_config/mrg_preamble.tex}\n"
        f"\\input{{../_config/templates/mrg_{template}.tex}}\n"
    )


def new_post(post: str) -> None:
    if not post:
        post = str(int(select_posts("", False)[0]) + 1)
    if not re.fullmatch(r"[1-9]\d*", post):
        raise ValueError("新期数必须是正整数，例如 make new42；make new 自动创建下一期。")
    if post in discover_posts():
        raise ValueError(f"第 {post} 期已存在，不会覆盖，包括带日期前缀的文件夹。")

    source_post = select_posts("", False)[0]
    source = validate_post(source_post)
    info = (source / post_file_name(source_post, "content")).read_text(encoding="utf-8")
    info = re.sub(
        r"^% !TeX root = .*$",
        f"% !TeX root = {post_file_name(post, 'poster')}",
        info,
        count=1,
        flags=re.MULTILINE,
    )
    info, count = SESSION_PATTERN.subn(lambda match: match[1] + post + "}", info)
    if count != 1:
        raise ValueError("原期数的 SessionNumber 定义不唯一，无法创建新期。")

    target = POSTS / f"MRG{post}"
    target.mkdir()
    (target / post_file_name(post, "content")).write_text(info, encoding="utf-8")
    for template in ("poster", "cover"):
        (target / post_file_name(post, template)).write_text(
            root_document(template, post), encoding="utf-8"
        )
    print(
        f"已创建 {target.name}/；其余内容沿用 {source.name}，请编辑本期 03_content.tex 文件后编译。"
    )


# 命令分发
# make / make 41 / make new 是日常入口；editor 和 list 供工具调用。


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "pdf", "images", "new", "list", "editor"])
    parser.add_argument("--post", default="", help="期数；留空选择数字最大的期数")
    parser.add_argument("--all", action="store_true", help="构建所有期数")
    parser.add_argument("--dpi", default="", help="临时覆盖 _config/mrg_export.toml 中的 DPI")
    parser.add_argument("--source", default="", help="编辑器当前编译入口的相对文件名")
    parser.add_argument("--directory", default="", help="编辑器当前根文件所在目录")
    args = parser.parse_args()
    sync_workspace_settings()

    if args.action == "list":
        print(" ".join(post_ids()))
        return
    if args.action == "new":
        new_post(args.post)
        return
    if args.action == "editor":
        editor_build(args.source, args.directory)
        return

    settings = tomllib.loads((PROJECT_DIR / "_config/mrg_export.toml").read_text(encoding="utf-8"))
    dpi = int(args.dpi or settings["dpi"])
    max_pixels = int(settings["max_pixels"])
    if dpi <= 0 or max_pixels <= 0:
        raise ValueError("dpi 和 max_pixels 必须为正整数。")

    for post in select_posts(args.post, args.all):
        folder = validate_post(post)
        print(f"构建第 {post} 期：{folder.name}")
        sync_root_comments(post)
        poster = compile_pdf(post, Path(post_file_name(post, "poster")).stem)
        combined = compile_pdf(post, Path(post_file_name(post, "cover")).stem)
        pdfs = [poster, combined]

        if args.action != "pdf":
            for pdf in pdfs:
                render_png(pdf, dpi, max_pixels)
        print("  成品已更新至 _output/MRG_output/ 下的 PDF 与 PNG 文件夹。")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, ImportError) as exc:
        sys.exit(f"构建失败：{exc}")
