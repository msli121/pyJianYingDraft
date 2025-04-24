import os

import pyJianYingDraft as draft


jy_draft_dir = os.path.join("D:\\Documents\\JianYingData\\JianyingPro Drafts")
template_name = "好人好事模板1"
draft_folder = draft.Draft_folder(jy_draft_dir)  # 一般形如 ".../JianyingPro Drafts"
script = draft_folder.load_template("好人好事")

draft_folder = draft.Draft_folder(jy_draft_dir)  # 一般形如 ".../JianyingPro Drafts"
script = draft_folder.duplicate_as_template("模板草稿", "新草稿")  # 复制"模板草稿"，并命名为"新草稿"，同时打开新草稿供编辑

# 对返回的Script_file对象进行编辑，如替换素材、添加轨道、片段等

script.save()  # 保存你的"新草稿"