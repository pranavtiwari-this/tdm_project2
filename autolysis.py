# /// script
# requires-python=">=3.9"
# dependencies = [
#     "pandas",
#     "numpy",
#     "matplotlib",
#     "seaborn",
#     "requests",
#     "openai",
#     "scikit-learn",
#     "tabulate",
#     "chardet",
#     "asyncio",
# ]
# ///

import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import httpx
import chardet
import time
import random
import asyncio

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
AIPROXY_TOKEN = "your_token_here"  # Replace with your actual token
MAX_ROWS = 10000  # Limit the number of rows to process
SAMPLE_SIZE = 5000  # Sample size for large datasets


def load_csv_data(file_path):
    """Load CSV data with encoding detection."""
    if not os.path.isfile(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    with open(file_path, 'rb') as file_handle:
        encoding_result = chardet.detect(file_handle.read())
    detected_encoding = encoding_result['encoding'] or 'utf-8'
    print(f"Detected file encoding: {detected_encoding}")

    try:
        df = pd.read_csv(file_path, encoding=detected_encoding)
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        sys.exit(1)

    # Sample if the dataset is too large
    if len(df) > MAX_ROWS:
        df = df.sample(n=SAMPLE_SIZE, random_state=1)  # Sample with a fixed seed for reproducibility
    return df


def perform_data_analysis(data_frame):
    """Perform basic data analysis."""
    if data_frame.empty:
        print("Error: Dataset is empty.")
        sys.exit(1)

    numeric_data_frame = data_frame.select_dtypes(include=['number'])  # Select only numeric columns
    analysis_results = {
        'summary': data_frame.describe(include='all').to_dict(),
        'missing_values': data_frame.isnull().sum().to_dict(),
        'correlation': numeric_data_frame.corr().to_dict()  # Compute correlation only on numeric columns
    }
    print("Data analysis complete.")
    return analysis_results


def create_visualizations(data_frame):
    """Generate and save visualizations."""
    sns.set(style="whitegrid")
    numeric_columns = data_frame.select_dtypes(include=['number']).columns
    if numeric_columns.empty:
        print("No numeric columns found for visualization.")
        return

    output_dir = "visualizations"
    os.makedirs(output_dir, exist_ok=True)

    for numeric_column in numeric_columns[:3]:  # Limit to first 3 numeric columns for visualization
        plt.figure()
        sns.histplot(data_frame[numeric_column].dropna(), kde=True)
        plt.title(f'Distribution of {numeric_column}')
        file_name = os.path.join(output_dir, f'{numeric_column}_distribution.png')
        plt.savefig(file_name, dpi=150)  # Reduce resolution to speed up saving
        print(f"Saved distribution plot: {file_name}")
        plt.close()


async def generate_analysis_narrative(analysis_data):
    """Generate narrative using LLM."""
    headers = {
        'Authorization': f'Bearer {AIPROXY_TOKEN}',
        'Content-Type': 'application/json'
    }
    prompt_message = f"Provide a detailed analysis based on the following data summary: {analysis_data}"
    request_data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt_message}]
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(API_URL, headers=headers, json=request_data, timeout=30.0)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
    except httpx.HTTPStatusError as http_error:
        print(f"HTTP error occurred: {http_error}")
    except httpx.RequestError as request_error:
        print(f"Request error occurred: {request_error}")
    except Exception as general_error:
        print(f"An unexpected error occurred: {general_error}")
    return "Narrative generation failed due to an error."


def main_process(file_path):
    start_time = time.time()  # Start timing
    print("Starting autolysis process...")

    data_frame = load_csv_data(file_path)
    print("Dataset loaded successfully.")

    print("Analyzing data...")
    analysis_data = perform_data_analysis(data_frame)

    print("Generating visualizations...")
    create_visualizations(data_frame)

    print("Generating narrative...")
    narrative_output = asyncio.run(generate_analysis_narrative(analysis_data))

    if narrative_output != "Narrative generation failed due to an error.":
        with open('README.md', 'w') as readme_file:
            readme_file.write(narrative_output)
        print("Narrative successfully written to README.md.")
    else:
        print("Narrative generation failed. Skipping README creation.")

    elapsed_time = time.time() - start_time
    print(f"Autolysis process completed in {elapsed_time:.2f} seconds.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <file_path>")
        sys.exit(1)
    main_process(sys.argv[1])
