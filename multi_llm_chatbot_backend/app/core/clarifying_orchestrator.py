import re

class ClarifyingOrchestrator:
    def __init__(self):
        self.required_fields = ["issue", "urgency", "product"]
        self.collected_info = {}

    def is_input_complete(self):
        return all(field in self.collected_info for field in self.required_fields)

    def extract_info(self, user_input):
        info = {}

        # Detect issue-related keywords
        issue_keywords = re.findall(r"(error|problem|bug|issue|not working.*?)(\.|$)", user_input, re.IGNORECASE)
        if issue_keywords:
            info["issue"] = issue_keywords[0][0]

        # Detect urgency level
        if any(word in user_input.lower() for word in ["urgent", "immediately", "asap", "critical"]):
            info["urgency"] = "high"
        elif any(word in user_input.lower() for word in ["whenever", "no rush", "not urgent", "later"]):
            info["urgency"] = "low"

        # Detect known product mentions
        for product in ["laptop", "server", "cloud", "dashboard", "mobile app", "web app"]:
            if product in user_input.lower():
                info["product"] = product
                break

        return info

    def analyze_input(self, user_input):
        extracted = self.extract_info(user_input)
        self.collected_info.update(extracted)

    def get_missing_questions(self):
        missing = [f for f in self.required_fields if f not in self.collected_info]
        questions = {
            "issue": "Can you describe the issue you're facing?",
            "urgency": "How urgent is this issue for you?",
            "product": "Which product or service are you referring to?"
        }
        return [questions[m] for m in missing]

    def process_input(self, user_input):
        self.analyze_input(user_input)
        if not self.is_input_complete():
            return {
                "status": "incomplete",
                "questions": self.get_missing_questions(),
                "collected": self.collected_info
            }
        return {
            "status": "complete",
            # "message": "Thank you! I have all the information needed.",
            "collected": self.collected_info
        }
