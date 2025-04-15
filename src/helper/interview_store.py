# import logging
from typing import Any, List, Dict

from ..datamodel.message import MessageModel

from .state_item import StateItem
from .utils import load_interview

from ..helper.logger import getLogger

logging = getLogger()


class InterviewStoreSingleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(InterviewStoreSingleton, cls).__new__(cls)
            cls._instance._init_interview()  # Initialisierung innerhalb der Methode
        return cls._instance

    def _init_interview(self):
        self._interview = load_interview('src/static/interview_it.json')
        self._cursor = {'category': 'general', 'step': 0}
        self._state = []
        self._skipped = []
        logging.info(f'init_interview - {self._cursor}')

    def get_interview(self):
        return self._interview

    def get_state(self):
        return self._state

    def get_skipped(self):
        return self._skipped

    def add_to_skipped(self, q: str):
        self._skipped.append(q)

    def add_to_state(self, q: MessageModel, a: MessageModel, s: Dict[str, Any]):
        logging.info(f"add_to_state - {q, a, s}")
        self._state.append(StateItem(question=q, answer=a, system=s))

    def get_upcomming_questions(self):
        category = self._cursor['category']
        step = self._cursor['step']
        # Retrieve all questions from the current category that are beyond the current step
        upcoming_questions = self._interview[category][step + 1:] if step + 1 < len(self._interview[category]) else []
        return upcoming_questions

    def current_question(self):
        category = self._cursor['category']
        step = self._cursor['step']
        if step < len(self._interview[category]):
            return self._interview[category][step]
        return None

    def next_question(self):
        categories = list(self._interview.keys())
        category = self._cursor['category']
        step = self._cursor['step']
        question = None

        logging.info(f"next_question - current: {step} all:{len(self._interview[category])}")

        if step + 1 < len(self._interview[category]):
            question = self._interview[category][step + 1]
            self._cursor['step'] += 1  # Move to the next question for the next call
        else:
            # Find the next category with available questions
            current_index = categories.index(category)
            for i in range(current_index + 1, len(categories)):
                next_category = categories[i]
                if len(self._interview[next_category]) > 0:  # Ensure the category has questions
                    self._cursor['category'] = next_category
                    self._cursor['step'] = 0
                    question = self._interview[next_category][0]

        # If no more questions are left in any category
        return question

    def update_interview(self, additionals: List[str]):
        category = self._cursor['category']
        step = self._cursor['step']

        # Insert the additional questions right after the current step in the current category
        if category in self._interview:
            before = self._interview[category][:step + 1]
            after = self._interview[category][step + 1:]
            self._interview[category] = before + additionals + after
            # Update the step to point to the next question correctly
            self._cursor['step'] += 1
            logging.info(f"update_interview - Updated interview questions for category '{category}': {self._interview[category]}")
        else:
            logging.error(f"update_interview - No such category '{category}' in the interview structure.")
