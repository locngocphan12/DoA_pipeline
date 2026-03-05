# Danh gia ti le Premise, Ti le các phuong phap cua cac cau Premise.
# Ti le Premise, theo cac phan.
# Hien tai la se chi tong hop duoc ket qua cua Summary, Strength.

import pandas as pd


def calculate_detailed_premise_ratio(human_file_path, llm_file_path):
    print("Loading data...")
    try:
        df_human = pd.read_json(human_file_path, lines=True)
        df_llm = pd.read_json(llm_file_path, lines=True)
    except FileNotFoundError as e:
        print(f"Error loading files: {e}")
        return

    # Gộp 2 dataframe lại để xử lý chung
    df_combined = pd.concat([df_human, df_llm], ignore_index=True)

    # ==========================================
    # 1. TỈ LỆ TỔNG QUÁT (OVERALL RATIO)
    # ==========================================
    print("\n" + "=" * 50)
    print("1. OVERALL ARGUMENT MINING STATISTICS")
    print("=" * 50)

    overall_stats = df_combined.groupby('Reviewer_Type').agg(
        Total_Sentences=('Sentence', 'count'),
        Premise_Count=('Is_Premise', 'sum')
    )
    overall_stats['Claim_Count'] = overall_stats['Total_Sentences'] - overall_stats['Premise_Count']
    overall_stats['Premise_Ratio (%)'] = (
                overall_stats['Premise_Count'] / overall_stats['Total_Sentences'] * 100).round(2)
    overall_stats['Claim_Ratio (%)'] = (overall_stats['Claim_Count'] / overall_stats['Total_Sentences'] * 100).round(2)

    overall_stats = overall_stats[
        ['Total_Sentences', 'Claim_Count', 'Claim_Ratio (%)', 'Premise_Count', 'Premise_Ratio (%)']]
    print(overall_stats.to_string())

    # ==========================================
    # 2. TỈ LỆ THEO TỪNG PHẦN (SECTION-WISE RATIO)
    # ==========================================
    print("\n" + "=" * 50)
    print("2. SECTION-WISE ARGUMENT MINING STATISTICS")
    print("=" * 50)

    # Group by thêm trường 'Section'
    section_stats = df_combined.groupby(['Reviewer_Type', 'Section']).agg(
        Total_Sentences=('Sentence', 'count'),
        Premise_Count=('Is_Premise', 'sum')
    )
    section_stats['Claim_Count'] = section_stats['Total_Sentences'] - section_stats['Premise_Count']
    section_stats['Premise_Ratio (%)'] = (
                section_stats['Premise_Count'] / section_stats['Total_Sentences'] * 100).round(2)
    section_stats['Claim_Ratio (%)'] = (section_stats['Claim_Count'] / section_stats['Total_Sentences'] * 100).round(2)

    section_stats = section_stats[
        ['Total_Sentences', 'Claim_Count', 'Claim_Ratio (%)', 'Premise_Count', 'Premise_Ratio (%)']]
    print(section_stats.to_string())

    # Xuất ra file CSV để dễ dàng copy vào Excel/Word làm báo cáo
    # section_stats.to_csv("section_wise_argument_stats.csv")
    # print("\n>>> Results saved to 'section_wise_argument_stats.csv'")


