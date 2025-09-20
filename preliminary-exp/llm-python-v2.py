import os
import requests
import tiktoken
from typing import List, Dict
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加 FileHandler 将日志输出到文件
file_handler = logging.FileHandler('python.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

class LLMApiClient:
    def __init__(self, base_url: str, api_key: str):
        """初始化客户端"""
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def call(self, prompt: str, model: str) -> dict:
        """调用大模型"""
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}]
        }

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API 调用失败: {str(e)}")
            raise

    def read_python_files(self, folder_path: str) -> List[Dict[str, str]]:
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
                            py_files.append({"path": file_path, "content": content})
                        except Exception as e:
                            logger.error(f"跳过文件 {file_path}，读取失败: {str(e)}")
        except Exception as e:
            logger.error(f"处理文件夹 {folder_path} 失败: {str(e)}")

        return py_files


def truncate_content(py_files: List[Dict[str, str]], max_tokens: int, encoding, skip_levels: int) -> tuple[str, List[str]]:
    """
    截断内容以满足最大 token 限制，按文件大小从小到大移除文件。

    参数:
        py_files: 包含文件路径和内容的字典列表
        max_tokens: 最大 token 数限制
        encoding: tiktoken 编码器
        skip_levels: 路径截断的层级数

    返回:
        tuple: (截断后的内容字符串, 被移除的文件名列表)
    """
    sorted_files = sorted(py_files, key=lambda x: len(x['content']))
    concatenated_content = ""
    removed_files = []
    current_tokens = 0

    for py_file in sorted_files:
        file_name = os.path.basename(py_file['path'])
        path_parts = py_file['path'].split(os.sep)
        if len(path_parts) > skip_levels:
            relative_path = os.sep.join(path_parts[skip_levels:])
        else:
            relative_path = file_name
        file_content = f"\nfile: {relative_path}\ncontent:\n{py_file['content']}\n"
        try:
            file_tokens = len(encoding.encode(file_content, allowed_special="all"))
            if current_tokens + file_tokens <= max_tokens:
                concatenated_content += file_content
                current_tokens += file_tokens
            else:
                removed_files.append(file_name)
        except Exception as e:
            logger.error(f"跳过文件 {file_name}，token 编码失败: {str(e)}")
            removed_files.append(file_name)

    return concatenated_content, removed_files


