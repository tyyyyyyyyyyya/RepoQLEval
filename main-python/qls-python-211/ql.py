import os


def read_ql_files(folder_path):
    """
    递归读取指定文件夹及其子文件夹下的所有 .ql 文件内容。

    参数:
        folder_path (str): 要扫描的文件夹路径

    返回:
        list: 包含每个 .ql 文件路径和内容的字典列表
    """
    ql_files = []

    try:
        if not os.path.isdir(folder_path):
            raise ValueError(f"路径 {folder_path} 不是一个有效的文件夹")

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.ql'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        ql_files.append({"path": file, "content": content})
                    except Exception as e:
                        print(f"读取文件 {file_path} 失败: {e}")

        return ql_files
    except Exception as e:
        print(f"读取文件夹失败: {e}")
        return []


project_dir="D:\papertest\test\cwe-78-6"
ql_position = project_dir.upper()
ql_position = ql_position[-8:-2]
ql_position = ql_position[:4] + "0" + ql_position[4:]
ql_position = os.path.join("D:\c\pythonProject2\qls-python-211", ql_position)


print(ql_position)
print(read_ql_files(ql_position))