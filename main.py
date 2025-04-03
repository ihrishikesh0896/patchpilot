import argparse
import json
import os
import subprocess
import tempfile
import time
import logging
from transformers import pipeline
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    import git
except ImportError:
    logging.error("GitPython library not found. Install it using: pip install GitPython")
    exit(1)

# Load the model and measure loading time
start_time = time.time()
# try:
#     # generator = pipeline("text2text-generation", model="Salesforce/codet5p-220m")
#     generator = pipeline("text-generation", model="microsoft/phi-1_5")
#     model_load_time = time.time() - start_time
#     logging.info(f"Model loaded successfully in {model_load_time:.2f} seconds.")
# except Exception as e:
#     logging.error(f"Error loading model: {e}")
#     exit(1)

REMOTE_MODEL_URL = "http://192.168.1.13:9000/generate"

def clone_repo(repo_url, temp_dir):
    """Clones a Git repository into a temporary directory."""
    logging.info(f"Cloning repository: {repo_url} into {temp_dir}")
    try:
        git.Repo.clone_from(repo_url, temp_dir)
        logging.info("Cloning successful.")
        return True
    except git.GitCommandError as e:
        logging.error(f"Error cloning repository: {e}")
        return False

def run_sast_tool(tool_name, repo_path, output_file):
    """Runs a SAST tool (Bandit or Semgrep) and returns results."""
    logging.info(f"Running {tool_name} on: {repo_path}")
    commands = {
        "bandit": ['bandit', '-r', repo_path, '-f', 'json', '-o', output_file],
        "semgrep": ['semgrep', '--config=auto', '--json', '-o', output_file, repo_path]
    }
    if tool_name not in commands:
        logging.error(f"Unsupported SAST tool: {tool_name}")
        return None
    try:
        start_time = time.time()
        subprocess.run(commands[tool_name], capture_output=True, text=True, check=False)
        elapsed_time = time.time() - start_time
        logging.info(f"{tool_name} scan completed in {elapsed_time:.2f} seconds.")
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                return json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: '{tool_name}' not found. Install it before running.")
    except Exception as e:
        logging.error(f"Error running {tool_name}: {e}")
    return None

# def get_llm_suggestion(finding):
#     """Gets an LLM-generated secure code fix."""
#     try:
#         prompt = (
#             f"Given this security finding: {finding.get('issue_text', 'N/A')} "
#             f"in file {finding.get('filename', 'N/A')} at line {finding.get('line_number', 'N/A')}, "
#             f"generate a concise and correct security fix. Keep the response under 100 words."
#         )
#         start_time = time.time()
#         suggestions = generator(prompt, max_length=250, num_return_sequences=1)
#         elapsed_time = time.time() - start_time
#         logging.info(f"LLM suggestion generated in {elapsed_time:.2f} seconds.")
#         return suggestions[0]['generated_text']
#     except Exception as e:
#         logging.error(f"Error getting LLM suggestion: {e}")
#         return None

def get_llm_suggestion(finding):
    """Gets an LLM-generated secure code fix from the hosted model."""
    try:
        prompt = (
            f"Given this security finding: {finding.get('issue_text', 'N/A')} "
            f"in file {finding.get('filename', 'N/A')} at line {finding.get('line_number', 'N/A')}, "
            f"generate a concise and correct security fix. Keep the response under 100 words."
        )

        start_time = time.time()
        response = requests.post(REMOTE_MODEL_URL, json={"prompt": prompt})
        elapsed_time = time.time() - start_time

        if response.status_code == 200:
            suggestion = response.json().get("generated_text", "").strip()
            logging.info(f"LLM suggestion generated in {elapsed_time:.2f} seconds.")
            return suggestion
        else:
            logging.error(f"Error: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error getting LLM suggestion: {e}")
        return None



def print_results(tool_name, results):
    """Prints scan results with LLM-generated fixes."""
    if results and 'results' in results:
        logging.info(f"\n--- {tool_name.upper()} Scan Results with LLM Suggestions ---")
        for finding in results['results']:
            logging.info(f"Severity: {finding.get('issue_severity', 'N/A')}")
            logging.info(f"Issue: {finding.get('issue_text', 'N/A')}")
            logging.info(f"File: {finding.get('filename', 'N/A')}:{finding.get('line_number', 'N/A')}")
            suggestion = get_llm_suggestion(finding)
            logging.info(f"Suggestion: {suggestion.strip() if suggestion else 'No suggestion available.'}\n")
    else:
        logging.info(f"No results from {tool_name}.")

def main():
    parser = argparse.ArgumentParser(description="SAST Orchestrator")
    parser.add_argument("command", choices=["repo_url"], help="Command to execute (only 'repo_url' is supported)")
    parser.add_argument("repo_url", help="Git repository URL to scan")
    parser.add_argument("-t", "--tool", choices=["bandit", "semgrep"], default="bandit", help="Choose SAST tool (default: bandit)")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_dir:
        if not clone_repo(args.repo_url, temp_dir):
            return

        output_file = os.path.join(temp_dir, "sast_results.json")
        results = run_sast_tool(args.tool, temp_dir, output_file)
        if results:
            print_results(args.tool, results)
        else:
            logging.info("\nNo security findings detected.")

if __name__ == "__main__":
    main()
