import re

MEDICAL_DISCLAIMER_EXACT = (
    "I am the Artficial Intelligent agent of the device owner, "
    "im not allowed to provide you with any medicinal advice. "
    "Please call or send message again."
)

# Regex pattern matching medical advice / drug queries in English, Bengali, or phonetic
MEDICAL_KEYWORDS_PATTERN = re.compile(
    r"\b("
    r"medicine|medicines|drug|drugs|tablet|tablets|capsule|capsules|syrup|dose|dosage|"
    r"antibiotic|antibiotics|paracetamol|napa|ace|painkiller|prescription|remedy|"
    r"treatment|headache|fever|cough|cold|stomach ache|vomit|infection|doctor|"
    r"ঔষধ|ওষুধ|ট্যাবলেট|প্যারাসিটামল|নাপা|ডাক্তার|প্রেসক্রিপশন"
    r")\b",
    re.IGNORECASE
)

# Common offensive / abusive terms
OFFENSIVE_TERMS_PATTERN = re.compile(
    r"\b("
    r"fuck|shit|bitch|bastard|asshole|cunt|dick|slut|whore|motherfucker|"
    r"খানকি|কুত্তা|মাদারচোদ|শুয়োর|হারামি|শালার পুত"
    r")\b",
    re.IGNORECASE
)

class SafetyGuard:
    def __init__(self, agent_name="Personal AI Assistant"):
        self.agent_name = agent_name

    def check_medical_query(self, message_text):
        """
        Deterministic interceptor:
        If message asks for medicine or drug suggestions, return exact required disclaimer.
        Otherwise returns None.
        """
        if not message_text:
            return None

        text_lower = message_text.lower()
        if MEDICAL_KEYWORDS_PATTERN.search(text_lower):
            # Check context: asking for advice, drug, medicine, or prescription
            intent_markers = [
                "suggest", "give", "which", "what", "take", "prescribe", "for", "please",
                "খাব", "কী খাব", "কোন", "ঔষধ", "ওষুধ", "দিন", "দাও", "প্রেসক্রিপশন",
                "medicine", "drug", "prescription", "tablet", "dose", "headache", "fever", "pain"
            ]
            if any(marker in text_lower for marker in intent_markers):
                return MEDICAL_DISCLAIMER_EXACT

        return None

    def build_system_prompt(self, contact_name):
        """
        Constructs system prompt enforcing:
        - Persona & Tone
        - Strict cross-contact privacy (Req 7)
        - Zero offensive slangs & no hate speech (Req 8)
        - Natural Islamic phrasing (Alhamdulillah, InshaALLAH, Assalamu Alaikum, Allah Hafez) (Req 8)
        """
        prompt = (
            f"You are {self.agent_name}, an intelligent, polite, and friendly personal AI assistant "
            f"replying on WhatsApp on behalf of the phone owner.\n\n"
            f"STRICT RULES & CONSTRAINTS:\n"
            f"1. TONE & ETIQUETTE:\n"
            f"   - Match the language and tone of {contact_name} (e.g. Bengali/Banglish/English).\n"
            f"   - Use Islamic greetings and phrases naturally and respectfully when appropriate: "
            f"     'Assalamu Alaikum' for greetings, 'Alhamdulillah' for good news/gratitude, "
            f"     'InshaALLAH' for plans/future actions, and 'Allah Hafez' for farewells.\n"
            f"   - NEVER use any offensive slangs, profanity, vulgarity, or insults under any circumstance.\n"
            f"   - NEVER engage in or output hate speech or disrespect towards any religion.\n"
            f"   - Keep replies short (1-2 sentences), natural, helpful, and polite.\n"
            f"   - Do NOT enclose responses in quotation marks.\n\n"
            f"2. ABSOLUTE PRIVACY DIRECTIVE:\n"
            f"   - You ONLY have context for this conversation with {contact_name}.\n"
            f"   - You do NOT know and MUST NEVER disclose any information, message content, or identity "
            f"     of any other contact on this device.\n"
            f"   - If {contact_name} asks about other people's messages, calls, or chats, reply politely: "
            f"     'I am sorry, I do not have access to any other conversations.'\n"
        )
        return prompt

    def filter_output(self, reply_text):
        """Post-generation sanitizer to guarantee no offensive terms leak."""
        if not reply_text:
            return ""
        # Remove surrounding quotes
        cleaned = reply_text.strip()
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1].strip()

        # Remove "Me: " prefix if model hallucinated it
        if cleaned.startswith("Me: "):
            cleaned = cleaned[4:].strip()

        # Sanitize any accidental vulgarity
        cleaned = OFFENSIVE_TERMS_PATTERN.sub("[redacted]", cleaned)
        return cleaned
