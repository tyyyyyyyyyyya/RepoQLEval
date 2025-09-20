# RepoQLEval: A Reproducible Benchmark for Evaluating LLMs on Generating CodeQL for Repo-Level Vulnerability Detection

## Overview

This project contains the code for Preliminary Experiment 2, the Main Experiment, and the benchmark created for the article *"RepoQLEval: A Reproducible Benchmark for Evaluating LLMs on Generating CodeQL for Repo-Level Vulnerability Detection"*. The dataset is divided into two parts: C/CPP and Python, stored in the `python-v1` and `cpp-v4` directories, respectively.

Since Preliminary Experiment 1 was conducted directly using the CodeQL plugin in VSCode, no additional code is required for it. Before starting the experiments, you must install the CodeQL CLI and properly configure the environment variables.

## Preliminary Experiment

Preliminary Experiment 2 evaluates the vulnerability detection capabilities of large language models (LLMs) at the repository level. The code is located in the `preliminary-exp` folder, divided into:

- **llm-python**: Tests the vulnerability detection capabilities of various LLMs on Python database repositories.
- **llm-cpp**: Tests the vulnerability detection capabilities of various LLMs on C/CPP database repositories.

**Parameters to Modify Before Running:**

- `folder_path`: Replace with the actual path to the project root folder.

## CodeQL Configuration

Before running the CodeQL database, you need to configure the `.yml` files. We have implemented a program for batch automation of this configuration. The relevant files are located in the `yml` folder.

**Parameters to Modify:**

- `root_directory`: Replace with the actual path to the project root folder.

## Main Experiment

The Main Experiment tests the CodeQL generation capabilities of various LLMs, divided into three progressive stages:

- **main.py**: Tests the ability of LLMs to directly generate CodeQL statements.
- **main-file.py**: Tests the ability of LLMs to customize CodeQL statements.
- **main-file-ql.py**: Tests the ability of LLMs to optimize CodeQL statements.

**Parameters to Modify Before Running:**

- `model`: Specify the name of the LLM to be tested.
- `root_dir`: Replace with the actual path to the project root folder.

## Saving and Analyzing Experiment Results

For the generated experiment results, we have designed extraction scripts and LLM-assisted vulnerability label comparison. After each part of the Main Experiment, you can use our scripts to automatically save and perform a preliminary analysis of the results. The scripts for saving and analyzing results are located in the `results` folder, divided into the following files:

- **save_history.py**: Saves all historical records for subsequent analysis.
- **results_ext.py**: Extracts results for subsequent LLM-assisted comparison and manual verification.

**results_ans.py**: Uses a capable LLM for preliminary comparison, followed by manual spot-checking to evaluate the model's capabilities across various aspects.