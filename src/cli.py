import os
import json
import datetime
import uuid
from dotenv import load_dotenv

from .audio.audio_tools import play_audio, record_audio

from .datamodel.message import MessageModel, Role

from .helper.utils import clean_json, conversation_from_history, generate_history, save_wiki
from .helper.interview_store import InterviewStoreSingleton
from .helper.logger import getLogger
from .agent import AgentSingleton

# load .env file
load_dotenv()

logging = getLogger()

store = InterviewStoreSingleton()
agent = AgentSingleton()

# Define global variables for session and iteration tracking
session_id = uuid.uuid4().hex[:5]  # Replace with your method of generating or setting a session ID


async def process_q_a(question, answer):
    q = MessageModel(role=Role.SYSTEM, content=question)
    a = MessageModel(role=Role.USER, content=answer)

    new_questions = await agent.analyse(
        question,
        answer,
        history=conversation_from_history(generate_history(store.get_state())),
        upcoming_questions=store.get_upcomming_questions(),
        skipped_questions=store.get_skipped())
    content = clean_json(new_questions.content)
    json_message = json.loads(content)

    store.update_interview(json_message['additional'])

    # answers.append({"question": question, "answer": answer, "system": json_message})  # Speichere Frage, Antwort und System Message
    store.add_to_state(q, a, json_message)


async def main():
    try:
        # Ask the user at the start how they want to provide their answers.
        method_choice = input("Type answer (T) or record audio (R)? ").lower()

        iteration_number = 0
        question = store.current_question()

        while question is not None:
            now = datetime.datetime.now()
            filename = now.strftime(os.path.join(os.getenv('BB_AUDIO_PATH'), f"{session_id}-%Y-%m-%d-%H-%M-{iteration_number}.mp3"))
            iteration_number += 1

            q_path = await agent.tts(question, filename.replace(".mp3", "_q.mp3"))
            play_audio(q_path)
            print("\n", question)

            if method_choice == 'r':
                print("Press 's' to skip this question, or any other key to continue.")
                skip = input()
                if skip.lower() == 's':
                    answer = 'skip'
                else:
                    fname = filename.replace(".mp3", "_a.mp3")
                    record_audio(fname)
                    answer = await agent.stt(fname)
            else:
                answer = input("Answer (type 'skip' to skip, press CTRL+D to exit): ")
                print()

            if answer.strip().lower() == 'skip':
                print("Skipping question...")
                store.add_to_skipped(question)
            elif len(answer.strip()) > 0:
                await process_q_a(question, answer)

            question = store.next_question()  # Get the next question

    except EOFError:
        print("\nProgram terminated with CTRL+D")

    print("Interview completed. Here are your responses:")
    answers = store.get_state()
    history = generate_history(answers)
    for answer in answers:
        print(f'Question: {answer.question.content}, Answer: {answer.answer.content}')

    # Batch processing of requests
    # graph_json = await agent.generate_graph(history=history)
    # process_graph(graph_json.content)
    wiki = await agent.generate_wiki(history=history)
    # TODO fix for user
    save_wiki(wiki.content)

# Run the async main function using an event loop
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
