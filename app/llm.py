import os
import time

from openai import OpenAI
from openai import RateLimitError, APITimeoutError


client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
    timeout=30.0,
    max_retries=0,
)

MODEL = "openai/gpt-oss-20b"


def ask_llm(prompt):

    max_attempts = 4

    for attempt in range(max_attempts):

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0,
                max_tokens=100,
            )

            return response.choices[0].message.content

        except RateLimitError:
            if attempt == max_attempts - 1:
                raise

            wait_time = 2 ** attempt

            print(
                f"NVIDIA rate limit. "
                f"Retrying in {wait_time}s..."
            )

            time.sleep(wait_time)

        except APITimeoutError:
            if attempt == max_attempts - 1:
                raise

            wait_time = 2 ** attempt

            print(
                f"NVIDIA timeout. "
                f"Retrying in {wait_time}s..."
            )

            time.sleep(wait_time)