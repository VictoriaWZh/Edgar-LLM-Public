from dotenv import dotenv_values
from datetime import datetime, timedelta
import qdrant_client
from langchain_groq import ChatGroq
from langchain.prompts.chat import ChatPromptTemplate
config = dotenv_values(".env")

chat_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "What are the three most frequently asked questions in:\n{questions}\n? Questions that are phrased similarly can be combined. Only respond with three questions.")
    ]
)
chat_model = ChatGroq(temperature=0, model_name="mixtral-8x7b-32768")

def questions_string(data_array):
    questions = []
    for item in data_array:
        questions.append(item["Question"])
    questions_list = "\n".join(questions)
    return questions_list

def questions_to_chatgpt(questions_string):
    messages = chat_prompt.format_messages(questions=questions_string)
    response = chat_model.invoke(messages).content

    return response

client = qdrant_client.QdrantClient(
    url=config["QDRANT_URL"],
    api_key=config["QDRANT_API_KEY"],
)


scroll = client.scroll(
    collection_name="edgar_questions"
)
out = []
for point in scroll[0]:
    point = point.payload
    d = datetime.fromisoformat(point["Timestamp"])
    if d > (datetime.now() - timedelta(30)) and d < (datetime.now()):
        out.append(point)

questions_str = questions_string(out)
response = questions_to_chatgpt(questions_str)
print(response)

sender = 'edgarllm.noreply@gmail.com'
receivers = ["awang28@eastsideprep.org", "vzhang@eastsideprep.org", "zbabbar@eastsideprep.org", "jchi@eastsideprep.org", "cschenk@eastsideprep.org"]
message = """\
    This is your monthly report for Edgar-LLM. Here are the most commonly asked questions:
    {response}
    """

