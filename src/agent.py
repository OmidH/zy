from datetime import datetime
from enum import Enum
from openai import AsyncOpenAI
from typing import Dict, List
import httpx
import os

from src.datamodel.prompt import PromptModel

from .datamodel.message import MessageModel, Role
from .helper.utils import conversation_from_history, string_conversation_from_history
from .helper.logger import getLogger
from .prompts.offboarding_prompt import p_followup_questions, p_wiki

logging = getLogger()


class GPTModel(Enum):
    GPT4 = 'gpt-4'
    GPT_4o = 'gpt-4o'
    GPT3_5 = 'gpt-3.5-turbo'
    GPT3_5_INSTRUCT = 'gpt-3.5-turbo-instruct'


class AgentSingleton:
    _instance = None
    _client = None
    _dify_client: httpx.AsyncClient = None
    _settings = None
    _dify_api_url = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AgentSingleton, cls).__new__(cls, *args, **kwargs)
            cls._instance._client = AsyncOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
                timeout=5000,
                max_retries=3
            )
            cls._instance._settings = {
                "model": 'gpt-4o',
                # "model": "gpt-3.5-turbo-instruct",
                "temperature": .2,
                "stream": False,
            }

            # Initialize HTTPX async client for DIFY
            cls._instance._dify_api_url = os.environ.get("DIFY_API_URL")
            headers = {'Content-Type': 'application/json'}
            cls._instance._dify_client = httpx.AsyncClient(base_url=cls._instance._dify_api_url, headers=headers)

        return cls._instance

    def get_settings(self):
        return self._settings

    def set_settings(self, settings: Dict):
        self._settings = settings
        logging.info(self._settings)

    async def completion(self, history: List[MessageModel] = [], query: MessageModel = '', model: None | GPTModel = None, max_tokens=500, as_json=False):
        # TODO: Implement properly
        if len(history) > 0:
            for msg in history:
                logging.info(f"--> history {msg}")
            ctx = [{"role": query.role.value, "content": query.content}]
        else:
            ctx = [{"role": query.role.value, "content": query.content}]

        logging.info(f"completion - {ctx}")

        settings = self._settings.copy()
        if model is not None:
            settings['model'] = model.value
        settings['max_tokens'] = max_tokens
        if as_json:
            settings["response_format"] = {"type": "json_object"}

        chat_completion = await self._client.chat.completions.create(
            messages=ctx,
            **settings,
        )

        return MessageModel(
            role=Role.SYSTEM,
            content=chat_completion.choices[0].message.content,
            model=chat_completion.model,
            tokens=chat_completion.usage.total_tokens
        )

    async def generate(self, query: MessageModel, model=None | GPTModel):
        settings = self._settings.copy()
        if model is not None:
            settings['model'] = model.value
        settings['max_tokens'] = 3000

        logging.info(f"generate - settings - {settings}")

        chat_completion = await self._client.completions.create(
            prompt=query.content,
            **settings,
        )

        logging.info(f"generate - {chat_completion}")
        return MessageModel(
            role=Role.SYSTEM,
            content=chat_completion.choices[0].text,
            model=chat_completion.model,
            tokens=chat_completion.usage.total_tokens
        )

    async def analyse(self, business_segment: str, question: str, message: str, history=[], mandatory_upcoming_questions=[], optional_upcoming_questions=[], skipped_questions=[]):
        mm = MessageModel(
            role=Role.USER,
            model="",
            tokens=0,
            content=p_followup_questions.format(
                business_segment=business_segment,
                question=question,
                message=message,
                history=history,
                mandatory_upcoming_questions=mandatory_upcoming_questions,
                optional_upcoming_questions=optional_upcoming_questions,
                skipped_questions=skipped_questions))

        sys_message = await self.completion(
            query=mm,
            model=GPTModel.GPT4
        )

        logging.info(f"\n\n\nask_a_question - {question}\n\n{message}\n\n{history}\n\n\n")
        logging.info(f"ask_a_question - {sys_message}")

        return sys_message

    async def generate_graph(self, history: List[MessageModel] = []):
        conversation = conversation_from_history(history)
        mm = MessageModel(
            role=Role.USER,
            model="",
            tokens=0,
            content=f"""
    Gegeben ist der folgende Text einer Konversation zwischen zwei Vertretern von unterschiedlichen oder gleichen Berufsgruppen. Es geht grundsätzlich um einen professionellen Austausch und der Zweck der Unterhaltung ist Informationsgewinnung und Prozessdokumentation:
```
{conversation}
```
Bitte erstelle einen Wissensgraphen, der die Schlüsselinformationen und Beziehungen dieser Konversation zwischen Berufsgruppen darstellt. Der Graph sollte thematisch orientiert sein und Informationen über Projekte, Aufgaben, Entitäten und Feedback einbeziehen, ohne sich auf die individuellen Sprecher zu konzentrieren. Verwende die MERGE-Anweisung in den Cypher-Queries, um die Erstellung doppelter Knoten und Beziehungen zu verhindern. Die Rückgabe sollte AUSSCHLIEßLICH als JSON-Objekt erfolgen, das die Cypher-Queries und den Wissensgraphen enthält. Das JSON-Object sollte folgendermaßen aussieht:
{{
    "cypher_queries": [
        "MERGE (var1:Label {{name: 'prop'}})",
        "MERGE (var2:Label2 {{name: 'prop2'}})",
        ...
    ],
    "knowledge_graph": {{
        "nodes": [
            {{"id": "id1", "label": "Label1", "properties": {{"name": "Name1"}}}},
            {{"id": "id2", "label": "Label2", "properties": {{"name": "Name2"}}}},
            ...
        ],
        "relationships": [
            {{"startNode": "node", "endNode": "node_x", "type": "TYPE1"}},
            {{"startNode": "node", "endNode": "node_y", "type": "TYPE2"}},
            ...
        ]
    }}
}}
Achte unbedingt darauf, dass die Variablen in "cypher_queries" eindeutige Namen haben, da dieses in eine Abfrage gemeinsam abgesetzt werden.
""")

        sys_message = await self.completion(
            history=[],
            query=mm,
            # model=GPTModel.GPT3_5,
            model=GPTModel.GPT_4o,
            max_tokens=3000,
            as_json=True)

        logging.info(f"generate_graph - {sys_message} \n\n{mm}")

        return sys_message

    async def generate_wiki(self, business_segment: str, history: List[MessageModel] = [], prompt: PromptModel = None, generate_conversation: bool = True):
        conversation = history
        if generate_conversation:
            conversation = conversation_from_history(history)

        wiki_prompt = prompt.prompt_text if prompt else p_wiki

        mm = MessageModel(
            role=Role.USER,
            model="",
            tokens=0,
            content=wiki_prompt.format(
                business_segment=business_segment,
                conversation=conversation
            ))

        sys_message = await self.completion(
            history=[],
            query=mm,
            model=GPTModel.GPT3_5,
            max_tokens=3000,
            as_json=False)

        logging.info(f"generate_wiki - {sys_message} \n\n{mm}")

        return sys_message

    async def stt(self, path: str):
        try:
            audio_file = open(path, "rb")
            transcription = await self._client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language="de"
            )

            logging.info(f"stt - {transcription}")
            return transcription
        except Exception as e:
            logging.error(f"Error in stt: {e}")
            return ""

    async def tts(self, query: str, path: str):
        response = await self._client.audio.speech.create(
            model="tts-1-hd",
            voice="fable",
            input=query,
            response_format='mp3'
        )
        response.stream_to_file(path)

        logging.info(f"tts - file saved to {path}")
        return path

    async def dify_analyse(
            self, business_segment: str, question: str, message: str, history=[], mandatory_upcoming_questions=[], optional_upcoming_questions=[], skipped_questions=[]):

        json_obj = {"response_mode": "blocking",
                    "user": "zy_mvp",
                    "inputs": {
                        "business_segment": business_segment,
                        "question": question,
                        "message": message,
                        "history": "\n".join([msg for msg in history]),
                        "mandatory_upcoming_questions": "\n".join([f"- {q}" for q in mandatory_upcoming_questions]),
                        "optional_upcoming_questions": "\n".join([f"- {q}" for q in optional_upcoming_questions]),
                        "skipped_questions": "\n".join([f"- {q}" for q in skipped_questions])
                    }}

        logging.info(f"dify_analyse: {json_obj}\n{self._dify_client.headers}")
        headers = {'Authorization': f'Bearer {os.environ.get("DIFY_QUESTIONS_API_KEY")}', 'Content-Type': 'application/json'}
        try:
            response = await self._dify_client.post('/workflows/run', json=json_obj, headers=headers)
            data = response.json()
            logging.info(f"response: {data}")
            return data
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return None

    async def generate_dify_summery(
            self,
            business_segment: str,
            history: List[MessageModel] = [],
            generate_conversation_string: bool = True):
        conversation = history
        if generate_conversation_string:
            conversation = string_conversation_from_history(history)

        json_obj = {"response_mode": "blocking",
                    "user": "zy_mvp",
                    "inputs": {
                        "interview": conversation,
                        "business_segment": business_segment,
                    }}
        headers = {'Authorization': f'Bearer {os.environ.get("DIFY_SUMMERY_API_KEY")}', 'Content-Type': 'application/json'}
        logging.info(f"generate_dify_summery: {json_obj}")

        try:
            timeout = httpx.Timeout(60.0)
            response = await self._dify_client.post('/workflows/run', json=json_obj, timeout=timeout, headers=headers)
            data = response.json()
            logging.info(f"response: {data}")
            return data
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return None

    async def generate_dify_wiki(
            self,
            business_segment: str,
            history: List[MessageModel] = [],
            prompt_id: int = 1,
            interview_date: str = datetime.now().strftime("%Y-%m-%dT%H:%M"),
            generate_conversation_string: bool = True):

        conversation = history
        if generate_conversation_string:
            conversation = string_conversation_from_history(history)

        json_obj = {"response_mode": "blocking",
                    "user": "zy_mvp",
                    "inputs": {
                        "interview": conversation,
                        "prompt_id": prompt_id,
                        "business_segment": business_segment,
                        "date": interview_date
                    }}
        headers = {'Authorization': f'Bearer {os.environ.get("DIFY_WIKI_API_KEY")}', 'Content-Type': 'application/json'}
        logging.info(f"generate_dify_wiki: {json_obj}")

        try:
            timeout = httpx.Timeout(300.0)  # 300 Sekunden (5 min) Gesamttimeout
            response = await self._dify_client.post('/workflows/run', json=json_obj, timeout=timeout, headers=headers)
            data = response.json()
            logging.info(f"response: {data}")
            return data
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return None
