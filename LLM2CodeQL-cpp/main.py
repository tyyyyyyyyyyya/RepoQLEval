import requests
from typing import List, Dict, Union
import logging
import os
from resultdemo import cmdresults
import json


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


file_handler = logging.FileHandler('qwen-a.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log.addHandler(file_handler)


class LLMApiClient:
    def __init__(self, base_url: str, api_key: str, system_prompt: str = ""):
        """Initialize the client"""
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

    def call(self, prompt: str, model: str, use_history: bool = True) -> dict:
        """Invoke the large model, supporting system prompt and conversation history"""
        endpoint = f"{self.base_url}/chat/completions"

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        if use_history and self.history:
            messages.extend(self.history)
        messages.append({"role": "user", "content": prompt})


        payload = {
            'model': model,
            'messages': messages
        }

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            response_data = response.json()

            if 'error' in response_data:
                log.info("The total number of tokens has exceeded the limit, discarding historical records")
                messages = []
                if self.system_prompt:
                    messages.append({"role": "system", "content": self.system_prompt})
                messages.append({"role": "user", "content": prompt})
                payload = {
                    'model': model,
                    'messages': messages
                }
                response = requests.post(endpoint, headers=self.headers, json=payload)
                response.raise_for_status()
                response_data = response.json()


            if 'error' in response_data:
                log.error(f"Still an error after removing historical records: {response_data['error']['message']}")
                client.prev_response=None
                return
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', 'No response content')
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": content})
            self.prev_prompt = prompt
            self.prev_response = content

            if self.prefill:
               content = self.prefill + content


            response_data['choices'][0]['message']['content'] = content
            return response_data
        except requests.exceptions.RequestException as e:
            raise Exception(f"API call failed: {str(e)}")

    def clear_history(self):
        """Clear conversation history"""
        self.history = []
        self.prev_prompt = None
        self.prev_response = None

    def set_prefill(self, prefill: Union[str, None]):
        """Set response prefill"""
        self.prefill = prefill



def process(root_dir,subdir, prompt):
    project_dir = os.path.join(root_dir, subdir)
    log.info(f"Processing project folder: {project_dir}")
    try:
        log.info(f"Generating QL query for {project_dir}")

        client.call(prompt, model="qwen3-32b", use_history=True)
        ql_code=client.prev_response
        if ql_code==None:
            return
        start_marker = "ql'''"
        end_marker = "'''"

        start_index = ql_code.find(start_marker) + len(start_marker)
        end_index = ql_code.find(end_marker, start_index)

        ql_code = ql_code[start_index:end_index]


        ql_file = os.path.join(project_dir, "test.ql")
        with open(ql_file, 'w', encoding='utf-8') as f:
            f.write(ql_code)
        log.info(f"QL query has been saved to: {ql_file}")

    except Exception as e:
        log.error(f"Unknown error occurred while generating QL query for {project_dir}: {str(e)}", exc_info=e)


    try:
        log.info(f"Running the generated QL query...")
        command = f"codeql query run --database=test-db {ql_file}"
        cmdresults.run_and_save_commands(project_dir, command, subdir)
        log.info(f"The generated query results have been saved")
    except Exception as e:
        log.error(f"Failed to run CodeQL for {project_dir}: {str(e)}")




def check_file_for_error(file_path, file_name):
    try:
        with open(f"{file_path}/{file_name}", 'r') as file:
            content = file.read()
            return "ERROR:" not in content
    except UnicodeDecodeError:
            print("UnicodeDecodeError, generation failed")
            return False


def get_errors_content(folder_path, file_name):
    """
    Extract the content after '--- Errors ---' from the specific .txt file in the specified folder.

    Parameters:
        folder_path (str): folder path
        file_name (str): target file name (including .txt suffix)

    Returns:
        str: content after '--- Errors ---', return empty string if not found
    """

    file_path = os.path.join(folder_path, file_name)
    if not os.path.isfile(file_path) or not file_name.endswith('.txt'):
        return f"Error: {file_name} does not exist or is not a .txt file"

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    marker = "--- Errors ---"
    if marker not in content:
        return "'--- Errors ---' marker not found"

    return content[content.index(marker) + len(marker):].strip()


base_url = "https://flag.smarttrot.com/v1"
api_key = ""


system_prompt = "You are a CodeQL expert, proficient in CodeQL version 2.11.0, with the corresponding cpp library version 0.4.0. Your goal is to provide CodeQL statements, so only output the QL statements that would be written in a .ql file, without any additional prompts. Ensure the outputted CodeQL statements can be directly saved as a .ql file and run without issues. The output format is as follows: start with ql''' and end with ''', with only CodeQL statements in between."



client = LLMApiClient(base_url, api_key, system_prompt)


def main():

    unable=[]
    root_dir = ""
    root_dir = os.path.abspath(root_dir)
    if not os.path.isdir(root_dir):
        log.error(f"Error: target folder '{root_dir}' does not exist")
        exit(1)
    for subdir in next(os.walk(root_dir))[1]:
        cat=subdir[:-2]
        prompt = f"Write a CodeQL query in the c/cpp language to test whether {cat} exists in the codebase.Require that if there is a vulnerability in the output results, the file name where the vulnerability is located must be specified in the results."
        prompt1 = prompt
        n = 0
        result = False
        while not result and n <= 10:
            log.info(f"Performing the {n + 1}th generation for {subdir}")
            process(root_dir, subdir, prompt)

            preresponse=client.prev_response
            if preresponse==None:
                log.info(f"This project exceeds the large model's capability, proceeding to the next project's test")


                unable.append(subdir)

                client.clear_history()
                break

            errors= get_errors_content(f"{root_dir}/{subdir}", f"{subdir}.txt")


            prompt=f"{prompt1}/nThe CodeQL statement generated by the model last time:'{preresponse}'\n The error reported when running the statement generated last time:'{errors}'"
            result = check_file_for_error(f"{root_dir}/{subdir}", f"{subdir}.txt")
            if n==10 or result == True:
                with open("history.json", "w", encoding="utf-8") as f:
                    json.dump(client.history, f, ensure_ascii=False, indent=4)
                print(f"The history record of the {subdir} project has been successfully saved")
                client.clear_history()

            if result == True:
                log.info(f"The {n + 1}th generation result for {subdir} is correct, exiting the loop")
                break

            n=n+1
            continue


        continue
    print("This round of testing has been completed")
    if len(unable)>0:
        print(f"The projects exceeding the model capability limit (maximum token) in this detection are {unable}")
    else:
        print("All projects in this round of detection did not exceed the model capability")
if __name__ == "__main__":
    main()