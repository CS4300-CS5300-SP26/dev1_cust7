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

#Context Object
context = "You are a senior software engineer tasked with performing code reviews for a web based django project. Provide concise and actionable feedback."
#Prompt Object
prompt = f"Provide concise and actionable feedback for this code, make sure to mention the file name and line number, and display the line of code for each suggestion. Also output your response in markdown format. Here is the pull request diff:\n{diff}"
#Resoponse Object
chat_response = ""
#Response object by querying ChatGPT
try:
    response = openai_client.responses.create(
        model="gpt-5.1-codex-mini",
        input=[
            {"role": "system", "content": context},
            {"role":"user", "content": prompt}
        ]

    )
    chat_response = response.output_text
except openai.RateLimitError:
    chat_response = "Querying ChatGPT Failed, AI Code Review Unavailable"

#Stripping markdown leading part if there
if chat_response.startswith("```markdown"):
    chat_response = chat_response[len("```markdown"):]
elif chat_response.startswith("```"):
    chat_response = chat_response[len("```"):]

chat_response.stripped = chat_response.rstrip()
if chat_response.stripped.endswith("```"):
    chat_response = chat_response[:len(chat_response) - 3]
    
#Saving response into the feedback.txt file
with open("feedback.txt","w") as feedback_file:
    feedback_file.write("# AI Code Review\n\n")
    feedback_file.write(chat_response)
