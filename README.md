# VTT Summarizer

This script extracts structured information from VTT files such as Zoom meeting transcripts or closed captions and converts it into JSON and Markdown formats. The extracted information includes an overview, participants, main topics, key points, decisions, and action items.

It uses open source LLMs to handle the data extraction and summarization, ensuring everything can be run locally and without the need to share with third parties.

## Features

- **Meeting Notes Extraction:** Uses an LLM to extract detailed meeting notes from transcripts.
- **JSON and Markdown Output:** Saves the extracted information in both JSON and Markdown formats.
- **Data Cleaning:** Cleans and validates the extracted JSON using a second LLM.
- **File Handling:** Reads transcript files in WebVTT format.

## Requirements
- `ollama`
- `langchain-core`
- `langchain-community`
- `webvtt`
- `pydantic`
- `json`

## Usage

### Installation
First, install the required packages:

```bash
pip install langchain-core langchain-community webvtt-py pydantic ollama
```

In this script we are using [Microsoft's Phi-3](https://azure.microsoft.com/en-us/blog/introducing-phi-3-redefining-whats-possible-with-slms/) LLM given its size and speed. To download:

```bash
ollama pull phi3
```

### Running the Script
1. **Place your WebVTT file** in the appropriate directory. Update the file_path variable in the main function to point to your WebVTT file.
2. **Run the script:**

```bash
python summarizer.py
```

### Adjustments

There are two LLM prompts for this script. The `initial_prompt_template` is used to retrieved the content for the summary, while the `cleanup_prompt_template` is used as a mechanism to mitigate any issues with the JSON formatting. Feel free to adjust these based on your needs.

```python
initial_prompt_template = """
Please extract the following information from the meeting transcript and format it as a JSON object:

{format_instructions}

Transcript:
{transcript}

Your response must be a single, well-formed JSON object with keys: meeting_overview, participants, main_topics, key_points_decisions, and action_items.
...
"""

cleanup_prompt_template = """
Please clean and validate the following JSON. Ensure it is well-formed and remove any unnecessary text or errors. Only return the JSON object.

Raw JSON:
{raw_json}

Cleaned JSON:
"""
``
