import os
import subprocess
import logging

log = logging.getLogger(__name__)

def run_and_save_commands(directory, command, output_file):
    try:

        old_dir = os.getcwd()

        os.chdir(directory)

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )


        output_filename = os.path.join(directory, f"{output_file}.txt")


        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(f"Directory changed to: {directory}\n")
            f.write(f"Command executed: {command}\n")
            f.write("--- Output ---\n")
            f.write(result.stdout)

            if result.stderr:
                f.write("\n--- Errors ---\n")
                f.write(result.stderr)

        print(f"Command output saved to {output_filename}")


        os.chdir(old_dir)

    except FileNotFoundError:
        print(f"Error: Directory '{directory}' not found")

    except Exception as e:
        print(f"An error occurred: {str(e)}")


project_dir = "/path/to/project"          
ql_file = "/path/to/query/test.ql"       
subdir = "query_result"                   



try:
    log.info("Running the generated QL query...")

    command = f"codeql query run --database=test-db {ql_file}"

    run_and_save_commands(
        project_dir,
        command,
        subdir
    )

    log.info("The generated query results have been saved")

except Exception as e:
    log.error(f"Failed to run CodeQL for {project_dir}: {str(e)}")