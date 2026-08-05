import subprocess

import os


def run_and_save_commands(directory, command, output_file):
    try:

        os.chdir(directory)


        result = subprocess.run(command, shell=True, capture_output=True, text=True)



        output_filename = os.path.join(directory, f"{output_file}.txt")

        # 输出
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(f"Directory changed to: {directory}\n")
            f.write(f"Command executed: {command}\n")
            f.write("--- Output ---\n")
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- Errors ---\n")
                f.write(result.stderr)

        print(f"Command output saved to {output_filename}")

    except FileNotFoundError:
        print(f"Error: Directory '{directory}' not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

