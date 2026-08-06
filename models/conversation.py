class Conversation:


    requirement: str
    questions: list[str]
    answers: list[str]


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


    def get_clarification_text(self) -> str:
            """
            Returns all clarification questions and answers
            as formatted text.
            """

            clarification = ""

            for question, answer in zip(
                self.questions,
                self.answers
            ):

                clarification += (
                    f"{question} : {answer}\n"
                )

            return clarification