def main():
    """主函数，展示 LLMApiClient 的使用"""
    # 初始化客户端
    base_url = "https://flag.smarttrot.com/v1"   #第三方api网址
    api_key = ""  # 替换为实际的 API 密钥
    client = LLMApiClient(base_url, api_key)

    # 定义 system_prompt
    system_prompt = "You are a code analysis assistant. Please analyze the content of the following files to determine if there are any CWE vulnerabilities present. If vulnerabilities exist, provide the CWE number and list all file names containing CWE vulnerabilities. Only list the file names with vulnerabilities and the CWE number, without outputting any related analysis or detailed information."

    # 大模型及其上下文窗口 token 数
    large_models = [
        {"name": "claude-3-haiku-20240307", "context_window_tokens": 200000},
        {"name": "gpt-4o", "context_window_tokens": 128000},
        {"name": "grok-3", "context_window_tokens": 128000},
        {"name": "qwen3-32b", "context_window_tokens": 256000},
        {"name": "llama3-8b-instruct", "context_window_tokens": 8000},
        {"name": "deepseek-reasoner", "context_window_tokens": 98304},
        {"name": "qwen3-coder-plus", "context_window_tokens": 1048576}
    ]

    models = ["grok-3"]  # 可替换为其他模型，也可以进行扩展
    skip_levels = 3  # 定义路径截断层级,此参数是为了节省token数，让大模型更好的接受项目


    folder_path = "D:/yml/python_test"  # 替换为实际的项目根文件夹路径

    encoding = tiktoken.get_encoding("cl100k_base")

    try:
        # 获取根文件夹下的所有子文件夹
        subdirs = next(os.walk(folder_path))[1]

        if not subdirs:
            logger.warning(f"根文件夹 {folder_path} 下没有子文件夹")
            return



        for subdir in subdirs:

            subdir_path = os.path.join(folder_path, subdir)
            logger.info(f"处理项目: {subdir_path}")

            # 读取子文件夹中的所有 .py 文件
            py_files = client.read_python_files(subdir_path)

            if not py_files:
                logger.warning(f"项目 {subdir_path} 中没有 .py 文件")
                continue

            # 初始拼接内容
            prompt_content = system_prompt
            for py_file in py_files:
                path_parts = py_file['path'].split(os.sep)
                if len(path_parts) > skip_levels:
                    relative_path = os.sep.join(path_parts[skip_levels:])
                else:
                    relative_path = os.path.basename(py_file['path'])
                prompt_content += f"\nfile: {relative_path}\ncontent:\n{py_file['content']}\n"

            # 计算初始 tokens
            try:
                current_tokens = len(encoding.encode(prompt_content, allowed_special="all"))
            except Exception as e:
                logger.error(f"初始内容 token 编码失败: {str(e)}")
                continue

            py_files_current = py_files.copy()

            for model in models:
                total_removed_files = 0  # 初始化总移除文件计数器
                # 获取模型的 max_tokens
                max_tokens = None
                for model_info in large_models:
                    if model_info["name"] == model:
                        max_tokens = model_info["context_window_tokens"]
                        break
                if max_tokens is None:
                    logger.warning(f"模型 {model} 未在 large_models 中找到，跳过")
                    continue

                current_max_tokens = max_tokens
                prompt_content_current = prompt_content
                py_files_current = py_files.copy()
                try:
                    current_tokens = len(encoding.encode(prompt_content_current, allowed_special="all"))
                except Exception as e:
                    logger.error(f"内容 token 编码失败: {str(e)}")
                    continue

                # 先粗略检查并截断如果超过
                if current_tokens > current_max_tokens:
                    logger.info(f"初始 tokens ({current_tokens}) 超过 {model} 限制 ({current_max_tokens})，进行截断")
                    system_tokens = len(encoding.encode(system_prompt, allowed_special="all"))
                    concatenated_content, removed_files = truncate_content(py_files_current, current_max_tokens - system_tokens, encoding, skip_levels)
                    prompt_content_current = system_prompt + concatenated_content
                    try:
                        current_tokens = len(encoding.encode(prompt_content_current, allowed_special="all"))
                    except Exception as e:
                        logger.error(f"截断后内容 token 编码失败: {str(e)}")
                        continue
                    total_removed_files += len(removed_files)  # 更新总移除文件计数
                    logger.info(f"移除文件: {removed_files}")
                    logger.info(f"截断后 tokens: {current_tokens}")

                    removed_set = set(removed_files)
                    py_files_current = [f for f in py_files_current if os.path.basename(f['path']) not in removed_set]

                success = False
                while not success and py_files_current:
                    try:
                        logger.info(f"调用模型: {model}")
                        response = client.call(prompt_content_current, model=model)

                        if 'error' in response:
                            logger.warning(f"Token 限制仍超过，继续截断 (当前 tokens: {current_tokens})")
                            current_max_tokens = int(current_max_tokens * 0.9)  # 逐步减少限制
                            if current_max_tokens < 1000:
                                logger.error("无法进一步截断，已达到最小限制")
                                break

                            system_tokens = len(encoding.encode(system_prompt, allowed_special="all"))
                            logger.info(f"当前 max tokens: {current_max_tokens}, 文件可用: {current_max_tokens - system_tokens}")
                            concatenated_content, removed_files = truncate_content(py_files_current, current_max_tokens - system_tokens, encoding, skip_levels)
                            prompt_content_current = system_prompt + concatenated_content
                            try:
                                current_tokens = len(encoding.encode(prompt_content_current, allowed_special="all"))
                            except Exception as e:
                                logger.error(f"截断后内容 token 编码失败: {str(e)}")
                                break
                            total_removed_files += len(removed_files)  # 更新总移除文件计数
                            logger.info(f"移除文件: {removed_files}")
                            logger.info(f"截断后 tokens: {current_tokens}")

                            removed_set = set(removed_files)
                            py_files_current = [f for f in py_files_current if os.path.basename(f['path']) not in removed_set]
                            continue

                        content = response.get('choices', [{}])[0].get('message', {}).get('content', '无响应内容')
                        logger.info(f"模型 {model} 返回: {content}")
                        if total_removed_files == 0:
                            logger.info(f"项目 {subdir_path} 处理完成，总移除文件数:0")
                        else:
                            logger.info(f"项目 {subdir_path} 处理完成，总移除文件数: {total_removed_files}")
                        success = True

                    except Exception as e:
                        logger.error(f"调用 {model} 失败: {str(e)}")
                        break
    except Exception as e:
        logger.error(f"处理文件夹失败: {str(e)}")


if __name__ == "__main__":
    main()