def analyze_aspect_distribution(human_file_path, llm_file_path):
    print("Loading data...")
    try:
        df_human = pd.read_json(human_file_path, lines=True)
        df_llm = pd.read_json(llm_file_path, lines=True)
    except FileNotFoundError as e:
        print(f"Error loading files: {e}")
        return

    # Gộp 2 dataframe
    df = pd.concat([df_human, df_llm], ignore_index=True)

    # ==========================================
    # BƯỚC 1: LÀM SẠCH DỮ LIỆU (DATA CLEANING)
    # ==========================================
    # Gộp các nhãn Methodology theo yêu cầu
    df['Aspect_Label'] = df['Aspect_Label'].replace({
        'METHODOLOGY (INTERNAL LOGIC, THEORY & DESIGN)': 'METHODOLOGY'
    })

    # Các nhãn chính (Core aspects)
    core_aspects = ['METHODOLOGY', 'EXPERIMENTS', 'RELATED_WORK', 'PRESENTATION']

    # Những nhãn không phải Core Aspect và không phải N/A (Claim) thì gom vào 'OTHER'
    is_noise = ~df['Aspect_Label'].isin(core_aspects) & (df['Aspect_Label'] != 'N/A')
    df.loc[is_noise, 'Aspect_Label'] = 'OTHER_ASPECTS'

    # Chỉ phân tích các câu là Premise (Loại bỏ N/A / Claims)
    df_premises = df[df['Aspect_Label'] != 'N/A'].copy()

    # ==========================================
    # BƯỚC 2: OVERALL ASPECT DISTRIBUTION
    # ==========================================
    print("\n" + "=" * 60)
    print("1. OVERALL ASPECT DISTRIBUTION (PREMISES ONLY)")
    print("=" * 60)

    # Tính tổng số Premise của mỗi Reviewer
    total_premises_per_reviewer = df_premises.groupby('Reviewer_Type')['Sentence'].count().rename('Total_Premises')

    # Tính số lượng từng Aspect
    overall_aspects = df_premises.groupby(['Reviewer_Type', 'Aspect_Label']).size().unstack(fill_value=0)

    # Nối tổng số vào để tính phần trăm
    overall_aspects = overall_aspects.join(total_premises_per_reviewer)

    # Tính phần trăm cho từng cột Aspect (so với Total Premises)
    for col in overall_aspects.columns:
        if col != 'Total_Premises':
            overall_aspects[f'{col} (%)'] = (overall_aspects[col] / overall_aspects['Total_Premises'] * 100).round(2)

    # Sắp xếp lại cột cho dễ nhìn
    cols = ['Total_Premises'] + [col for col in overall_aspects.columns if col != 'Total_Premises']
    overall_aspects = overall_aspects[cols]

    print(overall_aspects.to_string())

    # ==========================================
    # BƯỚC 3: SECTION-WISE ASPECT DISTRIBUTION
    # ==========================================
    print("\n" + "=" * 60)
    print("2. SECTION-WISE ASPECT DISTRIBUTION")
    print("=" * 60)

    # Tính tổng số Premise theo từng Section của mỗi Reviewer
    total_premises_section = df_premises.groupby(['Reviewer_Type', 'Section'])['Sentence'].count().rename(
        'Total_Premises')

    # Đếm số lượng Aspect
    section_aspects = df_premises.groupby(['Reviewer_Type', 'Section', 'Aspect_Label']).size().unstack(fill_value=0)
    section_aspects = section_aspects.join(total_premises_section)

    # Tính phần trăm
    for col in section_aspects.columns:
        if col != 'Total_Premises':
            section_aspects[f'{col} (%)'] = (section_aspects[col] / section_aspects['Total_Premises'] * 100).round(2)

    # Lọc cột hiển thị
    section_aspects = section_aspects[cols]
    print(section_aspects.to_string())

    # Xuất ra file CSV
    # overall_aspects.to_csv("overall_aspect_distribution.csv")
    # section_aspects.to_csv("section_wise_aspect_distribution.csv")
    # print("\n>>> Results saved to CSV files.")


import numpy as np


def format_mean_std(mean_series, std_series):
    """Helper function to format Mean and Std into 'Mean ± Std' strings."""
    return mean_series.round(2).astype(str) + " ± " + std_series.round(2).astype(str)


