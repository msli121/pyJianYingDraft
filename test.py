# 导入模块
import os
import pyJianYingDraft as draft


jy_draft_dir = os.path.join("D:\\Documents\\JianYingData\\JianyingPro Drafts")
draft_folder = draft.Draft_folder(jy_draft_dir)  # 一般形如 ".../JianyingPro Drafts"
script = draft_folder.load_template("草稿名称")
script.inspect_material()
