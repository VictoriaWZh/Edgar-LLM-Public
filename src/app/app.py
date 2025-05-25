import flask
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from markupsafe import escape
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
 
from dotenv import load_dotenv, dotenv_values
 
from datetime import datetime
import os, re

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer

import qdrant_client

import smtplib
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase
from detoxify import Detoxify
from dataLogs import DataLogs
from fineTuneModel import FineTuneModel
 
# Loading .env values such as passwords and API keys
load_dotenv()
config = dotenv_values(".env")
api_key = os.getenv("GROQ_API_KEY")
os.environ["GROQ_API_KEY"] = config["GROQ_API_KEY"]
 
chat_model = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile")
 
# Hyperparams for response - do not touch
threshold = 0.4
relevancy_threshold = 0.3
fine_tune_threshold = 0.6
dont_know_response = "I am unable to respond to your query. Please ask a relevant question to the EDGAR Chatbot. If you have application-specific questions, contact admissions@eastsideprep.org"

h_count = 0
 
# Loading Qdrant client, our vector database
client = qdrant_client.QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)
print("Connected to QDrant")
 
# Chat Prompt given to Groq
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful representative of Eastside Preparatory School. Don't say \"based on the given context\" or \"based on the information provided\" or \"Human\". You are promoting Eastside Preparatory School, so say \"our\" not \"their\". "),
    ("system", "Don't offer application advice on how to get into EPS, but do offer information about EPS from the given context. Don't discuss anything related to finances or money. If the user asks about finances or any other restricted content, please respond with " + dont_know_response),
    ("human", "Answer the question based only on the following context: {context} Question: {question}. Keep your answer a maximum of 50 words long, and a minimum of 40 words long.")
])
 
retry_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful representative of Eastside Preparatory School. Don't say \"based on the given context\" or \"based on the information provided\" or \"Human\". You are promoting Eastside Preparatory School, so say \"our\" not \"their\". "),
    ("system", "Don't offer application advice on how to get into EPS, but do offer information about EPS from the given context. Don't discuss anything related to finances or money. If the user asks about finances or any other restricted content, please respond with " + dont_know_response),
    ("system", "You were told to answer the question based only on the following context: {context} Question: {question}."),
    ("human", "Here was your previous answer: {answer}. It was {type}, so please rephrase using only the context. Keep your answer a maximum of 50 words long, and a minimum of 40 words long. Answer only with the rephrased answer")
])
 
# Vector embedding model
encoder = SentenceTransformer("all-MiniLM-L6-v2")
print("Sentence Transformers loaded")

# This is an SMTP server to send emails when a bug in the code arises
def theres_a_bug(bug):
    print("Sending bug report...")
    s = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    s.login("victoriawzh@gmail.com", "")
    s.sendmail("victoriawzh@gmail.com", ["vzhang@eastsideprep.org"], bug)
    s.quit()
    print("Bug report sent.")
 
# Get response function
def get_response(query):
    print(f"get_response called with query: {query}")
    query_vector = encoder.encode(query).tolist()
    print("Query vector encoded.")

    hits = client.search(
        collection_name="admissions_data",
        query_vector=query_vector,
        limit=3
    )
    print(f"Search hits: {len(hits)}")

    context = ""
    deepeval_context = []
    sum_similarity = 0
    num_hits = 0
    avg_similarity = 0
    sources = set()  # Properly initialized as an empty set

    for hit in hits:
        print(f"Hit score: {hit.score}")
        if hit.score >= threshold:
            context += "\n\n" + str(hit.payload['content'])
            deepeval_context.append(str(hit.payload['content']))
            sum_similarity += hit.score
            num_hits += 1
            sources.add(hit.payload['source'])

    if num_hits > 0:
        avg_similarity = sum_similarity / num_hits

    # Default values
    response = dont_know_response
    responded = False
    relevancy = 0
    harmfulness = 0

    input_check = evaluate_input(query)
    if input_check == "":
    # Handle no hits or empty query
        if num_hits == 0 or query.strip() == "":
            print("No hits or empty query.")
            exp = FineTuneModel.generate_response(query)
            print(f"OpenAIs response: {exp}")
            print(f"Using Fine Tune model for {query}")
            query_vector = encoder.encode(query).tolist()
            print("Query vector encoded.")

            hit = client.search(
                collection_name="admissions_data",
                query_vector=query_vector,
                limit=1
            )
            print(hit[0].score)
            if hit[0].score > fine_tune_threshold:
                response = exp
            else:
                response = dont_know_response
            return response, num_hits, avg_similarity, responded, context, query_vector, sources, relevancy, harmfulness


        messages = chat_prompt.format_messages(context=context, question=query)
        print("Prompt formatted.")
        response = chat_model.invoke(messages).content
        print(f"Initial response: {response}")
        responded = True

        relevancy = deepeval(query, response, deepeval_context)
        print(f"Relevancy: {relevancy}, Harmfulness: {harmfulness}")

        # Handle harmful or irrelevant responses
        if harmfulness > 0:
            print("Response deemed harmful.")
            response = "I'm afraid I cannot respond to that. Please ask respectful questions that are not harmful."
        
        if relevancy <= relevancy_threshold:
            print("Low relevancy, retrying...")
            retry_type = "irrelevant" if relevancy <= relevancy_threshold else "harmful"
            messages = retry_prompt.format_messages(context=context, question=query, answer=response, type=retry_type)
            response = chat_model.invoke(messages).content
            relevancy = deepeval(query, response, deepeval_context)
            print(f"Retry response: {response}, New relevancy: {relevancy}, New harmfulness: {harmfulness}")

            if harmfulness > 0:
                response = "I'm afraid I cannot respond to that. Please ask respectful questions that are not harmful."

            if relevancy <= relevancy_threshold:
                response = dont_know_response
    else:
        response = input_check
    return response, num_hits, avg_similarity, responded, context, query_vector, sources, relevancy, harmfulness