def calculate_macro_statistics(human_file_path, llm_file_path):
    print("Loading data...")
    try:
        df_human = pd.read_json(human_file_path, lines=True)
        df_llm = pd.read_json(llm_file_path, lines=True)
    except FileNotFoundError as e:
        print(f"Error loading files: {e}")
        return

    # Combine datasets
    df = pd.concat([df_human, df_llm], ignore_index=True)

    # Ensure the unique identifier exists
    review_id_col = 'unique_review_id' if 'unique_review_id' in df.columns else 'Paper_ID'

    # ==============================================================================
    # PART 1: ARGUMENT LABEL ANALYSIS (PREMISE RATIO)
    # ==============================================================================
    print("\n" + "=" * 80)
    print(" PART 1: ARGUMENT LABEL (PREMISE RATIO % PER REVIEW)")
    print("=" * 80)

    # Calculate Premise Ratio for EACH individual review
    review_args = df.groupby(['Reviewer_Type', 'Section', review_id_col]).agg(
        Total_Sentences=('Sentence', 'count'),
        Premise_Count=('Is_Premise', 'sum')
    ).reset_index()

    review_args['Premise_Ratio'] = (review_args['Premise_Count'] / review_args['Total_Sentences']) * 100
    review_args['Premise_Ratio'] = review_args['Premise_Ratio'].fillna(0)  # Handle edge cases

    # 1A. Overall Premise Ratio (Human vs. LLM)
    overall_args = review_args.groupby('Reviewer_Type').agg(
        Num_Reviews=(review_id_col, 'count'),
        Premise_Ratio_Mean=('Premise_Ratio', 'mean'),
        Premise_Ratio_Std=('Premise_Ratio', 'std')
    ).reset_index()

    overall_args['Premise Ratio (%)'] = format_mean_std(overall_args['Premise_Ratio_Mean'],
                                                        overall_args['Premise_Ratio_Std'])
    print("\n--- 1A. OVERALL ARGUMENT DISTRIBUTION ---")
    print(overall_args[['Reviewer_Type', 'Num_Reviews', 'Premise Ratio (%)']].to_string(index=False))

    # 1B. Section-wise Premise Ratio
    section_args = review_args.groupby(['Reviewer_Type', 'Section']).agg(
        Num_Reviews=(review_id_col, 'count'),
        Premise_Ratio_Mean=('Premise_Ratio', 'mean'),
        Premise_Ratio_Std=('Premise_Ratio', 'std')
    ).reset_index()

    section_args['Premise Ratio (%)'] = format_mean_std(section_args['Premise_Ratio_Mean'],
                                                        section_args['Premise_Ratio_Std'])
    print("\n--- 1B. SECTION-WISE ARGUMENT DISTRIBUTION ---")
    print(section_args[['Reviewer_Type', 'Section', 'Num_Reviews', 'Premise Ratio (%)']].to_string(index=False))

    # ==============================================================================
    # PART 2: ASPECT LABEL ANALYSIS (ONLY FOR PREMISES)
    # ==============================================================================
    print("\n\n" + "=" * 80)
    print(" PART 2: ASPECT LABEL DISTRIBUTION (PREMISES ONLY - % PER REVIEW)")
    print("=" * 80)
    target_sections = ['Summary', 'Strengths']
    # Filter out Claims (Is_Premise == 0 or Aspect_Label == 'N/A')
    # df_premises = df[(df['Is_Premise'] == 1) & (df['Aspect_Label'] != 'N/A')].copy()
    df_premises = df[
        (df['Is_Premise'] == 1) &
        (df['Aspect_Label'] != 'N/A') &
        (df['Section'].isin(target_sections))
    ].copy()
    # Data Cleaning: Merge Methodology and group noise
    df_premises['Aspect_Label'] = df_premises['Aspect_Label'].replace({
        'METHODOLOGY (INTERNAL LOGIC, THEORY & DESIGN)': 'METHODOLOGY'
    })

    core_aspects = ['METHODOLOGY', 'EXPERIMENTS', 'RELATED_WORK', 'PRESENTATION']
    is_noise = ~df_premises['Aspect_Label'].isin(core_aspects)
    df_premises.loc[is_noise, 'Aspect_Label'] = 'OTHER_ASPECTS'

    # Create a Pivot Table counting Aspects per review
    aspect_counts = df_premises.pivot_table(
        index=['Reviewer_Type', 'Section', review_id_col],
        columns='Aspect_Label',
        values='Sentence',
        aggfunc='count',
        fill_value=0
    )

    # Convert counts to percentages for each review (Row-wise percentage)
    aspect_ratios = aspect_counts.div(aspect_counts.sum(axis=1), axis=0) * 100
    aspect_ratios = aspect_ratios.fillna(0).reset_index()

    # Core aspect columns to analyze
    aspect_cols = [c for c in aspect_ratios.columns if c not in ['Reviewer_Type', 'Section', review_id_col]]

    # 2A. Overall Aspect Distribution
    print("\n--- 2A. OVERALL ASPECT DISTRIBUTION ---")
    overall_aspects = aspect_ratios.groupby('Reviewer_Type')[aspect_cols].agg(['mean', 'std'])

    overall_aspect_formatted = pd.DataFrame(index=overall_aspects.index)
    for col in aspect_cols:
        overall_aspect_formatted[col + ' (%)'] = format_mean_std(overall_aspects[(col, 'mean')],
                                                                 overall_aspects[(col, 'std')])

    print(overall_aspect_formatted.reset_index().to_string(index=False))

    # 2B. Section-wise Aspect Distribution
    print("\n--- 2B. SECTION-WISE ASPECT DISTRIBUTION ---")
    section_aspects = aspect_ratios.groupby(['Reviewer_Type', 'Section'])[aspect_cols].agg(['mean', 'std'])

    section_aspect_formatted = pd.DataFrame(index=section_aspects.index)
    for col in aspect_cols:
        section_aspect_formatted[col + ' (%)'] = format_mean_std(section_aspects[(col, 'mean')],
                                                                 section_aspects[(col, 'std')])

    print(section_aspect_formatted.reset_index().to_string(index=False))

    # Optional: Save final aggregated tables to CSV
    overall_args.to_csv("macro_argument_overall.csv", index=False)
    section_args.to_csv("macro_argument_section.csv", index=False)
    overall_aspect_formatted.to_csv("macro_aspect_overall.csv")
    section_aspect_formatted.to_csv("macro_aspect_section.csv")
    # print("\n>>> CSV Exports completed successfully.")

# ==========================================
# EXECUTION
# ==========================================
if __name__ == "__main__":
    # Replace these with your actual file paths
    HUMAN_RESULTS_FILE = "E:\\LLM_Review\\evaluation\\result_jsonl\\final_merged_dataset_v1_human_.jsonl"
    LLM_RESULTS_FILE = "E:\\LLM_Review\\evaluation\\result_jsonl\detailed_argument_mining_results_v1_sea.jsonl"

    calculate_macro_statistics(HUMAN_RESULTS_FILE, LLM_RESULTS_FILE)