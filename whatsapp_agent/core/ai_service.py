import json
import urllib.request
import urllib.error
from .safety_guard import SafetyGuard
from .model_router import ModelRouter

class AIService:
    def __init__(self, api_key, agent_name="Personal AI Assistant", model_config=None):
        self.api_key = api_key
        self.agent_name = agent_name
        self.safety_guard = SafetyGuard(agent_name=agent_name)
        self.router = ModelRouter(model_config=model_config)

    def generate_reply(self, contact_name, recent_messages, image_b64=None, audio_b64=None):
        """
        Coordinates Safety checks, Model Routing, and Gemini REST API generation.
        """
        last_message_text = recent_messages[-1] if recent_messages else ""
        
        # 1. Deterministic Medical Advice Check (Req 9)
        med_disclaimer = self.safety_guard.check_medical_query(last_message_text)
        if med_disclaimer:
            return med_disclaimer

        # 2. Dynamic Model Routing
        content_type, model_name = self.router.route(
            has_audio=(audio_b64 is not None),
            has_image=(image_b64 is not None)
        )

        # 3. Construct System & Context Prompt (Req 7, Req 8)
        system_prompt = self.safety_guard.build_system_prompt(contact_name)
        transcript = "\n".join(recent_messages[-8:])
        
        base_instruction = (
            f"{system_prompt}\n\n"
            f"--- Recent WhatsApp Chat with {contact_name} ---\n"
            f"{transcript}\n"
            f"--- End of Chat ---\n\n"
        )

        parts = []
        if content_type == "audio" and audio_b64:
            parts.append({
                "inlineData": {
                    "mimeType": "audio/ogg",
                    "data": audio_b64
                }
            })
            instruction = (
                f"{base_instruction}"
                f"{contact_name} sent the attached voice message. Listen carefully and generate a natural, "
                f"polite text reply to {contact_name} responding directly to what they said in the audio:"
            )
            parts.append({"text": instruction})

        elif content_type == "vision" and image_b64:
            parts.append({
                "inlineData": {
                    "mimeType": "image/png",
                    "data": image_b64
                }
            })
            instruction = (
                f"{base_instruction}"
                f"{contact_name} sent the attached image. Look at the image and generate a natural, "
                f"polite text comment/reply to {contact_name} in 1-2 sentences:"
            )
            parts.append({"text": instruction})

        else:
            instruction = f"{base_instruction}Generate the next reply from 'Me' to {contact_name}:"
            parts.append({"text": instruction})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "maxOutputTokens": 120,
                "temperature": 0.7
            }
        }

        # 4. Execute API Request with fallback models
        models_to_try = [model_name, "gemini-3.5-flash", "gemini-flash-latest", "gemini-3.8-flash"]
        # Deduplicate while preserving order
        unique_models = []
        for m in models_to_try:
            if m not in unique_models:
                unique_models.append(m)

        for attempt_model in unique_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{attempt_model}:generateContent?key={self.api_key}"
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=12) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    candidates = resp_data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts_resp = candidates[0]["content"].get("parts", [])
                        if parts_resp and "text" in parts_resp[0]:
                            raw_reply = parts_resp[0]["text"]
                            return self.safety_guard.filter_output(raw_reply)
            except Exception as e:
                # Try next model in fallback list
                continue

        return None
