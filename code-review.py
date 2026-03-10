import os
import openai
from openai import OpenAI

#Pulling OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

#Setting API Key inside the openai_client object
openai_client = OpenAI(api_key=OPENAI_API_KEY)

#Getting file content from diff.txt
with open("difference.txt","r") as diff_file:
    diff = diff_file.read()
print(diff)
print(diff)
chat_response = ""
#Response object by querying ChatGPT
try:
    response = openai_client.responses.create(
        model="gpt-5.1-codex-mini",
        input=[
            {"role": "system", "content": "You are a senior software engineer tasked with performing code reviews for a web based django project. Provide concise and actionable feedback."},
            {"role":"user", "content": f"Provide concise and actionable feedback for this code, make sure to mention the file name and line number for each suggestion. Here is the pull request diff:\n{diff}"}
        ]

    )
    chat_response = response.output_text
except openai.RateLimitError:
    chat_response = "Querying ChatGPT Failed, AI Code Review Unavailable"

#Saving response into the feedback.txt file
with open("feedback.txt","w") as feedback_file:
    feedback_file.write(chat_response)
