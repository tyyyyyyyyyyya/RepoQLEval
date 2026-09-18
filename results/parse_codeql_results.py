import os
import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List



def parse_txt_file(file_path):
    project_files = defaultdict(set)

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    projects = content.split('Project: ')[1:]

    for project in projects:
        project_name = project.split('\n')[0].strip()

        c_files = re.findall(r'\b[\w_]+\.(?:cpp|c|h|py)\b', project)
        for c_file in c_files:
            project_files[project_name].add(c_file)

    result = {k: sorted(list(v)) for k, v in project_files.items()}

    project_names = re.findall(r'Project: ([^\n]+)', content)

    for name in project_names:
        if name not in result:
            result[name] = []

    return result




def batch_process_codeql(root_dir: str):

    root_path = Path(root_dir)

    if not root_path.exists() or not root_path.is_dir():
        print(f"Error: {root_dir} is not a valid directory")
        return


    success_projects: List[Dict] = []
    failed_projects: List[str] = []
    all_contents: Dict[str, str] = {}
    combined_txt_content: List[str] = []


    output_dir = root_path / "codeql_results"
    output_dir.mkdir(exist_ok=True)


    for project_dir in root_path.iterdir():

        if project_dir.is_dir():

            print(f"Processing {project_dir.name}...")


            txt_file = project_dir / f"{project_dir.name}.txt"


            if txt_file.exists() and txt_file.is_file():

                try:

                    with txt_file.open('r', encoding='utf-8') as f:
                        content = f.read()


                    pattern = r'--- Output ---\n(.*?)(?:\n--- Errors ---|\Z)'

                    match = re.search(
                        pattern,
                        content,
                        re.DOTALL
                    )


                    extracted_content = (
                        match.group(1).strip()
                        if match else ""
                    )


                    all_contents[project_dir.name] = extracted_content


                    if extracted_content:
                        combined_txt_content.append(
                            f"Project: {project_dir.name}\n"
                            f"{extracted_content}\n"
                        )


                    success_projects.append({
                        'project': project_dir.name,
                        'file_path': str(txt_file),
                        'content_length': len(extracted_content)
                    })


                    print(f"{project_dir.name}: Success")


                except Exception as e:

                    failed_projects.append(
                        f"{project_dir.name}: Failed to read file ({str(e)})"
                    )


            else:

                failed_projects.append(
                    f"{project_dir.name}: No matching .txt file found"
                )



    output_data = {
        'project_contents': all_contents
    }


    output_file = output_dir / "codeql_batch_results.json"


    with output_file.open(
        'w',
        encoding='utf-8'
    ) as f:

        json.dump(
            output_data,
            f,
            indent=2,
            ensure_ascii=False
        )


    print(f"Results saved to {output_file}")




    combined_txt_file = output_dir / "combined_results.txt"


    with combined_txt_file.open(
        'w',
        encoding='utf-8'
    ) as f:

        f.write(
            '\n'.join(combined_txt_content)
        )


    print(
        f"Combined results saved to {combined_txt_file}"
    )



    result = parse_txt_file(
        combined_txt_file
    )


    final_json = output_dir / "output.json"


    with final_json.open(
        'w',
        encoding='utf-8'
    ) as f:

        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False
        )


    print(
        f"File mapping saved to {final_json}"
    )



if __name__ == "__main__":

    root_directory = r""

    batch_process_codeql(
        root_directory
    )