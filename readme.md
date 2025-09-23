<div align="center">
    <p>
    <h1>
    RepoQLEval
    </h1>
    <style="width: 200px; height: 200px;">
    </p>
    <p>
    </p>
    <a href="https://github.com/repoqleval/RepoQLEval"><img src="https://img.shields.io/badge/Platform-linux-lightgrey" alt="platform"></a>
    <a href="https://github.com/repoqleval/RepoQLEval"><img src="https://img.shields.io/badge/Python-3.8+-orange" alt="python"></a>
    <a href="https://github.com/repoqleval/RepoQLEval"><img src="https://img.shields.io/badge/License-MIT-red.svg" alt="license"></a>
</div>


<hr>

## 🚀 Overview
RepoQLEval is a comprehensive benchmark designed to evaluate the capabilities of large language models (LLMs) in generating CodeQL queries for repository-level vulnerability detection. The project includes code for Preliminary Experiment 2, the Main Experiment, and a structured dataset divided into two parts: C/CPP (stored in the `cpp-v4` directory) and Python (stored in the `python-v1` directory). Preliminary Experiment 1 was conducted using the CodeQL plugin in VSCode, so no additional code is provided for it.

> [NOTE]  
> Before running the experiments, ensure the CodeQL CLI is installed and environment variables are properly configured.

## 🔥 News
- *Sep 12, 2025*: RepoQLEval benchmark and experiments are now publicly available! 🎉

## 📥 Setup and Configuration

### Prerequisites
- Install the [CodeQL CLI](https://github.com/github/codeql-cli-binaries/releases?page=1) and configure environment variables.
- Ensure Python 3.8 or higher is installed.

### CodeQL Configuration
To automate the configuration of `.yml` files for CodeQL, use the batch automation program located in the `yml` folder.

**Parameters to Modify:**
- `root_directory`: Set to the actual path of the project root folder.

## 🛠️ Experiments

### Preliminary Experiment
Preliminary Experiment 2 evaluates the vulnerability detection capabilities of LLMs at the repository level. The code is organized in the `preliminary-exp` folder:

- **llm-python**: Tests LLMs on Python database repositories.
- **llm-cpp**: Tests LLMs on C/CPP database repositories.

**Parameters to Modify:**
- `folder_path`: Set to the actual path of the project root folder.

### Main Experiment
The Main Experiment evaluates LLMs' ability to generate and optimize CodeQL queries across three progressive stages, with code located in the project root:

- **main.py**: Tests direct generation of CodeQL statements.
- **main-file.py**: Tests customization of CodeQL statements.
- **main-file-ql.py**: Tests optimization of CodeQL statements.

**Parameters to Modify:**
- `model`: Specify the name of the LLM to be tested.
- `root_dir`: Set to the actual path of the project root folder.

## 📊 Saving and Analyzing Results
Scripts for saving and analyzing experiment results are located in the `results` folder:

- **save_history.py**: Saves historical records for subsequent analysis.
- **results_ext.py**: Extracts results for LLM-assisted comparison and manual verification.
- **results_ans.py**: Uses a capable LLM for preliminary comparison, followed by manual spot-checking to evaluate model performance.

## 🔍 Dataset Description
The dataset is divided into two parts:
- **python-v1**: Contains Python repository data.
- **cpp-v4**: Contains C/CPP repository data.

  you can download the all data from [Google Drive](https://drive.google.com/drive/folders/1esB_XYgWPUe95CgEdRmVvZ8m8CVWaQgI?usp=drive_link), or simply use the following links:
```bash
https://drive.google.com/drive/folders/1esB_XYgWPUe95CgEdRmVvZ8m8CVWaQgI?usp=drive_link
```

Each dataset includes repository-level information tailored for evaluating CodeQL query generation and vulnerability detection.



> [WARNING]  
> The code is not fully tested and may require debugging. If you encounter issues, please raise them on the [GitHub repository](https://github.com/repoqleval/RepoQLEval) or submit a pull request. Thank you!



