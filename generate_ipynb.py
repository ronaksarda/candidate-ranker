import json
import os

files_to_include = [
    "requirements.txt",
    "check_tech.py",
    "data_loader.py",
    "download_model.py",
    "embedding_engine.py",
    "plausibility_filter.py",
    "profile_builder.py",
    "reasoning_generator.py",
    "scorer.py",
    "validate_submission.py",
    "main.py"
]

cells = []

# Title cell
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": ["# Redrob Candidate Ranking Pipeline (Latest Version)\n", "This notebook contains the latest offline ranking pipeline with updated plausibility filters."]
})

for fname in files_to_include:
    if os.path.exists(fname):
        with open(fname, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Split into lines and append newline to match Jupyter format, except for the last line if empty
        lines = content.split('\n')
        source = [f"%%writefile {fname}\n"] + [line + "\n" for line in lines[:-1]]
        if lines and lines[-1]:
            source.append(lines[-1])
            
        cells.append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": source
        })

# Setup and run cell
cells.append({
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "!pip install -r requirements.txt\n",
        "!python download_model.py\n",
        "!python main.py --candidates /content/candidates.jsonl --out /content/submission.csv\n"
    ]
})

notebook = {
    "cells": cells,
    "metadata": {
        "colab": {"name": "Redrob_Candidate_Ranking_Latest.ipynb"},
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 0
}

with open("Redrob_Candidate_Ranking_Latest.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2)

print("Generated Redrob_Candidate_Ranking_Latest.ipynb")
