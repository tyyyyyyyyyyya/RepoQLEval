import requests
import json


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
            raise Exception(f"API 调用失败: {str(e)}")


import json


# 读取 JSON 文件
def read_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 未找到")
        return None
    except json.JSONDecodeError:
        print("错误：JSON 格式无效")
        return None


# 构造 prompt
def create_prompt(json_data, json_data2,prompts):
    if json_data is None:
        return None

    # 将 JSON 数据转换为字符串，嵌入 prompt
    prompt = f"""{prompts}:
    以下为第一个文件（每个项目的错误标签）
{json.dumps(json_data, ensure_ascii=False, indent=2)}
    以下为第二个文件（codeql检测结果）
{json.dumps(json_data2, ensure_ascii=False, indent=2)}
"""
    return prompt
def main():
    """主函数，展示 LLMApiClient 的使用"""
    # 初始化客户端
    base_url = "https://flag.smarttrot.com/v1"  # 第三方api网址
    api_key = ""  # 替换为实际的 API 密钥
    client = LLMApiClient(base_url, api_key)

    file_path=""#替换为
    file_path2=""

    # 测试模型调用
    prompt = "以下有两个文件，其中一个文件是项目名称与其对应的cwe漏洞所在位置（真标签），一个是codeql语句运行生成结果，比较两个文件中共有的项目。需要输出每个项目的查准率（查准的文件数/查到的文件数）召回率（查准的文件数/实际漏洞数）以及F1值，并输出平均的查准率、查全率和F1值(保留小数点后四位)"
    models = ["grok-3"]   #也可换为其他分析能力更强的模型
    json_data = read_json_file(file_path)
    json_data2=read_json_file(file_path2)

    # 构造 prompt
    prompt = create_prompt(json_data,json_data2, prompt)
    print(prompt)



    for model in models:
        try:
            print(f"\n调用模型: {model}")
            response = client.call(prompt, model=model)
            # 提取内容
            #print("this is resonse data:/n")
            #print(response)
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '无响应内容')

            print(f" {content}")
        except Exception as e:
            print(f"调用 {model} 失败: {str(e)}")


if __name__ == "__main__":
    main()