# Ragas evaluate on one question
def deepeval(question, answer, context):
    sample = LLMTestCase(input=question, actual_output=answer, context=context)
    relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model="gpt-3.5-turbo")
    relevancy_metric.measure(sample)
    answer_relevancy = relevancy_metric.score
    return answer_relevancy

def evaluate_input(query):
    """Check the toxicity of input query"""
    toxicity_scores = Detoxify("original").predict([query])  # Expecting a list
    harmfulness = toxicity_scores["toxicity"][0]  # Get toxicity score
 
    if harmfulness > 0.5:
        return "I'm afraid I cannot respond to that. Please ask appropriate questions that are not harmful."
    return ""
 
app = flask.Flask(__name__)
CORS(app)
app.config['TEMPLATES_AUTO_RELOAD'] = True
print(app.config['TEMPLATES_AUTO_RELOAD']) # = True
 
@app.route('/')
def home():
    print("Home route accessed.")
    return render_template('index.html')
 
@app.route('/data')
def data():
    print("Data route accessed.")
    return render_template('data.html')
 
@app.route('/api/chat/')
def chat():
    print("Chat endpoint accessed.")
    query = request.args.get('query')
    print(f"User query: {query}")
    user_message = escape(query)
       
    response_message, num_hits, avg_similarity, responded, context, query_vec, sources, relevancy, harmfulness = get_response(user_message)
    print(f"Response generated: {response_message}")
 
    record = {
        'Timestamp': datetime.now(),
        'Question': user_message,
        'Response': response_message,
        'Average Similarity': avg_similarity,
        'Relevancy': relevancy,
        'Harmfulness': harmfulness,
        'Context': context,
        'Number of Hits': num_hits,
        'Responded': responded,
        'Sources': sorted(sources) if sources is not None else []
    }
    print(f"Record created: {record}")

    DataLogs.write_mongodb(record)

    try:
        response = jsonify({
            'model_response': response_message,
            'sources': sorted(sources) if sources is not None else []
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
    except Exception as e:
        print(f"Error during response creation: {e}")
   
    return response

if __name__ == '__main__':
    print("Starting Flask app...")

    test_mode = input("Run in terminal test mode? (y/n): ").strip().lower()
    if test_mode == 'y':
        while True:
            query = input("Enter your query (or type 'exit' to quit): ").strip()
            if query.lower() == 'exit':
                print("Exiting terminal test mode.")
                break
            
            # Call the get_response function directly
            response_message, num_hits, avg_similarity, responded, context, query_vec, sources, relevancy, harmfulness = get_response(query)
            
            # Print response details
            print(f"\nResponse: {response_message}")
            print(f"Number of Hits: {num_hits}")
            print(f"Average Similarity: {avg_similarity}")
            print(f"Relevancy: {relevancy}")
            print(f"Harmfulness: {harmfulness}")
            print(f"Sources: {sorted(sources)}\n")
    else:
        app.run()