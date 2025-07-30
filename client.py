import requests
import os
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")


model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
output_parser = StrOutputParser()


# Conversational prompt for the main chatbot
conversation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are Ema, a helpful AWS S3 expert assistant. You help users create and configure S3 buckets through natural conversation.


Your personality:
- Friendly, knowledgeable, and patient
- Explain technical concepts in simple terms
- Ask clarifying questions when needed
- Provide helpful suggestions and best practices
- Guide users through the bucket creation process step by step


You can help with:
- Understanding S3 bucket concepts
- Choosing bucket names and settings
- Explaining security configurations
- Suggesting policies and access controls
- Troubleshooting issues


Current context: {context}


User's bucket configuration so far:
- Bucket name: {bucket_name}
- Versioning: {versioning}
- Tags: {tags}
- Public access block: {public_access_block}
- Policy: {policy}


Respond naturally and conversationally. If the user wants to create the bucket, ask for confirmation and then proceed.""",
        ),
        ("human", "{user_message}"),
    ]
)


# Policy explanation prompt
policy_explanation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an AWS S3 expert assistant. Explain S3 policies and concepts in simple, clear terms.
   Provide practical examples and best practices. Keep explanations concise but informative.""",
        ),
        (
            "human",
            "Explain what the {policy_name} S3 policy does in simple terms. Include when to use it and any important considerations.",
        ),
    ]
)


