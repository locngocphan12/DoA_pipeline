from google import genai
from google.genai import types

from openai import OpenAI

from prompt import scientific_aspects_classification_prompt, scientific_argument_system_prompt

import json
import re

def parse_argument_output(response_text):
    """
    Trích xuất Label và Reasoning từ output của LLM.
    Format mong đợi:
    <|ANSWER|>Label<|ANSWER|>
    <|REASONING|>Reasoning content<|REASONING|>
    """
    # 1. Chuẩn bị giá trị mặc định
    label = "ERROR"
    reasoning = "Parsing Failed"
    print(response_text)
    # 2. Trích xuất ANSWER (Label)
    # re.DOTALL giúp dấu chấm (.) khớp với cả ký tự xuống dòng
    # re.IGNORECASE để bắt được cả 'claim', 'Claim', 'CLAIM'
    answer_match = re.search(r"<\|ANSWER\|>(.*?)<\|ANSWER\|>", response_text, re.DOTALL | re.IGNORECASE)
    if answer_match:
        raw_label = answer_match.group(1).strip().lower()
        # Chuẩn hóa về dạng Capitalized
        if "claim" in raw_label:
            label = "Claim"
        elif "premise" in raw_label:
            label = "Premise"
        else:
            label = "OTHER" # Trường hợp model trả về nhãn lạ

    # 3. Trích xuất REASONING
    reasoning_match = re.search(r"<\|REASONING\|>(.*?)<\|REASONING\|>", response_text, re.DOTALL)
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()

    return label, reasoning

def parse_aspect_response(response_text):
    """
    Hàm phân tích phản hồi của LLM để lấy Reasoning và Label.
    """
    try:
        # 1. Làm sạch chuỗi: Tìm đoạn JSON nằm giữa dấu ngoặc nhọn đầu và cuối
        # Regex này tìm chuỗi bắt đầu bằng '{' và kết thúc bằng '}' (non-greedy)
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

        if json_match:
            json_str = json_match.group(0)
        else:            return "Parsing Error: No JSON found", "OTHER"

        # 2. Parse chuỗi JSON thành Dictionary
        data = json.loads(json_str)

        # 3. Trích xuất dữ liệu (dùng .get để tránh lỗi KeyError)
        reasoning = data.get("reasoning", "No reasoning provided").strip()
        label = data.get("label", "OTHER").strip().upper()

        # 4. Kiểm tra xem Label có nằm trong danh sách cho phép không (Optional)
        valid_labels = ["METHODOLOGY", "EXPERIMENTS", "RELATED_WORK", "PRESENTATION"]
        if label not in valid_labels:
            print(f"Warning: Unexpected label '{label}'")
        return reasoning, label

    except json.JSONDecodeError:
        return "Parsing Error: Invalid JSON format", "ERROR"
    except Exception as e:
        return f"Unknown Error: {str(e)}", "ERROR"

class GPTClassifier:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.sys_prompt = scientific_aspects_classification_prompt
    def classify_text(self, sentence: str, full_review: str) -> str:
        text =f"[SENTENCE]:{sentence}\n[FULL REVIEW]:{full_review}"
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.sys_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.0,
        )
        complete_sample = response.choices[0].message.content
        reasoning, label = parse_aspect_response(complete_sample)
        return reasoning, label

class GeminiClassifier:

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.sys_prompt = scientific_aspects_classification_prompt
        self.sys_prompt_arg = scientific_argument_system_prompt
    def classify_text(self, sentence: str, full_review: str) -> str:
        text =f"[SENTENCE]:{sentence}\n[FULL REVIEW]:{full_review}"
        response = self.client.models.generate_content(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=self.sys_prompt,
                temperature=0.0,
            ),
            contents=f"{text}"
        )
        reasoning, label = parse_aspect_response(response.text)
        return reasoning, label

    def classify_argument(self, sentence: str, full_review: str, section: str) -> str:
        text =f'[TOPIC]: Review about {section} of paper.\n [FULL TEXT]:{full_review}\n[SENTENCE]:{sentence}\n'
        response = self.client.models.generate_content(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=self.sys_prompt_arg,
                temperature=0.0,
            ),
            contents=f"{text}"
        )
        result = response.text
        match = re.search(r"<\|ANSWER\|>(.*?)<\|ANSWER\|>", result)
        if match:
            label = match.group(1).strip().lower()
            if "premise" in label: return "Premise"
            if "claim" in label: return "Claim"

        if "premise" in result.lower(): return "Premise"
        return "Claim"
