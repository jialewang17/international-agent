# story_kb_github — 可上传 GitHub 的故事素材

本目录是**干净上传版**。个人浏览用的 `.url` 备份已隔离到仓库外：

`D:\大创\本地备份_讲好中国故事素材_勿上传GitHub\`

## 上传建议（fork: luhao626/international-agent）

上传到仓库路径：

```
knowledge/diplomacy/story_kb_github/
knowledge/diplomacy/evidence.json
```

可用网页 Upload，或：

```powershell
cd <你的 international-agent clone>
# 复制本目录内容后
git add knowledge/diplomacy/story_kb_github knowledge/diplomacy/evidence.json
git commit -m "Add China storytelling evidence packs (official + overseas influencers)"
git push
```

## 结构

- `packs/` — 3 个采集包
- `by_category/` — food / culture / language / …
- `by_source_tier/` — 官方媒体 / 国际组织 / 海外生活媒体 / 洋网红报道 / 个人站
- `CATALOG.md` — 全量链接目录

## 入库

```powershell
python knowledge/diplomacy/story_materials/merge_into_evidence.py
```

（脚本会读取同级的 `story_evidence_v*.json`；上传版 `packs/` 与其内容一致。）

合计条目：**51**
