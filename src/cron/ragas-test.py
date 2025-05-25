import pandas as pd
from dotenv import load_dotenv, dotenv_values
import os

from langchain_openai import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from sentence_transformers import SentenceTransformer

import qdrant_client

load_dotenv()
config = dotenv_values(".env")
os.environ["OPENAI_API_KEY"] = config["OPENAI_API_KEY"]

from ragas.metrics import answer_relevancy, faithfulness, context_recall, answer_correctness
from ragas.metrics.critique import harmfulness
from ragas import evaluate
from datasets import Dataset

threshold = 0.4
relevancy_threshold = 0.8
dont_know_response = "I am unable to answer this question. Please email admissions@eastsideprep.org"

client = qdrant_client.QdrantClient(
    url=config["QDRANT_URL"],
    api_key=config["QDRANT_API_KEY"],
)
print("Connected to QDrant")

chat_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful representative of Eastside Preparatory School. Don't say \"based on the given context\" or \"based on the information provided\" or \"Human\". You are promoting Eastside Preparatory School, so say \"our\" not \"their\". "),
        ("system", "Don't offer application advice on how to get into EPS, but do offer information about EPS from the given context. Don't discuss anything related to finances or money. If the user asks about finances or any other restricted content, please respond with " + dont_know_response),
        ("human", "Answer the question based only on the following context: {context} Question: {question}. Keep your answer a maximum of 50 words long, and a minimum of 40 words long."),
    ]
)

retry_prompt =  ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful representative of Eastside Preparatory School. Don't say \"based on the given context\" or \"based on the information provided\" or \"Human\". You are promoting Eastside Preparatory School, so say \"our\" not \"their\". "),
        ("system", "Don't offer application advice on how to get into EPS, but do offer information about EPS from the given context. Don't discuss anything related to finances or money. If the user asks about finances or any other restricted content, please respond with " + dont_know_response),
        ("system", "You were told to answer the question based only on the following context: {context} Question: {question}."),
        ("human", "Here was your previous answer: {answer}. It was {type}, so please rephrase using only the context. Keep your answer a maximum of 50 words long, and a minimum of 40 words long. Answer only with the rephrased answer"),
    ]
)

chat_model = ChatOpenAI(openai_api_key=config["OPENAI_API_KEY"], model="gpt-3.5-turbo-0125")

encoder = SentenceTransformer("all-MiniLM-L6-v2")
print("Sentence Transformers loaded")

def load_set(path):
    return pd.read_csv(path)

def generate_response(query):
    query_vector = encoder.encode(query).tolist()
    hits = client.search(
        collection_name="admissions_data",
        query_vector=query_vector,
        limit=3,
    )
   
    context = ""
    num_hits = 0
    
    for hit in hits:
        if (hit.score >= threshold):
            context += "\n\n" + str(hit.payload['content'])
            num_hits +=1
    
    response = ""
    relevancy = 0
    harmfulness = 0

    if num_hits == 0 or query == "":
        response = dont_know_response
    else:
        messages = chat_prompt.format_messages(context=context, question=query)
        response = chat_model.invoke(messages).content

        relevancy, harmfulness = ragas_inference(query, response, context)
        
        if (relevancy <= relevancy_threshold or harmfulness != 0):
            if (relevancy <= relevancy_threshold):
                messages = retry_prompt.format_messages(context=context, question=query, answer=response, type="irrelevant")
                response = chat_model.invoke(messages).content
            else:
                messages = retry_prompt.format_messages(context=context, question=query, answer=response, type="harmful")
                response = chat_model.invoke(messages).content
            
            # Naive 1x recursion
            relevancy, harmfulness = ragas_inference(query, response, context)
            if (relevancy <= relevancy_threshold or harmfulness != 0):
                response = dont_know_response
        
    return response, context, relevancy, harmfulness

metrics = [
    answer_relevancy,
    harmfulness
]

def ragas_inference(question, answer, context):
    score = evaluate(Dataset.from_dict({'question': [question], 'answer': [answer], 'contexts': [[context]]}), metrics=metrics)
    df = score.to_pandas()
    return df['answer_relevancy'].iloc[0].item(), df['harmfulness'].iloc[0].item()

def generate_test_set_with_responses(real_set_path, save_location):
    test_set = load_set(real_set_path)
    for idx, test_case in test_set.iterrows():
        answer, context, relevancy, harmfulness = generate_response(test_case["question"])
        test_case["answer"] = answer
        test_case["context"] = context
        test_case["relevancy"] = relevancy
        test_case["harmfulness"] = harmfulness
        print(idx)
    test_set.to_csv(save_location)

generate_test_set_with_responses('././data/testdata.csv', '././data/completedtests.csv')