import requests
from typing import List, Dict, Union
import logging
import os
from resultdemo import cmdresults
import json


# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# 添加 FileHandler 将日志输出到文件
file_handler = logging.FileHandler('claude-c.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log.addHandler(file_handler)

#调用大模型接口的类
class LLMApiClient:
    def __init__(self, base_url: str, api_key: str, system_prompt: str = ""):
        """初始化客户端"""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.system_prompt = system_prompt
        self.history: List[Dict[str, str]] = []
        self.prev_prompt: Union[str, None] = None
        self.prev_response: Union[str, None] = None
        self.prefill: Union[str, None] = None



    def read_cpp_files(self, folder_path: str) -> List[Dict[str, str]]:
        """
        递归读取指定文件夹及其子文件夹下的所有c/cpp文件内容。

        参数:
            folder_path (str): 要扫描的文件夹路径

        返回:
            list: 包含每个c/cpp文件路径和内容的字典列表
        """
        cpp_files = []

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
                            cpp_files.append({"path": file, "content": content})
                        except Exception as e:
                            print(f"读取文件 {file_path} 失败: {e}")

            return cpp_files

        except Exception as e:
            print(f"读取文件夹失败: {e}")
            return []

    #加入读ql文件的函数
    def read_ql_files(self, folder_path: str) -> List[Dict[str, str]]:
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

    def call(self, prompt: str, model: str, use_history: bool = True, cpp_folder: Union[str, None] = None,
             ql_folder: Union[str, None] = None) -> dict:
        """调用大模型，支持系统提示词和对话历史以及所有py文件内容"""
        endpoint = f"{self.base_url}/chat/completions"

        # 构建消息列表
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        if use_history and self.history:
            messages.extend(self.history)


        if ql_folder:
            ql_files = self.read_ql_files(ql_folder)
            if ql_files:
                ql_content = "\n".join([f"### {file['path']}\n{file['content']}\n" for file in ql_files])
                prompt = f"{prompt}\nThe following is the content of the QL file from the official query file, optimized based on this:\n{ql_content}"

        if cpp_folder:
            cpp_files = self.read_cpp_files(cpp_folder)
            if cpp_files:
                # 将每个文件的路径和内容格式化为字符串
                py_content = "\n".join([f"### {file['path']}\n{file['content']}\n" for file in cpp_files])
                prompt = f"{prompt}\nThe following are the contents of all c/cpp files in this project：\n{py_content}"  # 在原有prompt基础上加入了全部的c/cpp文件内容
                #print(f"这是{prompt}/n")
                #效果显著，在测试中第二次生成就成功了

        #print(prompt)
        messages.append({"role": "user", "content": prompt})


        payload = {
            'model': model,
            'messages': messages
        }

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()  # 检查 HTTP 状态码
            response_data = response.json()

            # 检查是否有 error 字段
            if 'error' in response_data:
                log.info("检测到错误，可能 token 总数已超过限制，舍弃历史记录")
                # 清空消息列表，保留系统提示和用户提示
                messages = []
                if self.system_prompt:
                    messages.append({"role": "system", "content": self.system_prompt})
                messages.append({"role": "user", "content": prompt})
                payload = {
                    'model': model,
                    'messages': messages
                }
                # 重试请求
                response = requests.post(endpoint, headers=self.headers, json=payload)
                response.raise_for_status()
                response_data = response.json()


            # 第二次检查：去掉历史记录后，确认是否有 error
            if 'error' in response_data:
                log.error(f"去掉历史记录后仍出错：{response_data['error']['message']}")
                client.prev_response=None
                #raise RuntimeError(f"API 请求重试后失败：{response_data['error']['message']}")
                return
            # 提取响应内容
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '无响应内容')
            #print(response_data)
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

    def clear_history(self):
        """清空对话历史"""
        self.history = []
        self.prev_prompt = None
        self.prev_response = None

    def set_prefill(self, prefill: Union[str, None]):
        """设置响应前缀"""
        self.prefill = prefill



#进行指定文件夹codeql生成、保存和运行查询的函数
def process(root_dir,subdir, prompt):
    project_dir = os.path.join(root_dir, subdir)
    log.info(f"处理项目文件夹: {project_dir}")
# 1. 生成 QL 查询
    try:
        log.info(f"生成 QL 查询 for {project_dir}")

        ql_position = project_dir.upper()
        #print(ql_position)
        ql_position = ql_position[-8:-2]
        #print(ql_position)
        ql_position = ql_position[-3:]
        #print(ql_position)
        #print(ql_position)
        '''if '-' in ql_position:
            ql_position = "CWE-0" + ql_position[-2:]
            print(ql_position)
            #print(ql_position)
        '''
        if '-' in ql_position:
            # 去掉 '-'
            ql_position = ql_position.replace('-', '')
            # 在字符串的最前面加上 '0'
            ql_position = "CWE-0" + ql_position
            #print(ql_position)
        else:
            ql_position = "CWE-"+ql_position
        ql_position = os.path.join("C:/Users/86183/Desktop/codeql-cpp/qls-cpp-211", ql_position)

        client.call(prompt, model="claude-3-haiku-20240307", use_history=True, cpp_folder=project_dir,
                    ql_folder=ql_position)

        ql_code=client.prev_response
        #print(f"调用call方法后结果{ql_code}")、
        if ql_code==None:
            return
        #ql_code=ql_code[5:-3]
        #提取ql语句并写入
        start_marker = "ql'''"
        end_marker = "'''"

        start_index = ql_code.find(start_marker) + len(start_marker)
        end_index = ql_code.find(end_marker, start_index)

        ql_code = ql_code[start_index:end_index]


        ql_file = os.path.join(project_dir, "test.ql")
        with open(ql_file, 'w', encoding='utf-8') as f:
            f.write(ql_code)
        log.info(f"QL 查询已保存到: {ql_file}")

    except Exception as e:
        log.error(f"生成 QL 查询时发生未知错误 for {project_dir}: {str(e)}", exc_info=e)


# 2. 运行 CodeQL 并保存输出
    try:
        log.info(f"正在运行生成的QL 查询...")
        command = f"codeql query run --database=test-db {ql_file}"
        cmdresults.run_and_save_commands(project_dir, command, subdir)
        log.info(f"本次生成的查询结果已保存")
    except Exception as e:
        log.error(f"运行 CodeQL 失败 for {project_dir}: {str(e)}")




#检查输出结果是否有误（编写的codeql语句是否有误）的函数
def check_file_for_error(file_path, file_name):
    try:
        with open(f"{file_path}/{file_name}", 'r') as file:
            content = file.read()
            return "ERROR:" not in content
    except UnicodeDecodeError:
            print("输出内容中含有中文，本次生成不成功")
            return False


def get_errors_content(folder_path, file_name):
    """
    从指定文件夹中的特定 .txt 文件中提取 '--- Errors ---' 以下的内容。

    参数:
        folder_path (str): 文件夹路径
        file_name (str): 目标文件名（包含 .txt 后缀）

    返回:
        str: '--- Errors ---' 以下的内容，如果未找到则返回空字符串
    """

    # 构建完整的文件路径
    file_path = os.path.join(folder_path, file_name)
    # 检查文件是否存在且是 .txt 文件
    if not os.path.isfile(file_path) or not file_name.endswith('.txt'):
        return f"Error: {file_name} 不存在或不是 .txt 文件"

    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

     # 查找 '--- Errors ---' 的位置
    marker = "--- Errors ---"
    if marker not in content:
        return "未找到 '--- Errors ---' 标记"

        # 返回标记后的内容
    return content[content.index(marker) + len(marker):].strip()


base_url = "https://flag.smarttrot.com/v1"  # 第三方api网址
api_key = ""  # 替换为实际的 API 密钥


system_prompt = "You are a CodeQL expert, proficient in CodeQL version 2.11.0, with the corresponding c/cpp library version 0.4.0. Your goal is to provide CodeQL statements, so only output the QL statements that would be written in a .ql file, without any additional prompts. Ensure the outputted CodeQL statements can be directly saved as a .ql file and run without issues. The output format is as follows: start with ql''' and end with ''', with only CodeQL statements in between."



client = LLMApiClient(base_url, api_key, system_prompt)


def main():

    unable=[]
    root_dir = ""   #替换为实际的项目所在目录
    root_dir = os.path.abspath(root_dir)
    if not os.path.isdir(root_dir):
        log.error(f"错误: 目标文件夹 '{root_dir}' 不存在")
        exit(1)
    for subdir in next(os.walk(root_dir))[1]:
        cat=subdir[:-2]
        prompt = f"Write a CodeQL query in the c/cpp language to test whether {cat} exists in the codebase.Require that if there is a vulnerability in the output results, the file name where the vulnerability is located must be specified in the results."
        prompt1 = f"Write a CodeQL query in the c/cpp language to test whether {cat} exists in the codebase.Require that if there is a vulnerability in the output results, the file name where the vulnerability is located must be specified in the results."
        n = 0
        result = False
        while not result and n <= 10:
            log.info(f"进行{subdir}的第{n + 1}次生成")
            #看是否有反馈文件 没有这个文件，则用最初的prompt，如有
            #读取错误，以及上一次的response作为下一次的反馈
            process(root_dir, subdir, prompt)
            #prompt=read_file(root_dir+subdir, subdir)
            #print(prompt)

            #print(f"第{n + 1}次生成的prompt是：{prompt}\n")

            preresponse=client.prev_response
            if preresponse==None:
                log.info(f"此项目超出了大模型的能力，即将进入下一个项目的测试")


                unable.append(subdir)

                client.clear_history()
                break

            errors= get_errors_content(f"{root_dir}/{subdir}", f"{subdir}.txt")

            #print(f"第{n}次生成的{prompt}/n")
            prompt=f"{prompt1}\nThe CodeQL statement generated by the model last time:'{preresponse}'\n The error reported when running the statement generated last time:'{errors}'"

            result = check_file_for_error(f"{root_dir}/{subdir}", f"{subdir}.txt")
            if n==10 or result == True:
                with open("history.json", "w", encoding="utf-8") as f:
                    json.dump(client.history, f, ensure_ascii=False, indent=4)
                print(f"历史记录已成功保存")
                client.clear_history()

            if result == True:
                log.info(f"{subdir}的第{n + 1}次生成结果正确，退出循环")
                break

            n=n+1
            continue


        continue
    print("本轮测试已经完成")
    if len(unable)>0:
        print(f"本次检测中超出模型能力限制（最大token）的项目为{unable}")
        #with open("unable.txt", "w") as file:
            #for item in unable:
                #file.write(str(item) + "\n")
    else:
        print("本轮检测的所有项目都未超过模型能力")


if __name__ == "__main__":
    main()

                                        #1.修改项目文件夹位置（总的大文件夹位置）       main中的root_dir
                                        #2.修改大模型名称                         process函数中的client.call，修改model="模型名"

