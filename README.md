# DeepMacro Lab · Macro Reading Group

本期内容、排版与导出各有一处来源。每期文件夹直接放在根目录；公共目录以 `_` 开头，`.git`、`.vscode` 等工具规定的目录名保留原样。

```sh
make       # 生成最新一期的海报与 combined 封面
make 41    # 生成第 41 期
make new   # 创建下一期
```

## 项目结构

```text
_config/
    mrg_brand.tex            组织名称、标签、颜色、全文字距与词距
    mrg_fields.tex           成组填写信息的两参数命令
    mrg_poster_layout.tex    海报字号、模块留白和活动区间距
    mrg_cover_layout.tex     封面字号、比例和安全距离
    mrg_export.toml          导出 DPI 与像素上限
    mrg_preamble.tex         公共加载顺序与字体设置
    templates/
        mrg_poster.tex       海报 TikZ 模板
        mrg_cover.tex        combined 封面 TikZ 模板
    assets/                  唯一一份字体、校徽与 Lab 标识
_scripts/
    build_mrg.py             MRG 构建与图片导出程序
_tests/
    test_mrg_build.py        目录、命名和编辑器设置回归测试
MRG41/
    MRG41_01_poster.tex      海报入口
    MRG41_02_cover.tex       combined 封面入口
    MRG41_03_content.tex     本期内容
_output/
    MRG_output/
        PDF/                 海报与 combined 封面的 PDF
        PNG/                 对应的两张 PNG
_build/
    MRG_build/               TeX 编译缓存与日志
Makefile                     简单命令入口
README.md                    本说明
```

每个本期文件名都包含期数、排序号和用途。两个入口排在一起，内容文件排在它们后面。将来有其他公众号栏目，可在 `_output/` 下增加独立的栏目输出目录，不与 `MRG_output/` 混放。

## 日常编辑

打开 `MRG41/MRG41_03_content.tex` 填写本期论文与活动内容；海报和封面共同调用它。相关字段可一起填写：

```tex
\Publication{2026}{The Review of Economic Studies}
\Presenter{Yifan Liu}{Xiamen University}
\EventDay{09 Sep 2026}{Wed}
\newcommand{\EventTime}{12:30–13:30}
\Location{Economics Bldg}{A117}
\OnlineMeeting{Tencent Meeting}{518-7453-0980}
```

主标题 `PaperTitle`、副标题 `PaperSubtitle` 保持分开。作者使用 `\AddPaperAuthor{姓名}{单位}`，按输入顺序编号；1–2 位纵排，3 位及以上每行两位。成组命令内部仍使用 `PresenterName`、`PresenterAffiliation`、`PaperYear`、`PaperJournal` 等原有宏名，模板无需迁移这些字段。

标题中的 `\\` 用于海报换行，封面会将其当作空格。摘要源码可以自然换行；标题和 TikZ 测量盒子中用于抑制多余空格的行尾 `%` 应保留。

## 调整排版与导出

全文字距和词距在 `_config/mrg_brand.tex`；海报字号与距离在 `mrg_poster_layout.tex`；封面设置在 `mrg_cover_layout.tex`。`CoverJoinSafety` 控制接缝两侧各自的安全延展，当前为每侧 3 mm，以 100 mm 高母版计；`CoverFooterGap` 控制底部活动信息组间距。

仅生成海报和 combined 封面，不生成 wide、square 的 PDF 或 PNG。第 41 期成品为：

```text
_output/MRG_output/PDF/MRG41_01_poster.pdf
_output/MRG_output/PDF/MRG41_02_cover.pdf
_output/MRG_output/PNG/MRG41_01_poster.png
_output/MRG_output/PNG/MRG41_02_cover.png
```

PDF 旁保留 `.synctex.gz`，用于源码与预览双向定位，在 VS Code 文件树中隐藏。图片默认 250 DPI，最高 600 万像素；设置位于 `_config/mrg_export.toml`。超限时自动降低实际 DPI，并写入 PNG 分辨率信息。重复构建更新同名文件，不产生不同 DPI 后缀的副本。

