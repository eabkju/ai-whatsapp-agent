class ModelRouter:
    def __init__(self, model_config=None):
        self.model_config = model_config or {
            "text": "gemini-2.5-flash",
            "vision": "gemini-2.0-flash",
            "audio": "gemini-2.0-flash"
        }

    def route(self, has_audio=False, has_image=False):
        """
        Determines the appropriate Gemini model and content classification.
        Priority: Audio (Voice Note) > Vision (Image) > Text.
        """
        if has_audio:
            return "audio", self.model_config.get("audio", "gemini-2.0-flash")
        elif has_image:
            return "vision", self.model_config.get("vision", "gemini-2.0-flash")
        else:
            return "text", self.model_config.get("text", "gemini-2.5-flash")
