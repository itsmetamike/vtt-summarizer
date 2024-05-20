import os
from datetime import datetime
import json
import webvtt
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.chat_models import ChatOllama
from langchain_core.exceptions import OutputParserException

# Define the data structure for the meeting notes using Pydantic
class MeetingNotes(BaseModel):
    meeting_overview: list = Field(description="Overview of the meeting")
    participants: list = Field(description="Participants in the meeting")
    main_topics: list = Field(description="Main topics discussed in the meeting (5-10 topics)")
    key_points_decisions: list = Field(description="Key points and decisions made in the meeting (25-50 points)")
    action_items: list = Field(description="Action items from the meeting (5-10 items)")

# Set up the prompt template for initial extraction
initial_prompt_template = """
Please extract the following information from the meeting transcript and format it as a JSON object:

{format_instructions}

Transcript:
{transcript}

Your response must be a single, well-formed JSON object with keys: meeting_overview, participants, main_topics, key_points_decisions, and action_items.
- For "meeting_overview", provide a list of strings summarizing the meeting.
- For "participants", provide a list of participant names as strings.
- For "main_topics", provide a list of a minimum of 5 to 10 strings representing the topics discussed in detail.
- For "key_points_decisions", provide a list of a minimum of 25 to 50 objects, each containing "decision" and "impact" keys with string values.
- For "action_items", provide a list of a minimum of 5 to 10 objects, each containing "item", "assigned_to", and "description" keys with string values.

Ensure that the response is valid JSON and includes detailed information for each key. Do not include any comments or additional text outside the JSON object. Do not omit items for brevity.
"""

# Set up the prompt template for JSON cleanup
cleanup_prompt_template = """
Please clean and validate the following JSON. Ensure it is well-formed and remove any unnecessary text or errors. Only return the JSON object.

Raw JSON:
{raw_json}

Cleaned JSON:
"""

# Initialize the LLM models
local_llm = 'phi3'
cleanup_llm = 'phi3'  # You can use the same or a different model for cleanup

print(f"Initializing LLM for extraction: {local_llm}")
model = ChatOllama(model=local_llm, temperature=0.1)

print(f"Initializing LLM for cleanup: {cleanup_llm}")
cleanup_model = ChatOllama(model=cleanup_llm, temperature=0)

def clean_json_output(raw_content):
    # Strip leading and trailing whitespace
    raw_content = raw_content.strip()

    # Remove code block markers if present
    if raw_content.startswith("```json"):
        raw_content = raw_content[7:]
    if raw_content.endswith("```"):
        raw_content = raw_content[:-3]

    # Split lines and remove comments (lines starting with `//`)
    lines = raw_content.split("\n")
    json_lines = [line for line in lines if not line.strip().startswith("//")]

    # Clean lines and ensure correct placement of commas
    cleaned_lines = []
    inside_array = False
    for line in json_lines:
        stripped_line = line.strip()
        if stripped_line.startswith("["):
            inside_array = True
        if inside_array and stripped_line.startswith("]"):
            inside_array = False

        if not inside_array:
            cleaned_lines.append(line)
        else:
            if line.endswith(","):
                cleaned_lines.append(line)
            else:
                cleaned_lines.append(line + ",")

    # Rejoin the cleaned lines, removing any final commas
    cleaned_json = "\n".join(cleaned_lines).replace(",]", "]").replace(",}", "}")

    return cleaned_json

def escape_curly_braces(text):
    return text.replace("{", "{{").replace("}", "}}")

def extract_meeting_notes(transcript):
    # Create the JSON output parser
    parser = JsonOutputParser(pydantic_object=MeetingNotes)

    # Get the format instructions and escape curly braces
    format_instructions = parser.get_format_instructions().replace("{", "{{").replace("}", "}}")

    # Create the initial prompt template
    prompt = PromptTemplate(
        template=initial_prompt_template,
        input_variables=["transcript"],
        partial_variables={"format_instructions": format_instructions},
    )

    # Format the initial prompt
    query = prompt.format(transcript=transcript)
    print("Query:", query)

    # Invoke the LLM to get the initial response
    response = model.invoke(query)
    raw_content = response.content
    print("Initial Response:", raw_content)

    # Clean the JSON output using another LLM
    cleanup_prompt = cleanup_prompt_template.format(raw_json=raw_content)
    cleanup_response = cleanup_model.invoke(cleanup_prompt)
    cleaned_raw_content = cleanup_response.content
    print("Cleaned Raw Content:", cleaned_raw_content)

    # Further clean the JSON output
    cleaned_json = clean_json_output(cleaned_raw_content)
    print("Final Cleaned JSON:", cleaned_json)

    # Parse the response
    try:
        result = parser.parse(cleaned_json)
        if isinstance(result, dict):
            # Ensure all required fields are present
            for key in MeetingNotes.__fields__.keys():
                if key not in result:
                    result[key] = []
            # Convert JSON strings back to lists/dictionaries
            for key, value in result.items():
                if isinstance(value, str):
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        pass
            result = MeetingNotes(**result)
    except (json.JSONDecodeError, KeyError, TypeError, OutputParserException) as e:
        print(f"Error parsing JSON response: {e}")
        result = None

    return result

def read_vtt_file(file_path):
    print("Reading transcript from file:", file_path)
    vtt = webvtt.read(file_path)
    transcript = " ".join([caption.text for caption in vtt])
    print("Transcript length:", len(transcript))
    return transcript

def save_json_to_file(data, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Extracted information saved to {file_path}")

def save_md_to_file(data, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(f"# Meeting Overview\n")
        for overview in data['meeting_overview']:
            f.write(f"- {overview}\n")
        f.write(f"\n## Participants\n")
        for participant in data['participants']:
            f.write(f"- {participant}\n")
        f.write(f"\n## Main Topics\n")
        for topic in data['main_topics']:
            f.write(f"- {topic}\n")
        f.write(f"\n## Key Points and Decisions\n")
        for point in data['key_points_decisions']:
            f.write(f"- **Decision**: {point['decision']}\n  **Impact**: {point['impact']}\n")
        f.write(f"\n## Action Items\n")
        for item in data['action_items']:
            f.write(f"- **Item**: {item['item']}\n  **Assigned to**: {item['assigned_to']}\n  **Description**: {item['description']}\n")
    print(f"Markdown file saved to {file_path}")

def main():
    file_path = r"../dfg-transcripts/2024/1Q24/MSF-Digital-Fashion-Wearables-for-Avatars-2024-01-08_16h02_audio_transcript.vtt" 
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    transcript = read_vtt_file(file_path)
    result = extract_meeting_notes(transcript)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    base_name = os.path.basename(file_path).replace(".vtt", "")
    
    json_file_path = f'./json/summary_{base_name}_{timestamp}.json'
    md_file_path = f'./md/summary_{base_name}_{timestamp}.md'
    
    print("\nExtracted Information:")
    if result:
        result_dict = result.dict()
        print(json.dumps(result_dict, indent=2))
        save_json_to_file(result_dict, json_file_path)
        save_md_to_file(result_dict, md_file_path)
    else:
        print("No valid information extracted.")
    print("Information extraction completed.")

if __name__ == "__main__":
    main()
