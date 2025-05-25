import json

# Define the system message (constant for all entries)
SYSTEM_MESSAGE = (
    "You are an official admissions representative for Eastside Preparatory School. "
    "Your role is to provide precise, accurate, and highly relevant answers to prospective students' questions regarding admissions requirements, deadlines, programs, financial aid, and other related topics. "
    "Don't respond to irrelevant or sensitive questions/topics. Maintain a formal and professional tone at all times. "
    "If a question is unclear, ask for clarification rather than assuming. "
    "If information is unavailable, politely direct the user to the appropriate official sources. "
    "Do not provide speculative or unverifiable answers."
)

# Input JSON file name
input_filename = "data\\fine_tune_data_raw.json"

# Output JSONL file
output_filename = "data\\fine_tune_data_final.jsonl"

# Load the original JSON file
with open(input_filename, "r") as infile:
    data = json.load(infile)

# Open the output JSONL file for writing
with open(output_filename, "w") as outfile:
    for qa in data["qapairs"]:
        entry = {
            "messages": [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": qa["question"]},
                {"role": "assistant", "content": qa["answer"]}
            ]
        }
        # Write each entry as a separate JSON object on a new line
        outfile.write(json.dumps(entry) + "\n")

print(f"Successfully wrote {len(data['qapairs'])} entries to {output_filename}")
