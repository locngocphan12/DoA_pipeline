import spacy
nlp = spacy.load("en_core_web_sm")
def split_into_sentences(text):
    """Tách đoạn văn thành các câu bằng Spacy"""
    if not text or not isinstance(text, str):
        return []
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents]