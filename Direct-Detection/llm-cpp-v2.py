import os
import requests
import tiktoken
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

file_handler = logging.FileHandler('cpp.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


class LLMApiClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def call(self, prompt: str, model: str) -> dict:
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
            logger.error(f"API call failed: {str(e)}")
            raise

    def read_cpp_files(self, folder_path: str) -> List[Dict[str, str]]:

        py_files = []

        try:
            if not os.path.isdir(folder_path):
                raise ValueError(f"Path {folder_path} is not a valid folder")

            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith(('.h','.c','.cpp')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            py_files.append({"path": file_path, "content": content})
                        except Exception as e:
                            logger.error(f"Skipping file {file_path}, read failed: {str(e)}")
        except Exception as e:
            logger.error(f"Processing folder {folder_path} failed: {str(e)}")

        return py_files


def truncate_content(py_files: List[Dict[str, str]], max_tokens: int, encoding, skip_levels: int) -> tuple[str, List[str]]:

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
            logger.error(f"Skipping file {file_name}, token encoding failed: {str(e)}")
            removed_files.append(file_name)

    return concatenated_content, removed_files


def main():

    base_url = ""
    api_key = ""
    client = LLMApiClient(base_url, api_key)

    system_prompt = "You are a code analysis assistant. Please analyze the content of the following files to determine if there are any CWE vulnerabilities present. If vulnerabilities exist, provide the CWE number and list all file names containing CWE vulnerabilities. Only list the file names with vulnerabilities and the CWE number, without outputting any related analysis or detailed information."

    large_models = [
        {"name": "claude-3-haiku-20240307", "context_window_tokens": 200000},
        {"name": "gpt-4o", "context_window_tokens": 128000},
        {"name": "grok-3", "context_window_tokens": 128000},
        {"name": "qwen3-32b", "context_window_tokens": 256000},
        {"name": "llama3-8b-instruct", "context_window_tokens": 8000},
        {"name": "deepseek-reasoner", "context_window_tokens": 98304},
        {"name": "qwen3-coder-plus", "context_window_tokens": 1048576}
    ]

    models = ["grok-3"]
    skip_levels = 3

    folder_path = ""

    encoding = tiktoken.get_encoding("cl100k_base")

    try:
        subdirs = next(os.walk(folder_path))[1]

        if not subdirs:
            logger.warning(f"No subfolders found in root folder {folder_path}")
            return



        for subdir in subdirs:
            subdir_path = os.path.join(folder_path, subdir)
            logger.info(f"Processing project: {subdir_path}")

            py_files = client.read_cpp_files(subdir_path)

            if not py_files:
                logger.warning(f"Project {subdir_path} has no .c/.cpp files")
                continue

            prompt_content = system_prompt
            for py_file in py_files:
                path_parts = py_file['path'].split(os.sep)
                if len(path_parts) > skip_levels:
                    relative_path = os.sep.join(path_parts[skip_levels:])
                else:
                    relative_path = os.path.basename(py_file['path'])
                prompt_content += f"\nfile: {relative_path}\ncontent:\n{py_file['content']}\n"

            try:
                current_tokens = len(encoding.encode(prompt_content, allowed_special="all"))
            except Exception as e:
                logger.error(f"Initial content token encoding failed: {str(e)}")
                continue

            py_files_current = py_files.copy()

            for model in models:
                total_removed_files = 0
                max_tokens = None
                for model_info in large_models:
                    if model_info["name"] == model:
                        max_tokens = model_info["context_window_tokens"]
                        break
                if max_tokens is None:
                    continue

                current_max_tokens = max_tokens
                prompt_content_current = prompt_content
                py_files_current = py_files.copy()
                try:
                    current_tokens = len(encoding.encode(prompt_content_current, allowed_special="all"))
                except Exception as e:
                    logger.error(f"Content token encoding failed: {str(e)}")
                    continue

                if current_tokens > current_max_tokens:
                    logger.info(f"Initial tokens ({current_tokens}) exceed {model} limit ({current_max_tokens}), performing truncation")
                    system_tokens = len(encoding.encode(system_prompt, allowed_special="all"))
                    concatenated_content, removed_files = truncate_content(py_files_current, current_max_tokens - system_tokens, encoding, skip_levels)
                    prompt_content_current = system_prompt + concatenated_content
                    try:
                        current_tokens = len(encoding.encode(prompt_content_current, allowed_special="all"))
                    except Exception as e:
                        logger.error(f"Token encoding failed after truncation: {str(e)}")
                        continue
                    total_removed_files += len(removed_files)
                    logger.info(f"Removed files: {removed_files}")
                    logger.info(f"Tokens after truncation: {current_tokens}")

                    removed_set = set(removed_files)
                    py_files_current = [f for f in py_files_current if os.path.basename(f['path']) not in removed_set]

                success = False
                while not success and py_files_current:
                    try:
                        logger.info(f"Calling model: {model}")
                        response = client.call(prompt_content_current, model=model)

                        if 'error' in response:
                            logger.warning(f"Token limit still exceeded, continuing truncation (current tokens: {current_tokens})")

                            current_max_tokens = int(current_max_tokens * 0.9)
                            if current_max_tokens < 1000:
                                logger.error("Unable to truncate further, minimum limit reached")
                                break

                            system_tokens = len(encoding.encode(system_prompt, allowed_special="all"))
                            logger.info(f"Current max tokens: {current_max_tokens}, tokens available for files: {current_max_tokens - system_tokens}")
                            concatenated_content, removed_files = truncate_content(py_files_current, current_max_tokens - system_tokens, encoding, skip_levels)
                            prompt_content_current = system_prompt + concatenated_content
                            try:
                                current_tokens = len(encoding.encode(prompt_content_current, allowed_special="all"))
                            except Exception as e:
                                logger.error(f"Token encoding failed after truncation: {str(e)}")
                                break
                            total_removed_files += len(removed_files)
                            logger.info(f"Removed files: {removed_files}")
                            logger.info(f"Tokens after truncation: {current_tokens}")
                            removed_set = set(removed_files)
                            py_files_current = [f for f in py_files_current if os.path.basename(f['path']) not in removed_set]
                            continue

                        content = response.get('choices', [{}])[0].get('message', {}).get('content','No response content')
                        logger.info(f"Model {model} returned: {content}")
                        if total_removed_files == 0:
                            logger.info(f"Project {subdir_path} processing completed, total removed files: 0")
                        else:
                            logger.info(
                                f"Project {subdir_path} processing completed, total removed files: {total_removed_files}")
                        success = True

                    except Exception as e:
                        logger.error(f"Failed to call {model}: {str(e)}")
                        break
    except Exception as e:
        logger.error(f"Failed to process folder: {str(e)}")




if __name__ == "__main__":
    main()