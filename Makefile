# 运行方式
# make       生成最新一期的 PDF 和 PNG
# make 41    生成第 41 期
# make new   创建下一期

PYTHON ?= python3
POST   ?=
DPI    ?=

# 由 Python 返回纯数字期数，避免 Make 将日期前缀中的空格拆成多个目标。
POST_TARGETS := $(shell "$(PYTHON)" _scripts/build_mrg.py list)

.DEFAULT_GOAL := all
.PHONY: all pdf images all-posts new $(POST_TARGETS)

# 编译与导出
all:
	@"$(PYTHON)" _scripts/build_mrg.py build --post "$(POST)" --dpi "$(DPI)"

$(POST_TARGETS):
	@"$(PYTHON)" _scripts/build_mrg.py build --post "$@" --dpi "$(DPI)"

pdf:
	@"$(PYTHON)" _scripts/build_mrg.py pdf --post "$(POST)"

images:
	@"$(PYTHON)" _scripts/build_mrg.py images --post "$(POST)" --dpi "$(DPI)"

all-posts:
	@"$(PYTHON)" _scripts/build_mrg.py build --all --dpi "$(DPI)"

# 新建期数
new:
	@"$(PYTHON)" _scripts/build_mrg.py new --post "$(POST)"

new%:
	@"$(PYTHON)" _scripts/build_mrg.py new --post "$*"