某一期需要局部排版时，在该期增加 `MRG41_04_layout.tex`，无需复制整套配置：

```tex
% !TeX root = MRG41_01_poster.tex
\renewcommand{\CoverTitleSize}{34}
\setlength{\ContentGap}{4mm}
```

## 文件夹改名与新增期数

支持 `MRG41`、`26 09 09 MRG41` 等目录名。日期前缀采用 `YY MM DD ` 格式，可增加、删除或修改；仍使用 `make 41`，里面的文件名不需要跟着日期变化。期数由末尾 `MRG` 后的数字决定，必须与内容文件中的 `SessionNumber` 一致。

`make` 选择数字最大的期数，`make all-posts` 更新全部期数，`make pdf` 只更新 PDF。同一期出现两个文件夹时会明确报错，不会任选一份覆盖成品。构建会更新共享配置的根文件声明，避免日期前缀变化后仍引用旧目录。

`make new` 创建下一期，`make new42` 指定创建第 42 期。只复制内容并生成本期三个文件，不复制素材、配置或成品。其他内容先沿用上一期，编辑新一期的 `MRG42_03_content.tex` 后再运行 `make`。已有期数不会被覆盖。

## VS Code 与缩进

本工作区默认使用 4 空格缩进，关闭自动识别缩进，避免旧文件的 2 空格设置覆盖默认值；Makefile 命令仍使用 Tab。`.editorconfig` 和 `pyproject.toml` 保存统一格式规则。

`.vscode/settings.json` 隐藏根目录的全部文件，保留期数文件夹与公共配置、输出目录；编译缓存、Python 缓存和 SyncTeX 文件也隐藏。这里只改变文件树显示，不移动或删除文件。新增根目录文件后，再运行一次 `make` 会自动将其加入隐藏清单。配套的 `search.exclude: false` 规则覆盖搜索中的同名排除项，因此隐藏的 README、Makefile 等仍可通过 Go to File（⌘P）和文本搜索找到；Finder 元数据继续排除。

LaTeX Workshop 与 Make 共用 `_scripts/build_mrg.py`。编辑器从本期入口的所在目录编译，PDF 与 SyncTeX 均在 `_output/MRG_output/PDF/`；`MRG41_03_content.tex` 的根声明默认指向海报入口。编辑器只更新当前 PDF，运行 `make` 才会同时更新两张图片。

## iCloud 路径兼容

整个项目未来可以移动到 iCloud，不需要修改绝对路径。程序从脚本位置推导项目根目录，以本期文件夹为工作目录，只将相对入口和相对输出路径传给 XeLaTeX。空格、`~`、`#`、`%` 等父目录字符不会被当作 TeX 命令解释；子进程也不经过 shell 拼接。

进入带空格的项目目录时，使用 `cd "/完整路径/项目"`，然后执行 `make`。文件需要已下载并在本机可读。本项目尚未迁移到 iCloud，目前仍在原工作目录维护。

## 环境与检查

需要 Python 3.11+、PyMuPDF、TeX Live 的 XeLaTeX、latexmk、standalone、fontspec、TikZ、graphicx、hyperref。Python 依赖可通过 `python3 -m pip install -r requirements.txt` 安装，Outfit 字体与许可已附带。

```sh
python3 -m unittest discover -s _tests
ruff check .
ruff format --check .
```

`.gitignore` 排除 `_output/`、`_build/`、Python 缓存、编辑器临时文件及 iCloud 占位文件，保留共享 VS Code 配置和素材 PDF。

## 内容来源

论文信息依据 [Oxford Academic](https://academic.oup.com/restud/advance-article/doi/10.1093/restud/rdag047/8688845)，关键词依据 [CEPR DP16980](https://cepr.org/publications/dp16980)。摘要为原文的精简改写，活动信息与标识由用户提供。
