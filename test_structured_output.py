import os
from openai import OpenAI
from pydantic import BaseModel

class Response(BaseModel):
    answer: str

client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_API_BASE')
)

try:
    response = client.beta.chat.completions.parse(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': 'Say hi'}],
        response_format=Response
    )
    print('Structured output works:', response.choices[0].message.parsed.answer)
except Exception as e:
    print(f'Structured output failed: {e}')
