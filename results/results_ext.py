import os
import json
import re
from pathlib import Path
from typing import Dict, List


def batch_process_codeql(root_dir: str) -> None:

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
                    # Read the content of the txt file
                    with txt_file.open('r', encoding='utf-8') as f:
                        content = f.read()
                        # Extract content between --- Output --- and --- Errors ---
                        pattern = r'--- Output ---\n(.*?)(?:\n--- Errors ---|\Z)'
                        match = re.search(pattern, content, re.DOTALL)
                        extracted_content = match.group(1).strip() if match else ""
                        all_contents[project_dir.name] = extracted_content
                        # Add to combined content with project name header
                        if extracted_content:
                            combined_txt_content.append(f"Project: {project_dir.name}\n{extracted_content}\n")
                        success_projects.append({
                            'project': project_dir.name,
                            'file_path': str(txt_file),
                            'content_length': len(extracted_content)
                        })
                        print(f"{project_dir.name}: Success")
                except Exception as e:
                    failed_projects.append(f"{project_dir.name}: Failed to read file ({str(e)})")
                    print(f"{project_dir.name}: Failed to read file ({str(e)})")
            else:
                failed_projects.append(f"{project_dir.name}: No matching .txt file found")
                print(f"{project_dir.name}: Failed - No matching .txt file found")


    output_data = {

        'project_contents': all_contents
    }


    output_file = output_dir / "codeql_batch_results.json"
    try:
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to {output_file}")
    except Exception as e:
        print(f"\nError saving JSON file: {str(e)}")

    combined_txt_file = output_dir / "combined_results.txt"
    try:
        with combined_txt_file.open('w', encoding='utf-8') as f:
            f.write('\n'.join(combined_txt_content))
        print(f"Combined results saved to {combined_txt_file}")
    except Exception as e:
        print(f"Error saving combined TXT file: {str(e)}")


if __name__ == "__main__":
    root_directory = r"" #替换为项目实际路径
    batch_process_codeql(root_directory)