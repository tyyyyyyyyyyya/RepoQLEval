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
RepoQLEval is a benchmark designed to evaluate the capability of Large Language Models (LLMs) in generating **executable** CodeQL queries for repository-level vulnerability detection.

The benchmark contains **87 real-world open-source repositories** (44 Python and 43 C/C++) spanning **12 CWE categories**, with manually validated file-level ground truth and auxiliary function-/line-level annotations for 67 repositories. Every repository–CWE pair is paired with a pre-constructed CodeQL database and evaluated under a **pinned toolchain** (CodeQL CLI 2.11.0, python-all 0.6.0, cpp-all 0.4.0), so differences in results come from the queries, not from inconsistent extraction environments.

RepoQLEval treats **executability and context feasibility as first-class outcomes**. A generated query must compile, execute within a 300-second budget, and localize the correct files before its semantic score is meaningful.

RepoQLEval supports:

- **Direct LLM vulnerability localization** — models predict vulnerable files directly from repository context.
- **T1: Generic CWE-to-CodeQL generation** — generate a query from a CWE description and target language alone.
- **T2: Repository-conditioned CodeQL query customization** — generate a query using project-specific sources, sinks, wrappers, and APIs.
- **T3: Seed-guided CodeQL query rewriting** — rewrite or adapt an official seed query for a concrete repository.

> [NOTE]  
> Before running the experiments, ensure the CodeQL CLI is installed and environment variables are properly configured.



## 📥 Setup and Configuration

### Prerequisites
- Install the [CodeQL CLI](https://github.com/github/codeql-cli-binaries/releases?page=1) and configure environment variables.
- Ensure Python 3.8 or higher is installed.


### CodeQL Configuration
To automate the configuration of `.yml` files for CodeQL, use the batch automation program located in the `yml` folder:
- `yml/yml-python.py` creates `qlpack.yml` with `codeql/python-all:0.6.0` and runs `codeql pack install`.
- `yml/yml-cpp.py` creates `qlpack.yml` with `codeql/cpp-all:0.4.0` and runs `codeql pack install`.

**Parameters to Modify:**
- `root_directory`: Set to the actual path of the project root folder.


## 🛠️ Experiments

### 1. Direct LLM Detection (`Direct-Detection/`)
- `llm-python-v2.py` and `llm-cpp-v2.py` feed repository source files to an LLM and ask it to list vulnerable files for a target CWE.
- Context is truncated with `tiktoken` (largest-file-discard policy) when it exceeds the model’s usable context window.
- Output is normalized to repository-relative file paths and compared against `labels-python.json` / `labels-cpp.json`.

### 2. LLM → CodeQL Generation (`LLM2CodeQL-python/` and `LLM2CodeQL-cpp/`)
All three probes share a **10-round repair loop** (5 rounds for DeepSeek-Reasoner) that feeds compiler/runtime errors back to the model.

| Probe | Script | Input |
|-------|--------|-------|
| T1 Generic CWE→QL | `main.py` | CWE description + target language |
| T2 Repo-conditioned | `main_file.py` | CWE description + full repository source |
| T3 Seed-guided | `main_file_ql.py` | CWE description + repository source + official seed query |

- Prompts are defined in `prompts.txt` and use a `ql''' ... '''` code-only output constraint.
- Generated queries are saved as `test.ql` and executed with `codeql query run --database=test-db test.ql`.

### 3. Result Analysis (`results/`)
- `results_ext.py` — batch-extracts CodeQL outputs from per-project `.txt` logs into `codeql_batch_results.json`.
- `codeql_compile_error_classifier.py` — classifies repair-log compilation errors into diagnostic categories (syntax/parsing, import/module resolution, name/API resolution, type compatibility, binding/range restriction, class/predicate structure, declaration/query-shape, metadata/result-shape) and produces CSV/JSON/Markdown reports.
- `save_history.py` — copies per-project `history.json`, `*.txt`, and `test.ql` artifacts into a target directory.


## 🔍 Dataset Description
The dataset is divided into two parts:
- **python-v1**: Contains 44 Python repository–CWE instances.
- **cpp-v4**: Contains 43 C/C++ repository–CWE instances.

Each instance is labeled with manually curated file-level ground truth in `labels-python.json` and `labels-cpp.json`. 67 repositories additionally include function- and line-level annotations as auxiliary metadata.

Covered CWE categories include:

- Python: CWE-20, CWE-22, CWE-78, CWE-79, CWE-89, CWE-94, CWE-352, CWE-502, CWE-798, CWE-918
- C/C++: CWE-20, CWE-22, CWE-78, CWE-79, CWE-89, CWE-119, CWE-190

You can download all data (pre-constructed CodeQL databases, repository sources, and labels) from [Google Drive](https://drive.google.com/drive/folders/1esB_XYgWPUe95CgEdRmVvZ8m8CVWaQgI?usp=drive_link):
```bash
https://drive.google.com/drive/folders/1esB_XYgWPUe95CgEdRmVvZ8m8CVWaQgI?usp=drive_link
```


## 📊 Evaluation Protocol and Metrics

RepoQLEval evaluates every generated query through the same pipeline:

1. **Compile** the generated `.ql` file under the pinned toolchain.
2. **Execute** it on the pre-constructed CodeQL database (300 s timeout).
3. **Normalize** output paths to repository-relative file paths.
4. **Score** against the manually curated file-level ground truth.

### Semantic metrics
- **Precision**, **Recall**, and **F1**.

### Feasibility metrics
- **Compile-Pass** — fraction of generated queries that compile successfully.
- **Exec-Pass** — fraction that compile and execute without runtime error or timeout.
- **Timeout Rate** — fraction of executions exceeding the 300-second budget.
- **Context-Feasible Ratio (CFR)** — fraction of repository–CWE instances whose required context fits the model’s usable context window.
- **Feasibility-Adjusted F1** = F1 × CFR, summarizing effective performance under context constraints.




## 📄 Citation
If you use RepoQLEval in your research, please cite our paper:

> RepoQLEval: A Large-Scale Benchmark and Baseline Study for Repository-Level CodeQL Query Generation.


## 📜 License
RepoQLEval annotations and evaluation code are released under the MIT License. The original benchmark repositories remain under their respective open-source licenses.

