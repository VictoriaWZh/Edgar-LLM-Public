import flask
from flask import request, render_template, jsonify
from flask_cors import CORS
from markupsafe import escape

from dotenv import load_dotenv, dotenv_values
from .dataLogs import DataLogs
import os
import json
import ast
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import ChatOpenAI

# Loading .env values such as API keys
load_dotenv()
config = dotenv_values(".env")

# Ensure OPENAI_API_KEY is set
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Missing OPENAI_API_KEY in environment variables")

os.environ["OPENAI_API_KEY"] = api_key

# Initialize OpenAI GPT-4o Mini model
chat_model = ChatOpenAI(model_name="gpt-4o-mini")
user_history = []

dont_know_response = (
    "I am unable to respond to your query. Please ask a relevant question to the "
    "EDGAR Chatbot. If you have application-specific questions, contact "
    "admissions@eastsideprep.org"
)

# Load admissions context data
with open('data/admissions_chunked.json', encoding="utf-8") as file:
    data = json.load(file)
    db = json.dumps(data, indent=4)

# Build the system and human prompt templates
chat_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful representative of Eastside Preparatory School. "
     "Don't say 'based on the given context' or 'Human'. "
     "You are promoting Eastside Preparatory School, so say 'our' not 'their'. "
     "Don't offer application advice on how to get into EPS, but do offer "
     "information about EPS from the given context. "
     "Don't discuss anything related to finances or money. "
     "If the user asks about finances or any other restricted content, "
     "respond with: "
     f"{{{{\"source\": [], \"response\": \"{dont_know_response}\"}}}}"
    ),

    ("system",
     "You are given three things:\n"
     "1. A plaintext JSON database with entries like:\n"
     "   {{{{\"source\": \"<url>\", \"content\": \"<text snippet>\"}}}}\n"
     "2. A single user question related to school admissions.\n\n"
     "Read all context entries.\n"
     "- Synthesize the most accurate, relevant, and concise response using ONLY the context.\n"
     "- Combine info from multiple sources if helpful.\n"
     "- If the question is irrelevant, inappropriate, or unanswerable, "
     "respond exactly with:\n"
     f"{{{{\"source\": [], \"response\": \"{dont_know_response}\"}}}}"
     "Only return a dictionary in this format:\n"
     "{{{{\"source\": [list of referenced urls], \"response\": \"[synthesized answer]\"}}}}\n"
     "3. A list of dictionaries between you and the user as conversation history of user questions and your responses."
     "- Use the conversation history if necessary to guide your ability to answer the user's questions."
     "Keep your answer a maximum of 50 words long and a minimum of 40 words."
     "Never explain your reasoning or return additional text."
    ),

    ("human",
     "Answer the question based only on the JSON Database: {context} "
     "Question: {question}. "
     "History: {history}"
    ),
])

# def evaluate_input(query):
#     """Check the toxicity of input query"""
#     toxicity_scores = Detoxify("original").predict([query])  # Expecting a list
#     harmfulness = toxicity_scores["toxicity"][0]  # Get toxicity score
 
#     if harmfulness > 0.5:
#         return "I'm afraid I cannot respond to that. Please ask appropriate questions that are not harmful."
#     return ""

# Get response function
def get_response(query: str, history: list) -> str:
    # input_check = evaluate_input(query)
    # if input_check != "":
    #     print("Response deemed harmful.")
    #     return [], input_check
    messages = chat_prompt.format_messages(context=db, question=query, history=history)
    print("Prompt formatted.")
    print(messages)
    # Invoke the OpenAI model
    ai_response = chat_model.invoke(messages)
    parsed = ast.literal_eval(ai_response.content)
    return parsed["source"], parsed["response"]

# Initialize Flask
app = flask.Flask(__name__)
CORS(app)
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/')
def home():
    print("Home route accessed.")
    return render_template('index.html')

@app.route('/data')
def data_route():
    print("Data route accessed.")
    return render_template('data.html')

@app.route('/api/chat/')
def chat():
    temp_dict = {"user_query": None, "response": None}
    print("Chat endpoint accessed.")
    query = request.args.get('query')
    temp_dict["user_query"] = query
    print(f"User query: {query}")
    user_message = escape(query)

    # Generate response
    sources, response_message = get_response(user_message, user_history[-5:])
    temp_dict["response"] = response_message
    user_history.append(temp_dict)
    print(f"Response generated: {response_message}")

    try:
        # Create log record
        log_record = {
            'timestamp': datetime.now(),
            'user_query': user_message,
            'response': response_message,
            'sources': sources,
            'harmfulness_score': harmfulness,
            'user_history': user_history[-5:]  # Last 5 interactions
        }
        
        # Log to MongoDB
        DataLogs.write_mongodb(log_record)
        
        resp = jsonify({
            'model_response': response_message,
            'sources': sources  # Adjust if you extract sources in future
        })
        resp.headers.add('Access-Control-Allow-Origin', '*')
        return resp
    except Exception as e:
        print(f"Error during response creation: {e}")
        return jsonify({'error': 'Failed to create response'})

if __name__ == '__main__':
    app.run()