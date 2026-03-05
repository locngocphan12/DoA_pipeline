# import pandas as pd
# import os
#
# # Đường dẫn thư mục chứa file của bạn
# folder_path = r'E:\LLM_Review\processed_reviews_sea'
#
# # Danh sách file theo thứ tự để gộp
# file_list = ['summary.jsonl', 'strengths.jsonl', 'weaknesses.jsonl', 'questions.jsonl']
#
# dfs = []
# for file_name in file_list:
#     full_path = os.path.join(folder_path, file_name)
#     if os.path.exists(full_path):
#         # Đọc từng file jsonl
#         df_temp = pd.read_json(full_path, lines=True)
#         dfs.append(df_temp)
#     else:
#         print(f"Cảnh báo: Không tìm thấy file {file_name}")
#
# if len(dfs) == len(file_list):
#     # 1. Gộp ngang các DataFrame (axis=1)
#     # Lưu ý: Các file phải có cùng số dòng và cùng thứ tự sample
#     merged_df = pd.concat(dfs, axis=1)
#
#     # 2. Loại bỏ các cột 'paper_id' và 'type' bị lặp lại khi gộp
#     # Chỉ giữ lại cột đầu tiên xuất hiện
#     merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()].copy()
#
#     # 3. Tạo cột Full_review (vẫn giữ lại các cột thành phần)
#     # Dùng .fillna('') để tránh lỗi khi cộng chuỗi nếu có ô trống
#     merged_df['Full_review'] = (
#         "### SUMMARY:\n" + merged_df['Summary'].fillna('') + "\n\n" +
#         "### STRENGTHS:\n" + merged_df['Strengths'].fillna('') + "\n\n" +
#         "### WEAKNESSES:\n" + merged_df['Weaknesses'].fillna('') + "\n\n" +
#         "### QUESTIONS:\n" + merged_df['Questions'].fillna('')
#     )
#
#     # 4. Lưu lại toàn bộ các cột bao gồm cả các cột gốc và Full_review
#     output_path = os.path.join(folder_path, 'final_combined_full_sea.jsonl')
#     merged_df.to_json(output_path, orient='records', lines=True, force_ascii=False)
#
#     print(f"Hoàn thành! File mới chứa các cột: {list(merged_df.columns)}")
#     print(f"Đã lưu tại: {output_path}")
# else:
#     print("Không thể gộp vì thiếu file đầu vào.")

import pandas as pd
import os

file_combined = r'E:\LLM_Review\processed_reviews_sea\final_combined_full_sea.jsonl'
output_folder = r'E:\LLM_Review\new_extracted_parts_sea'

if os.path.exists(file_combined):
    df = pd.read_json(file_combined, lines=True)

    # Danh sách cấu hình: Cột gốc -> Tên file -> Tiền tố ID
    parts = {
        'Summary': {'file': 'Summary.jsonl', 'prefix': 'sum'},
        'Strengths': {'file': 'Strengths.jsonl', 'prefix': 'str'},
        'Weaknesses': {'file': 'Weaknesses.jsonl', 'prefix': 'wea'},
        'Questions': {'file': 'Questions.jsonl', 'prefix': 'que'}
    }

    print(f"Đang tiến hành tách với ID độc nhất cho từng file...")

    for col_name, config in parts.items():
        if col_name in df.columns:
            # Tạo bản sao để tránh thay đổi dataframe gốc
            temp_df = df.copy()

            # TẠO ID ĐỘC NHẤT: Kết hợp tiền tố riêng của file + số thứ tự
            # Ví dụ: sum_00001, str_00001, wea_00001...
            # Như vậy không bao giờ có chuyện trùng ID giữa các file.
            temp_df['unique_review_id'] = [f"{config['prefix']}_{i:05d}_sea" for i in range(len(temp_df))]

            # Trích xuất các cột
            extracted_df = temp_df[['unique_review_id', 'paper_id', 'type', col_name, 'Full_review']]

            output_path = os.path.join(output_folder, config['file'])
            extracted_df.to_json(output_path, orient='records', lines=True, force_ascii=False)
            print(f" -> Đã xuất {config['file']} với tiền tố ID: {config['prefix']}")
        else:
            print(f" ! Bỏ qua: Cột '{col_name}' không tồn tại.")

    print("\nHoàn tất! Bây giờ ID trong 4 file là hoàn toàn khác nhau.")