from unsloth import FastLanguageModel
from transformers import TextStreamer
from prompt import scientific_argument_system_prompt
# Load Llama Model
import re

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=f'brunoyun/Llama-3.1-Amelia-ADUC-8B-v1',
    max_seq_length=2048,
    dtype=None,
    load_in_4bit=False,
    gpu_memory_utilization=0.6,
)

FastLanguageModel.for_inference(model)

def Argument_Mining_Classification(sentence, full_text, section_context):
    """Gửi sentence vào Llama để phân loại"""

    # Prompt Template
    messages = [
        {'role': 'system', 'content': scientific_argument_system_prompt},
        {'role': 'user', 'content': f'[TOPIC]: Review about {section_context} of paper.\n[FULL TEXT]:{full_text}\n[SENTENCE]:{sentence}\n'}
    ]

    # Tokenize & Generate
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to('cuda')

    outputs = model.generate(
        inputs,
        max_new_tokens=128,
        temperature=0.0,
        use_cache=True,
        pad_token_id=tokenizer.eos_token_id
    )

    decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]

    match = re.search(r"<\|ANSWER\|>(.*?)<\|ANSWER\|>", decoded)
    if match:
        label = match.group(1).strip().lower()
        if "premise" in label: return "Premise"
        if "claim" in label: return "Claim"

    if "premise" in decoded.lower(): return "Premise"
    return "Claim"