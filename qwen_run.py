from prompt import scientific_aspects_classification_prompt, scientific_argument_system_prompt

import json
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


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
        else:
            return "Parsing Error: No JSON found", "OTHER"

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

class QwenLocalClassifier:
    def __init__(self, model_id="Qwen/Qwen3-8B"):

        self.sys_prompt = scientific_aspects_classification_prompt
        self.sys_prompt_arg = scientific_argument_system_prompt

        self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            load_in_4bit=True,  # Tiết kiệm VRAM cho card 23GB
            trust_remote_code=True
        )

    def _generate(self, sys_prompt, user_text):
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_text}
        ]
        # Tạo format chat chuẩn của Qwen
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=512,
            do_sample=False  # Tương đương temperature=0
        )
        # Chỉ lấy phần model mới tạo ra
        response = self.tokenizer.batch_decode(
            generated_ids[:, model_inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )[0]
        return response

    def classify_argument(self, sentence, section_text, section_name):
        # Input chỉ là Section Context
        user_text = f"[TOPIC]: {section_name}\n[CONTEXT]: {section_text}\n[SENTENCE]: {sentence}"
        result = self._generate(self.sys_prompt, user_text)
        reasoning, label = parse_aspect_response(result)
        return reasoning, label

    def classify_aspect(self, sentence, full_review):
        # Input là Full Review Context
        user_text = f"[FULL REVIEW]: {full_review}\n[SENTENCE]: {sentence}"
        result = self._generate(self.sys_prompt_arg, user_text)
        # Logic parse label của bạn...
        match = re.search(r"<\|ANSWER\|>(.*?)<\|ANSWER\|>", result)
        if match:
            label = match.group(1).strip().lower()
            if "premise" in label: return "Premise"
            if "claim" in label: return "Claim"

        if "premise" in result.lower(): return "Premise"
        return "Claim"