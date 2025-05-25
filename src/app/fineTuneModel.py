from openai import OpenAI

class FineTuneModel:
    client = OpenAI()
    prompt = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": '''You are an official admissions representative for Eastside Preparatory School. Your role is to provide precise, accurate, and highly relevant answers to prospective students' questions regarding admissions requirements, deadlines, programs, financial aid, and other related topics.
                                - Don't respond to irrelevant or sensitive questions/topics. Maintain a formal and professional tone at all times. "
                                - If a question is unclear, ask for clarification rather than assuming.
                                - If information is unavailable, politely direct the user to the appropriate official sources. "
                                - Do not provide speculative or unverifiable answers.'''  
                },
                {
                    "type": "text",
                    "text": ""  
                }
            ]
        }
    ]

    @staticmethod
    def generate_response(query):
        FineTuneModel.prompt[0]["content"][1]["text"] = query
        final_prompt = FineTuneModel.prompt
        response = FineTuneModel.client.chat.completions.create(
            model="ft:gpt-4o-mini-2024-07-18:personal:edgar-chatbot-v2:BFv4T1TG",
            messages=final_prompt,
        )

        return response.choices[0].message.content