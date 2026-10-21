
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from runtime.llm_usage import LLMUsageTracker
from runtime.llm_fallback import QuotaAwareLLM

import os

load_dotenv()

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = Chroma(
    persist_directory="chroma_db",
    embedding_function=embedding_model
)

llm_usage_tracker = LLMUsageTracker()

primary_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    callbacks=[llm_usage_tracker],
)

fallback_model_name = os.getenv("GEMINI_FALLBACK_MODEL")
fallback_llm = (
    ChatGoogleGenerativeAI(
        model=fallback_model_name,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        callbacks=[llm_usage_tracker],
    )
    if fallback_model_name
    else None
)

llm = QuotaAwareLLM(
    primary=primary_llm,
    fallback=fallback_llm,
)
