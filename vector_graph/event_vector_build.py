import pandas as pd
import jieba
import chromadb
from chromadb.utils import embedding_functions

# 1. 初始化向量数据库
client = chromadb.PersistentClient(path="./chroma_db")
# 使用默认开源文本嵌入模型
embedding_func = embedding_functions.DefaultEmbeddingFunction()
# 创建集合，集合名自定义
collection = client.get_or_create_collection(
    name="event_collection",
    embedding_function=embedding_func
)

# 文本分词清洗函数
def text_cut(text):
    if not isinstance(text, str):
        text = str(text)
    words = jieba.lcut(text)
    return " ".join(words)

if __name__ == "__main__":
    try:
        print("开始加载Excel数据...")
        file_path = 'dispute_events.xlsx'
        df = pd.read_excel(file_path)
        total_row = len(df)
        print(f"数据加载完成，表格一共 {total_row} 行")

        # 准备入库容器
        ids_list = []
        docs_list = []
        meta_list = []

        print("开始文本分词预处理...")
        for idx, row in df.iterrows():
            # 整行内容拼接为一条文档
            raw_text = " ".join([str(item) for item in row.values])
            cut_text = text_cut(raw_text)

            ids_list.append(f"event_{idx}")
            docs_list.append(cut_text)
            meta_list.append({"row_index": idx})

        print("开始生成向量并写入Chroma向量库...")
        collection.add(
            ids=ids_list,
            documents=docs_list,
            metadatas=meta_list
        )

        count = collection.count()
        print(f"入库完成！向量库当前存量：{count} 条")

        # 查看库总量、集合信息
        print(f"\n【集合基础信息查看】")
        print(f"集合名称：{collection.name}")
        print(f"当前向量总条数：{collection.count()}")
        preview = collection.peek(5)
        print(f"\n前5条入库文本预览：")
        for index, doc in enumerate(preview["documents"]):
            print(f"{index+1}. {doc}")

        print("脚本运行结束")

    except Exception as e:
        print(f"运行出错，错误详情: {e}")