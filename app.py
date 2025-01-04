import streamlit as st
import os
import dateparser
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai.llms import GoogleGenerativeAI
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
    embedding = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = FAISS.from_documents(documents, embedding)
    return vectorstore.as_retriever()

# Function to process query with the retriever
def query_document(query, retriever):
    qa_chain = RetrievalQA.from_chain_type(
        llm=GoogleGenerativeAI(model="models/gemini-2.0-flash-exp"),
        retriever=retriever,
    )
    response = qa_chain.invoke(query)
    return response

# Streamlit UI
st.title("Interactive Chatbot Interface")

# Chatbot Interaction
st.header("👋 Welcome to the Chatbot Assistant!")
st.write("You can interact with documents, ask questions, and even book appointments.")

# Step 1: Upload document
st.subheader("Step 1: Upload a Document")
uploaded_file = st.file_uploader("Please upload a document (txt, pdf, or docx)", type=["txt", "pdf", "docx"])

retriever = None
if uploaded_file:
    content = load_document_content(uploaded_file)
    if content:
        with open("uploaded_document.txt", "w") as f:
            f.write(content)
        retriever = load_retriever("uploaded_document.txt")
        st.success("Document uploaded successfully! You can now ask questions.")

# Step 2: Chat with the document
st.subheader("Step 2: Chat with the Document")
if retriever:
    query = st.text_input("Ask a question about the document:")
    if st.button("Get Response"):
        if query:
            response = query_document(query, retriever)
            if 'result' in response:
                st.write(f"**Response:** {response['result']}")
            else:
                st.warning("No answer found.")
        else:
            st.warning("Please enter a query.")

# Step 3: Book an Appointment
st.subheader("Step 3: Book an Appointment")
st.write("Fill out the form below to schedule an appointment.")

name = st.text_input("Your Name:")
phone = st.text_input("Phone Number:")
email = st.text_input("Email Address:")
date_query = st.text_input("Preferred Date (e.g., next Monday, December 25):")

if st.button("Submit Appointment Request"):
    if not name or not phone or not email or not date_query:
        st.warning("Please fill in all the fields.")
    else:
        try:
            user = UserInfo(name=name, phone_number=phone, email=email)
            if not user.validate_phone_number():
                st.error("Invalid phone number format.")
            else:
                appointment_date = extract_date(date_query)
                if "Could not parse" in appointment_date:
                    st.error(appointment_date)
                else:
                    st.success(f"Appointment successfully booked for {name} on {appointment_date}.")
        except ValidationError as e:
            st.error(f"Validation Error: {e}")
