# DML_WeChatOA_TikZ_Poster

这是用于存放 DeepMacro Lab 微信公众号推文的仓库。目前仅有 MRG 内容，使用 TikZ 为其制作活动海报、推文封面。

# 项目结构

```text
_assets/                  项目材料

_config/
    templates/
        mrg_poster.tex       TikZ 海报主项目
        mrg_cover.tex        TikZ 封面主项目

    mrg_brand.tex            其他设置
    mrg_macros.tex           宏集
    mrg_poster_layout.tex    海报排版配置
    mrg_cover_layout.tex     封面排版配置
    mrg_export.toml          导出图片配置
    mrg_preamble.tex         总配置文件

_scripts/
    build_mrg.py             编译 PDF 并导出 PNG

MRGxx/
    MRGxx_01_poster.tex      海报入口
    MRGxx_02_cover.tex       combined 封面入口
    MRGxx_03_content.tex     本期内容

_output/
    MRG_output/
        PDF/                 海报与 combined 封面的 PDF
        PNG/                 对应的两张 PNG
```

# 使用方式

请先确保设备中有：本项目、makefile、以及 xeLaTeX 环境。

- 终端执行 `make new[number]` 创建新的 MRG 项目
- 找到文件 `MRGxx_03_content` 并修改其中信息
- 终端执行 `make [number]` 编译项目并获得 PNG 图片
- 在 `_output/MRG_output/PNG/` 中找到对应的图片
- 本期素材制作完成

# 注意事项

公众号未来还有其他栏目出现，本项目待拓展；拓展后项目结构变更导致 `make` 命令需随之修改。