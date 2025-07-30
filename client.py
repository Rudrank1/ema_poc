import requests
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
output_parser = StrOutputParser()
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant that can answer human queries."),
    ("human", "Explain what the {policy_name} S3 policy does in simple terms."),
])

def explain_policy(policy_name):
    chain = prompt | model | output_parser
    return chain.invoke({"policy_name": policy_name})

def prompt_bool(prompt):
    while True:
        val = input(f"{prompt} (y/n): ").strip().lower()
        if val in ("y", "yes"): return True
        if val in ("n", "no"): return False
        print("Please enter 'y' or 'n'.")

def prompt_tags():
    tags = {}
    print("Enter tags as key=value (empty to finish):")
    while True:
        entry = input("Tag: ").strip()
        if not entry:
            break
        if '=' not in entry:
            print("Invalid format. Use key=value.")
            continue
        k, v = entry.split('=', 1)
        tags[k.strip()] = v.strip()
    return tags

def prompt_public_access_block():
    pab = {}
    print("Configure Public Access Block settings:")
    for key in [
        'BlockPublicAcls',
        'IgnorePublicAcls',
        'BlockPublicPolicy',
        'RestrictPublicBuckets']:
        pab[key] = prompt_bool(f"{key}?")
    return pab

def main():
    print("=== S3 Bucket Creation Client ===")
    bucket_name = input("Bucket name: ").strip()
    versioning = prompt_bool("Enable versioning?")
    tags = prompt_tags()
    pab = prompt_public_access_block() if prompt_bool("Configure Public Access Block?") else None
    policy = None
    if prompt_bool("Attach a bucket policy?"):
        if prompt_bool("Would you like an explanation of a common policy?"):
            policy_name = input("Enter policy name to explain (e.g., 'Block Public ACLs'): ").strip()
            print("Gemini explanation:")
            print(explain_policy(policy_name))
        policy = input("Paste policy JSON (or leave blank to skip): ").strip() or None

    payload = {
        "bucket_name": bucket_name,
        "versioning": versioning,
        "tags": tags if tags else None,
        "public_access_block": pab,
        "policy": policy
    }
    resp = requests.post("http://localhost:8000/create_bucket", json=payload)
    print("\nMCP Server Response:")
    print(resp.json())

if __name__ == "__main__":
    main()
