import os
import re
import json
from typing import List


from ..datamodel.manager.neo4j_databse import Neo4jDBSingleton
from ..datamodel.message import MessageModel
from .logger import getLogger
from .state_item import StateItem

logging = getLogger()
no_main_title_marker = "Kein Haupttitel gefunden"


def load_interview(path: str = 'src/static/interview.json'):
    with open(path, 'r') as file:
        data = json.load(file)
    return data


def generate_history(interview_data: List[StateItem]):
    history: List[MessageModel] = []
    for item in interview_data:
        if not isinstance(item, StateItem):
            logging.error(f'Expected StateItem instance, but got {type(item)}')
            continue  # Überspringe dieses Element oder handle den Fehler angemessen

        history.append(item.question)
        history.append(item.answer)

    logging.info(f"generate_history - {history}")
    return history


def conversation_from_history(history: List[MessageModel]):
    conversation: List[str] = []
    for item in history:
        if not isinstance(item, MessageModel):
            logging.error(f'Expected MessageModel instance, but got {type(item)}')
            continue  # Überspringe dieses Element oder handle den Fehler angemessen

        conversation.append(f"{item.role.value}: {item.content}")

    logging.info(f"conversation_from_history - {conversation}")
    return conversation


def string_conversation_from_history(history: List[str]):
    conversation = "\n".join([f"{item}" for item in history])
    logging.info(f"string_conversation_from_history - {conversation}")
    return conversation


def process_graph(json_file: str):
    logging.info(f"process_graph - {json_file}")
    json_obj = json.loads(json_file)
    cypherQueries = json_obj["cypher_queries"]
    query = ""
    for item in cypherQueries:
        query += '\n' + item
    neo = Neo4jDBSingleton()
    neo.query(query.strip())


def clean_json(input_string: str):
    # Regular expression to match the JSON object
    match = re.search(r'\{.*\}', input_string, re.DOTALL)
    if match:
        return match.group(0)
    else:
        raise ValueError("No valid JSON object found in the input string")


def get_env_prop(name: str):
    prop = os.getenv(name)
    if not prop or "None" in prop:
        raise SystemExit(f"{name} is not defined")
    return prop


def build_wiki_from_data(wiki_data) -> str:
    try:
        markdown = wiki_data.get('markdown', "")
        # split markdown to seperate the title and the content, by looking for a '# ' pattern
        title_markdown, remaining_markdown = extract_main_title_and_content(markdown)
        logging.info(f"build_wiki_from_data - {title_markdown} - rest - {remaining_markdown}")

        wiki = "\n".join(['# ' + title_markdown + '\n' if title_markdown != no_main_title_marker else '', remaining_markdown])
        logging.info(f"build_wiki_from_data - {wiki}")
        return wiki
    except Exception as e:
        logging.error(f"Fehler beim Erstellen des Wikis: {e} {wiki_data}")
        return ""


def extract_main_title_and_content(md_text):
    # Suche nach der ersten Hauptüberschrift und teile den Text in Titel und Rest
    parts = re.split(r"^# (?P<title>[^\n]+)$", md_text, 1, flags=re.MULTILINE)

    if len(parts) > 1:
        # Der Titel wird in parts[1] und der restliche Text in parts[2] sein
        main_title = parts[1].strip()
        remaining_text = parts[2].strip()
    else:
        # Falls keine Hauptüberschrift gefunden wird
        main_title = no_main_title_marker
        remaining_text = md_text.strip()

    return main_title, remaining_text
