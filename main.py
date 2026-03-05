import time

import json
import os
import argparse
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv

# Import các module của bạn
from sentence_splitting import split_into_sentences
#from argument_mining import Argument_Mining_Classification
from aspects_classification import GeminiClassifier, GPTClassifier

# ==========================================
# 0. SETUP & CONFIGURATION
# ==========================================

# Load API Key từ file .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in .env file.")

# # Khởi tạo Classifier với API Key
classifier_gemini = GeminiClassifier(api_key=GEMINI_API_KEY)


# classifier_gpt = GPTClassifier(api_key=OPENAI_API_KEY) # Uncomment nếu dùng GPT

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================

def get_processed_ids(output_file):
    """
    Đọc file output hiện tại để lấy danh sách các bài đã xử lý xong.
    Trả về một set chứa các tuple: (Reviewer_Type, Section, Paper_ID)
    """
    processed = set()
    if not os.path.exists(output_file):
        return processed

    print(f"Checking existing progress in {output_file}...")
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    uid = record.get('unique_review_id')
                    processed.add(uid)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error reading existing file: {e}")

    print(f"Found {len(processed)} sentences processed previously. Resuming logic engaged.")
    return processed


# ==========================================
# 2. MAIN PROCESSING LOOP
# ==========================================

def process_all_folders(root_path, output_file="detailed_argument_mining_results.jsonl"):
    # Cấu trúc folder mapping
    folders = {
        'Human': 'new_extracted_parts_human',
        #'SEA_LLM': 'new_extracted_parts_sea'
    }

    files = {
        'Summary': 'Summary.jsonl',
        'Strengths': 'Strengths.jsonl',
        'Weaknesses': 'Weaknesses.jsonl',
        'Questions': 'Questions.jsonl'
    }

    # 1. Load danh sách đã chạy để Resume
    # Lưu ý: Set này chứa (Reviewer, Section, PaperID) để biết bài nào đã làm rồi
    processed_ids = get_processed_ids(output_file)
    # Mở file ở chế độ 'a' (append) để ghi nối tiếp
    with open(output_file, 'a', encoding='utf-8') as f_out:

        for reviewer_type, folder_name in folders.items():
            folder_path = os.path.join(root_path, folder_name)

            for section, filename in files.items():
                file_path = os.path.join(folder_path, filename)

                if not os.path.exists(file_path):
                    print(f"Skipping {file_path} (Not found)")
                    continue

                print(f"\nProcessing {reviewer_type} - {section}...")

                # Đọc file input
                with open(file_path, 'r', encoding='utf-8') as f_in:
                    lines = f_in.readlines()

                # Duyệt qua từng dòng (Mỗi dòng là 1 bài review/paper)
                for idx, line in tqdm(enumerate(lines), total=len(lines), desc=f"{reviewer_type}-{section}"):
                    try:
                        data = json.loads(line)
                        paper_id = data.get("paper_id", f"unknown_{idx}")
                        unique_id = data.get("unique_review_id")
                        # --- RESUME CHECK ---
                        # Logic: Nếu key này đã tồn tại trong tập đã xử lý -> Bỏ qua
                        if unique_id and unique_id in processed_ids:
                            continue
                            # --------------------

                        full_review = data.get("Full_review", "")
                        full_paragraph = data.get(section, "")

                        # Fallback context
                        if not full_review:
                            full_review = full_paragraph

                        # Tách câu
                        sentences = split_into_sentences(full_paragraph)

                        for sent in sentences:
                            if not sent.strip(): continue

                            # 1. Argument Mining Classification
                            # (Giả định hàm này trả về "Claim" hoặc "Premise")
                            arg_label= classifier_gemini.classify_argument(sent, full_paragraph, section)
                            aspect_label = "N/A"
                            aspect_reasoning = "N/A"

                            # 2. Aspect Classification (Chỉ chạy nếu là Premise)
                            if arg_label == "Premise":
                                try:
                                    # Gọi Gemini để phân loại Aspect
                                    reasoning, label = classifier_gemini.classify_text(sent, full_review)
                                    aspect_reasoning = reasoning
                                    aspect_label = label
                                except Exception as e:
                                    # Ghi log lỗi nhỏ nhưng không dừng chương trình
                                    # print(f"API Error on sent: {sent[:20]}... {e}")
                                    aspect_label = "ERROR"
                                    aspect_reasoning = str(e)

                            # 3. Tạo record kết quả
                            result_record = {
                                'unique_review_id': unique_id,
                                'Reviewer_Type': reviewer_type,
                                'Paper_ID': paper_id,
                                'Section': section,
                                'Sentence': sent,
                                'Argument_Label': arg_label,
                                'Aspect_Label': aspect_label,
                                'Aspect_Reasoning': aspect_reasoning,
                                'Is_Premise': 1 if arg_label == "Premise" else 0
                            }

                            # 4. Ghi ngay lập tức xuống file
                            f_out.write(json.dumps(result_record, ensure_ascii=False) + "\n")

                        # Sau khi ghi xong hết các câu của 1 bài báo, flush buffer để đảm bảo an toàn
                        f_out.flush()

                    except json.JSONDecodeError:
                        print(f"JSON Error at line {idx} in {filename}")
                        continue
                    except Exception as e:
                        print(f"Unexpected Error at line {idx}: {e}")
                        continue

    print("\n>>> PIPELINE COMPLETED SUCCESSFULLY!")


# ==========================================
# 3. ENTRY POINT
# ==========================================

if __name__ == "__main__":
    # Parse Arguments
    parser = argparse.ArgumentParser(description="Run Argument Mining & Aspect Classification Pipeline")
    parser.add_argument("--data_dir", type=str, default="",
                        help="Root path containing processed_reviews_human/sea folders")
    parser.add_argument("--output_file", type=str, default="detailed_argument_mining_results_v1.jsonl",
                        help="Path to save the output JSONL file")

    args = parser.parse_args()

    # Chạy pipeline
    process_all_folders(root_path=args.data_dir, output_file=args.output_file)

    # (Tuỳ chọn) Convert sang CSV ở bước cuối cùng nếu cần view
    try:
        print("Converting final JSONL to CSV for backup...")
        df = pd.read_json(args.output_file, lines=True)
        csv_name = args.output_file.replace(".jsonl", ".csv")
        df.to_csv(csv_name, index=False)
        print(f"Saved CSV backup to: {csv_name}")
    except Exception as e:
        print(f"Could not convert to CSV (File might be empty): {e}")






