

import json
import os
from typing import Counter
from src.datamodel.prompt import PromptModel
from src.server.utils import get_redis


redis = get_redis()


def get_counter(prompt_usage_label: str = "prompt_usage"):
    prompt_usage = Counter()

    usage_data = redis.get(prompt_usage_label)
    if usage_data:
        prompt_usage = Counter(json.loads(usage_data))

    return prompt_usage


def save_counter(prompt_usage: Counter, prompt_usage_label: str = "prompt_usage"):
    redis.set(prompt_usage_label, json.dumps(prompt_usage))


def load_prompts(directory="./src/prompts/wiki_prompts", dify=True, max_prompt_id=4) -> list[PromptModel]:
    if dify:
        prompts = [
            PromptModel(id=str(i), prompt_text="")
            for i in range(1, max_prompt_id + 1)
        ]
    else:
        prompts = []

        required_substitutions = ["{conversation}"]

        for filename in os.listdir(directory):
            if filename.endswith(".txt"):
                filepath = os.path.join(directory, filename)
                with open(filepath, "r") as file:
                    prompt_text = file.read().strip()

                    # Check for required substitutions
                    if all(substitution in prompt_text for substitution in required_substitutions):
                        prompt = PromptModel(
                            id=filename[:-4],  # Remove .txt extension to get the id
                            prompt_text=prompt_text
                        )
                        prompts.append(prompt)
                    else:
                        print(f"Prompt {filename} is missing required substitutions.")
    return prompts


max_prompt_id = int(os.getenv("DIFY_MAX_PROMPT_ID")) | 4
prompts = load_prompts(max_prompt_id=max_prompt_id)


def assign_prompts(dify=True) -> list[PromptModel]:
    if dify:
        prompt_usage = get_counter(prompt_usage_label="dify_prompt_usage")
    else:
        prompt_usage = get_counter()

    # Sort prompts by usage and assign the two least used prompts
    least_used_prompts = sorted(prompts, key=lambda x: prompt_usage[x.id])[:2]

    # Update the assignment dictionary and usage counter
    for prompt in least_used_prompts:
        prompt_usage[prompt.id] += 1

    # Save the updated assignments and usage data
    if dify:
        save_counter(prompt_usage, "dify_prompt_usage")
    else:
        save_counter(prompt_usage)

    return least_used_prompts
