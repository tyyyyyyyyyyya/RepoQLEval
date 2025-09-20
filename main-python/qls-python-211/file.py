import os

def read_python_files(folder_path):
#def read_python_files(self, folder_path: str)-> List[Dict[str, str]]:
    """
    递归读取指定文件夹及其子文件夹下的所有 .py 文件内容。

    参数:
        folder_path (str): 要扫描的文件夹路径

    返回:
        list: 包含每个 .py 文件路径和内容的字典列表
    """
    py_files = []

    try:
        if not os.path.isdir(folder_path):
            raise ValueError(f"路径 {folder_path} 不是一个有效的文件夹")

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        py_files.append({"path": file, "content": content})
                    except Exception as e:
                        print(f"读取文件 {file_path} 失败: {e}")

        return py_files

    except Exception as e:
        print(f"读取文件夹失败: {e}")
        return []

'''
def call(self, prompt: str, model: str, use_history: bool = True, py_folder: Union[str, None] = None) -> dict:
    """调用大模型，支持系统提示词、对话历史和可选的.py文件内容"""
    endpoint = f"{self.base_url}/chat/completions"

    # 构建消息列表
    messages = []
    if self.system_prompt:
        messages.append({"role": "system", "content": self.system_prompt})
    if use_history and self.history:
        messages.extend(self.history)

    # 如果提供了文件夹路径，读取所有.py文件内容并添加到提示中
    if py_folder:
        py_files = self.read_python_files(py_folder)
        if py_files:
            # 将每个文件的路径和内容格式化为字符串
            py_content = "\n".join([f"### {file['path']}\n{file['content']}\n" for file in py_files])
            prompt = f"{prompt}\n\n以下是指定文件夹中的 Python 文件内容:\n{py_content}"

    messages.append({"role": "user", "content": prompt})

    payload = {
        'model': model,
        'messages': messages
    }

    try:
        response = requests.post(endpoint, headers=self.headers, json=payload)
        response.raise_for_status()
        response_data = response.json()

        # 提取响应内容（OpenAI 风格）
        content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '无响应内容')

        # 更新历史记录和上次对话
        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": content})
        self.prev_prompt = prompt
        self.prev_response = content

        # 如果有 prefill，添加到响应内容
        if self.prefill:
            content = self.prefill + content

        response_data['choices'][0]['message']['content'] = content
        return response_data
    except requests.exceptions.RequestException as e:
        raise Exception(f"API 调用失败: {str(e)}")
'''

if __name__ == "__main__":


    folder_path = "D:/papertest/claude"  # 替换为实际文件夹路径
    # 读取所有 .py 文件
    py_files = read_python_files(folder_path)
    print(py_files)

