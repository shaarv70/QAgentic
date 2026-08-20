class Conversation:

    def __init__(self):
        self.requirement = ""
        self.clarification_state = {}



    def add_answer(
        self,
        key: str,
        question: str,
        answer: str,
    ):
        self.clarification_state[key] = {
            "key": key,
            "question": question,
            "answer": answer,
        }

    def has_key(self, key: str) -> bool:
        return key in self.clarification_state



    def get_clarification_state(self) -> list[dict]:
        return list(self.clarification_state.values())



    def get_clarification_text(self) -> str:

        if not self.clarification_state:
            return ""

        return "\n\n".join(
            f"KEY: {item['key']}\n"
            f"QUESTION: {item['question']}\n"
            f"ANSWER: {item['answer']}\n"
            for item in self.clarification_state.values()
        )