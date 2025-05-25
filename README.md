# Welcome to Edgar-LLM
EdgAr-LLM stands for EPS digitally generated Admissions responses Large Language Model. We are building a chatbot to answer questions from EPS applicants, which will be displayed on the EPS website at some point in the future.

Contact: 

Amy Wang - [awang28@eastsideprep.org](mailto:awang28@eastsideprep.org)

Victoria Zhang - [vzhang@eastsideprep.org](mailto:vzhang@eastsideprep.org)

Zoe Babbar - [zbabbar@eastsideprep.org](mailto:zbabbar@eastsideprep.org)

# Setup
Clone the repository and run `pip install -r requirements.txt`. You can safely ignore the Numpy warning for SentenceTransformers. Obtain a .env file from Angad or whoever is maintaining this project at this time (possibly Mr. Clarke or Mr. Briggs). Run app.py to deploy the app.

# Architecture
![alt text](EdgarLLMArchitecture.png)
This is a pretty basic RAG architecture. 

First, we vectorize the user's query using [Sentence Transformers](https://arxiv.org/abs/1908.10084). To learn more about vectorization and NLP embeddings, please click [here](https://www.turing.com/kb/guide-on-word-embeddings-in-nlp).

The reason we vectorize the query is to compare it (semantically) to website data from EPS admissions. For this, we use [Qdrant](https://qdrant.tech/). We get the top 3 most relevant parts of the website. Then, we compare each chunk's cosine similarity with an arbitrary threshold (0.4).

We feed the chunks which pass the threshold test to ChatGPT. Then, we measure ChatGPT's hallucinations using [Deepeval](https://docs.confident-ai.com/).

# Future work
There are many ideas which the original team did not have time to implement. Here's a list:
 1. Change from ChatGPT-3.5 to Llama 3-70B on [Groq](https://wow.groq.com/). If Llama 3-400B is out by the time you are implementing this, please evaluate as well. At the time of writing, Llama3-70B on Groq is comparable in price to ChatGPT-3.5. 
 2. Re-ranking algorithms
 3. Custom search algorithms. Must be faster than QDrant (which is kind of impossible to do without years of time)
 4. Any other cool RAG implementations
 
 If you make any changes, make sure to rerun the ragas-test.py file and adjust parameters.

# Cost Considerations

Per input, we have around 500 tokens per call. We have 50 tokens per output (which was a set parameter). Per test, assume 1500 tokens per call.