# Policy generation prompt
policy_generation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an AWS S3 security expert. Based on the user's requirements, suggest appropriate S3 bucket policies.
   You must return ONLY valid JSON policy documents. Do not include any explanations, markdown formatting, or additional text.
   The response must start with an opening brace and be valid JSON that can be parsed directly.""",
        ),
        (
            "human",
            "Create an S3 bucket policy for: {requirements}. Return ONLY the JSON policy document, no other text.",
        ),
    ]
)


class S3BucketAssistant:
    def __init__(self):
        self.bucket_name = None
        self.versioning = False
        self.tags = {}
        self.public_access_block = None
        self.policy = None
        self.context = "Starting a new conversation about S3 bucket creation."
        self.name_confirmed = False  # Track if bucket name has been confirmed

    def get_config_summary(self):
        """Get a summary of current configuration"""
        summary = []
        if self.bucket_name:
            summary.append(f"Bucket name: {self.bucket_name}")
        summary.append(f"Versioning: {'Enabled' if self.versioning else 'Disabled'}")
        summary.append(f"Tags: {len(self.tags)} tags" if self.tags else "Tags: None")
        summary.append(
            f"Public access block: {'Configured' if self.public_access_block else 'Default'}"
        )
        summary.append(f"Policy: {'Attached' if self.policy else 'None'}")
        return summary

    def validate_bucket_name(self, name):
        """Validate S3 bucket name"""
        if not name:
            return False, "Bucket name cannot be empty."

        if len(name) < 3 or len(name) > 63:
            return False, "Bucket name must be between 3 and 63 characters."

        if not re.match(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$", name):
            return (
                False,
                "Bucket name can only contain lowercase letters, numbers, dots, and hyphens. It must start and end with a letter or number.",
            )

        if name.startswith("xn--") or name.endswith("-s3alias"):
            return False, "Bucket name cannot start with 'xn--' or end with '-s3alias'."

        return True, "Valid bucket name."

    def extract_bucket_name(self, text):
        """Extract potential bucket name from user text"""
        # Common words to ignore when extracting bucket names
        ignore_words = {
            "want",
            "create",
            "new",
            "bucket",
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "must",
            "shall",
            "like",
            "to",
            "name",
            "it",
        }

        # Look for patterns that might be bucket names
        words = text.split()
        for word in words:
            # Remove punctuation and check if it looks like a bucket name
            clean_word = re.sub(r"[^\w.-]", "", word.lower())

            # Skip common words and very short words
            if clean_word in ignore_words or len(clean_word) < 3:
                continue

            if 3 <= len(clean_word) <= 63 and re.match(
                r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$", clean_word
            ):
                return clean_word
        return None

    def extract_bucket_name_from_context(self, text):
        """Extract bucket name with better context awareness"""
        # Common words to ignore when extracting bucket names
        ignore_words = {
            "want",
            "create",
            "new",
            "bucket",
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "must",
            "shall",
            "like",
            "to",
            "name",
            "it",
            "i",
            "am",
            "wanting",
            "trying",
            "going",
        }

        # Look for the longest word that matches bucket name pattern
        words = text.split()
        potential_names = []

        for word in words:
            # Remove punctuation and check if it looks like a bucket name
            clean_word = re.sub(r"[^\w.-]", "", word.lower())

            # Skip common words and very short words
            if clean_word in ignore_words or len(clean_word) < 3:
                continue

            if 3 <= len(clean_word) <= 63 and re.match(
                r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$", clean_word
            ):
                potential_names.append(clean_word)

        # Return the longest potential name (most likely to be the actual bucket name)
        if potential_names:
            return max(potential_names, key=len)

        return None

    def extract_tags(self, text):
        """Extract tags from user text"""
        tags = {}
        # Look for key=value patterns
        tag_pattern = r"(\w+)\s*=\s*([^\s,]+)"
        matches = re.findall(tag_pattern, text)
        for key, value in matches:
            tags[key] = value
        return tags

    def generate_policy(self, requirements):
        """Generate policy using AI"""
        try:
            chain = policy_generation_prompt | model | output_parser
            response = chain.stream({"requirements": requirements})

            # Clean up the response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # Validate JSON
            json.loads(response)
            return response
        except Exception as e:
            return None

    def explain_policy(self, policy_name):
        """Get AI explanation of S3 policies"""
        try:
            chain = policy_explanation_prompt | model | output_parser
            return chain.stream({"policy_name": policy_name})
        except Exception as e:
            return f"Sorry, I couldn't explain that policy right now. Error: {str(e)}"

    def create_bucket(self):
        """Create the bucket using the MCP server"""
        if not self.bucket_name:
            return False, "No bucket name specified."

        payload = {
            "bucket_name": self.bucket_name,
            "versioning": self.versioning,
            "tags": self.tags if self.tags else None,
            "public_access_block": self.public_access_block,
            "policy": self.policy,
        }

        try:
            resp = requests.post("http://localhost:8000/create_bucket", json=payload)
            result = resp.json()

            if resp.status_code == 200:
                return True, f"✅ Bucket '{self.bucket_name}' created successfully!"
            else:
                return (
                    False,
                    f"❌ Failed to create bucket: {result.get('detail', 'Unknown error')}",
                )

        except requests.exceptions.ConnectionError:
            return (
                False,
                "❌ Could not connect to the MCP server. Make sure it's running on http://localhost:8000",
            )
        except Exception as e:
            return False, f"❌ An error occurred: {str(e)}"

    def chat(self, user_message):
        """Process user message and return response"""
        user_lower = user_message.lower()

        # If no bucket name is set yet, ask for it explicitly
        if not self.bucket_name and not self.name_confirmed:
            # Look for explicit bucket name mentions
            if any(
                phrase in user_lower
                for phrase in [
                    "bucket name",
                    "call it",
                    "name it",
                    "named",
                    "like to name",
                ]
            ):
                # Try to extract a bucket name from the message
                bucket_name = self.extract_bucket_name_from_context(user_message)
                if bucket_name:
                    is_valid, message = self.validate_bucket_name(bucket_name)
                    if is_valid:
                        self.bucket_name = bucket_name
                        self.name_confirmed = True
                        return f"Perfect! I've set the bucket name to '{self.bucket_name}'. What would you like to configure next?"
                    else:
                        return f"I see '{bucket_name}' as a potential bucket name, but {message} Could you suggest a different name?"

            # If no clear bucket name found, ask explicitly
            return "I'd be happy to help you create an S3 bucket! What would you like to name it? (Please provide a unique name between 3-63 characters, using only lowercase letters, numbers, dots, and hyphens)"

        # Handle bucket name confirmation if not confirmed yet
        if self.bucket_name and not self.name_confirmed:
            # If user confirms the name or provides a new one
            if any(
                word in user_lower
                for word in ["yes", "correct", "right", "good", "ok", "sure"]
            ):
                self.name_confirmed = True
                return f"Great! The bucket name is confirmed as '{self.bucket_name}'. What would you like to configure next?"
            elif any(
                word in user_lower for word in ["no", "wrong", "change", "different"]
            ):
                self.bucket_name = None
                return "No problem! What would you like to name your bucket instead?"
            else:
                # Try to extract a new bucket name
                bucket_name = self.extract_bucket_name_from_context(user_message)
                if bucket_name:
                    is_valid, message = self.validate_bucket_name(bucket_name)
                    if is_valid:
                        self.bucket_name = bucket_name
                        self.name_confirmed = True
                        return f"Perfect! I've updated the bucket name to '{self.bucket_name}'. What would you like to configure next?"
                    else:
                        return f"I see '{bucket_name}' as a potential bucket name, but {message} Could you suggest a different name?"

        # Handle explicit bucket name changes (only if name is already confirmed)
        if self.name_confirmed and any(
            phrase in user_lower
            for phrase in ["change name", "rename", "different name", "should be"]
        ):
            # Extract potential new name
            bucket_name = self.extract_bucket_name_from_context(user_message)
            if bucket_name:
                is_valid, message = self.validate_bucket_name(bucket_name)
                if is_valid:
                    old_name = self.bucket_name
                    self.bucket_name = bucket_name
                    return f"Perfect! I've changed the bucket name from '{old_name}' to '{self.bucket_name}'. What else would you like to configure?"
                else:
                    return f"I see '{bucket_name}' as a potential bucket name, but {message} Could you suggest a different name?"

        # Extract tags if mentioned
        if "tag" in user_lower or "=" in user_message:
            new_tags = self.extract_tags(user_message)
            if new_tags:
                self.tags.update(new_tags)
                return f"Great! I've added the tags: {new_tags}. What else would you like to configure?"

        # Handle versioning
        if any(word in user_lower for word in ["version", "versioning"]):
            if "enable" in user_lower or "yes" in user_lower or "on" in user_lower:
                self.versioning = True
                return "Perfect! I've enabled versioning for your bucket. This will help protect against accidental deletions and overwrites. What else would you like to configure?"
            elif "disable" in user_lower or "no" in user_lower or "off" in user_lower:
                self.versioning = False
                return "Got it! Versioning will remain disabled. What else would you like to configure?"

        # Handle public access
        if "public" in user_lower and "access" in user_lower:
            if "block" in user_lower or "restrict" in user_lower:
                self.public_access_block = {
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                }
                return "Excellent! I've configured the public access block settings to keep your bucket secure. What else would you like to configure?"

        # Handle policy requests
        if "policy" in user_lower:
            if "explain" in user_lower or "what" in user_lower:
                policy_words = [
                    "block public",
                    "read only",
                    "write",
                    "cross account",
                    "cloudfront",
                ]
                for policy in policy_words:
                    if policy in user_lower:
                        return self.explain_policy(policy.title())
                return "I can explain various S3 policies like 'Block Public Access', 'Read Only Access', 'Write Access', etc. Which one would you like me to explain?"

        # Handle bucket creation
        if any(
            word in user_lower
            for word in ["create", "make", "build", "set up", "ready", "done", "finish"]
        ):
            if not self.bucket_name or not self.name_confirmed:
                return "I need to confirm your bucket name first. What would you like to name your bucket?"

            summary = self.get_config_summary()
            response = f"Perfect! I'm ready to create your bucket. Here's what I have configured:\n"
            for item in summary:
                response += f"• {item}\n"
            response += "\nShould I go ahead and create the bucket?"
            return response

        # Handle general questions about tags
        if "tag" in user_lower and ("what" in user_lower or "explain" in user_lower):
            return """Tags are key-value pairs you can attach to your S3 bucket for organization and cost tracking.
           Examples: Environment=Production, Project=MyApp, Owner=TeamA
           Would you like to add some tags to your bucket?"""

        # Generate AI response for other queries
        try:
            chain = conversation_prompt | model | output_parser
            response = chain.stream(
                {
                    "context": self.context,
                    "bucket_name": self.bucket_name or "Not set",
                    "versioning": "Enabled" if self.versioning else "Disabled",
                    "tags": str(self.tags) if self.tags else "None",
                    "public_access_block": (
                        "Configured" if self.public_access_block else "Default"
                    ),
                    "policy": "Attached" if self.policy else "None",
                    "user_message": user_message,
                }
            )
            return response
        except Exception as e:
            return (
                f"Sorry, I'm having trouble processing that right now. Error: {str(e)}"
            )


def main():
    print("🤖 Welcome to Ema, your S3 Bucket Assistant!")
    print(
        "I'm here to help you create and configure S3 buckets through natural conversation."
    )
    print(
        "You can ask me questions, tell me what you want, and I'll guide you through the process."
    )
    print("Type 'quit' or 'exit' to end our conversation.")
    print("=" * 60)

    assistant = S3BucketAssistant()

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ["quit", "exit", "bye"]:
                print("\nEma: Thanks for chatting with me! Have a great day! 👋")
                break

            if not user_input:
                continue

            response = assistant.chat(user_input)
            print(f"\nEma: {response}")

            # Check if user wants to create the bucket
            if "Should I go ahead and create the bucket?" in response:
                create_input = input("\nYou: ").strip().lower()
                if create_input in ["yes", "y", "sure", "ok", "go ahead", "create"]:
                    success, message = assistant.create_bucket()
                    print(f"\nEma: {message}")
                    if success:
                        print(
                            "\nEma: 🎉 Your bucket has been created successfully! Is there anything else you'd like to know about S3 buckets?"
                        )
                    else:
                        print(
                            "\nEma: Let me know if you'd like to try again or if you have any questions!"
                        )
                else:
                    print(
                        "\nEma: No problem! Let me know if you want to change anything or if you have other questions."
                    )

        except KeyboardInterrupt:
            print("\n\nEma: Goodbye! 👋")
            break
        except Exception as e:
            print(f"\nEma: Sorry, something went wrong: {str(e)}")


if __name__ == "__main__":
    main()
