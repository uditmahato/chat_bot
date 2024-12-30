import streamlit as st
import os
import dateparser
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import TextLoader  # Updated import
from langchain_community.vectorstores import FAISS  # Updated import
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # Correct import for embeddings
from langchain_google_genai.llms import GoogleGenerativeAI  # Correct import for LLM
from pydantic import BaseModel, EmailStr, ValidationError
import phonenumbers
from PyPDF2 import PdfReader
from docx import Document

# Set up the Google credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/udit/Desktop/chat_bot/.gitignore/sharp-agent-392105-bf6377f9f1c7.json"

# Function to extract date in YYYY-MM-DD format
def extract_date(user_query):
    date = dateparser.parse(user_query)
    if date:
        return date.strftime("%Y-%m-%d")
    else:
        return "Could not parse date. Please try again."

# Function to validate user input (Name, Phone, Email)
class UserInfo(BaseModel):
    name: str
    phone_number: str
    email: EmailStr

    def validate_phone_number(self):
        try:
            parsed = phonenumbers.parse(self.phone_number, None)
            return phonenumbers.is_valid_number(parsed)
        except phonenumbers.NumberParseException:
            return False

# Function to load content from documents
def load_document_content(file):
    file_type = file.name.split(".")[-1].lower()
    if file_type == "txt":
        return file.read().decode("utf-8")
    elif file_type == "pdf":
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    elif file_type == "docx":
        doc = Document(file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    else:
        st.error("Only .txt, .pdf, and .docx files are supported.")
        return None

# Function to load documents into retriever
@st.cache_resource()
def load_retriever(file_path):
    loader = TextLoader(file_path)
    documents = loader.load()
    embedding = GoogleGenerativeAIEmbeddings(model="models/embedding-001")  # Use Gemini embeddings
    vectorstore = FAISS.from_documents(documents, embedding)
    return vectorstore.as_retriever()

# Function to process query with the retriever
def query_document(query, retriever):
    qa_chain = RetrievalQA.from_chain_type(
        llm=GoogleGenerativeAI(model="models/gemini-2.0-flash-exp"),  # Use Gemini model
        retriever=retriever,  # Pass the retriever here
    )
    response = qa_chain.invoke(query)
    return response

# Streamlit UI
st.title("Interactive Chatbot with Document Upload")

# Upload document
uploaded_file = st.file_uploader("Upload a text, PDF, or Word document", type=["txt", "pdf", "docx"])

# Process the uploaded file and generate retriever
if uploaded_file:
    content = load_document_content(uploaded_file)
    if content:
        # Save content to a temporary file
        with open("uploaded_document.txt", "w") as f:
            f.write(content)

        # Load document retriever
        retriever = load_retriever("uploaded_document.txt")
        st.success("Document uploaded and processed successfully!")

        # Chat interface
        st.subheader("Chat with the Document")
        query = st.text_input("Ask a question:")
        if st.button("Submit Query"):
            if query:
                response = query_document(query, retriever)
                if 'result' in response:
                   st.write(f"**Response:** {response['result']}")
                else:
                   st.warning("No answer found.")
            else:
                st.warning("Please enter a query.")

        # Book Appointment (Conversational form)
        st.subheader("Book an Appointment")

        # Collect user info
        name = st.text_input("Your Name:")
        phone = st.text_input("Phone Number:")
        email = st.text_input("Email Address:")
        date_query = st.text_input("Preferred Date (e.g., next Monday, December 25):")

        if st.button("Book Appointment"):
            if not name or not phone or not email or not date_query:
                st.warning("Please fill all fields.")
            else:
                # Validate phone number and email
                try:
                    user = UserInfo(name=name, phone_number=phone, email=email)
                    if not user.validate_phone_number():
                        st.error("Invalid phone number.")
                    else:
                        # Extract and validate date
                        date = extract_date(date_query)
                        if "Could not parse" in date:
                            st.error(date)
                        else:
                            st.success(f"Appointment booked for {name} on {date}.")
                except ValidationError as e:
                    st.error(f"Validation error: {e}")
