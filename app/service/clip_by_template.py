import pyJianYingDraft as draft

def test():
    # 一般形如 ".../JianyingPro Drafts"
    draft_folder_path = ""
    draft_folder = draft.DraftFolder(draft_folder_path)
    script = draft_folder.duplicate_as_template("开头三个核心", "AUTO开头三个核心")  # 复制"模板草稿"，并命名为"新草稿"，同时打开新草稿供编辑

    # 提取草稿素材元数据
    script.inspect_material()

    # 对返回的ScriptFile对象进行编辑，如替换素材、添加轨道、片段等

    script.save()  # 保存你的"新草稿"

if __name__ == '__main__':
    test()