class Conversation:

    def __init__(self):              #constructor, elf means this
        self.requirement = ""
        self.questions = []
        self.answers = []

    def add_answer(self, question, answer):
        self.questions.append(question)
        self.answers.append(answer)

    def get_context(self):

        context = self.requirement + "\n\n"

        for q, a in zip(self.questions, self.answers):     #zip is used to iterate multiple collection at same time
            context += f"{q}\nAnswer: {a}\n\n"

        return context