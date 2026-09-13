# Chroma 向量知识库（本地）

用语义相似度补充「按类别取论据」，让措辞不同的评论也能命中相关素材。

## 一次性建库

```powershell
cd D:\大创\anyclaw
.\venv\Scripts\activate
pip install chromadb
python scripts/build_chroma_kb.py
```

首次会下载 Chroma 自带的 ONNX 模型 `all-MiniLM-L6-v2`（约 80MB）。  
若 chromadb 安装失败，脚本会自动回退为 TF-IDF，接口不变。

## 测试检索

```powershell
python scripts/test_chroma_retrieve.py
```

看返回里 `retrieval: chroma`（或 `tfidf`）是否出现。

## 如何接到智能体

`intl_comm_reply` → `retrieve_statements(..., query=comment)`：

1. Chroma 语义召回（优先同类）
2. 原类别列表补齐
3. 无向量库时自动回退为旧逻辑

向量库目录：`knowledge/diplomacy/chroma_db/`（已 gitignore）。

`evidence.json` 更新后重新执行 `build_chroma_kb.py`。
