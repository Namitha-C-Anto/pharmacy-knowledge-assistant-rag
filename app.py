import streamlit as st
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv(override=True)

openai_api_key = os.getenv("OPENAI_API_KEY")

st.title("💊 Pharmacy Knowledge Assistant") 

with st.sidebar:
    st.title("⚙️ Settings")
    with open("sample_docs/standard treatment guidelines.pdf", "rb") as f:
        st.download_button(
            label="📥 Download Sample PDF",
            data=f,
            file_name="standard treatment guidelines.pdf",
            mime="application/pdf"
        )
    
    uploaded_files = st.file_uploader("📤 Upload Documents", accept_multiple_files=True, type="pdf")
 
if uploaded_files: 
    with st.spinner("⏳ Processing documents..."):
        documents = []

        for uploaded_file in uploaded_files:
            temp_pdf = f"temp_{uploaded_file.name}" 
            with open(temp_pdf, "wb") as file:
                file.write(uploaded_file.getvalue())
                file_name = uploaded_file.name

                #Use document loader and extend the documents list
                loader = PyPDFLoader(temp_pdf)
                loaded_docs = loader.load()
                documents.extend(loaded_docs)
    
    os.remove(temp_pdf)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splitted_docs = text_splitter.split_documents(documents)
    embedding = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=openai_api_key)
    vectorstore = FAISS.from_documents(splitted_docs, embedding)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", 
            "You are a helpful assistant. \n" 
            "Answer only from the provided context. \n"
            "Include source references like (Source: file_name, Page: X) in the answer. \n"
            "If not found, say you don't know. \n\n"
            "context: \n {context}"            
            ),
            ("user", "{question}"
            )
        ]
    ) 

    llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=openai_api_key)
    chain = prompt | llm | StrOutputParser()

    st.success("✅ Documents processed! 💡 You can now ask questions.")
    st.write(f"📄 Processed {len(documents)} pages")

    question = st.text_input("💬 Ask a question about your documents")
 
    if question:
        # Step 1: Retrieve relevant docs
        docs = retriever.invoke(question)

        # Step 2: Prepare context (simple + readable)
        context = "\n\n".join([
            f"{doc.page_content}\n(Source: {os.path.basename(doc.metadata.get('source', 'Unknown'))[5:]}, Page: {doc.metadata.get('page', 'N/A')})"
            for doc in docs
        ])

        # Step 3: Generate answer
        response = chain.invoke(
            {
                "context":context,
                "question":question
            }
        )
        st.subheader("Answer")
        st.write(response)
        
        with st.expander("🔍 Retrieved Context"):
            for i,doc in enumerate(docs):
                st.write(f"🔹 Result {i+1}")
                st.write(f"📄 {os.path.basename(doc.metadata.get('source', 'Unknown'))[5:]}")
                st.write(f"Page: {doc.metadata.get('page', "N/A")}")
                st.write(doc.page_content[:300] + "...")
                st.write("---")

else:
     
    st.info("👈 Upload PDF documents from the sidebar to begin")
