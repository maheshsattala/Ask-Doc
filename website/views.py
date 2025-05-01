from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from website.forms import SignUpForm, AddRecordForm
from .models import Record


from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from src.prompt import system_prompt
from src.helper import load_pdf_file, text_split
from langchain_core.prompts import ChatPromptTemplate
import google.generativeai as genai
import os
from dotenv import load_dotenv


# Create your views here.
def home(request):
    records = Record.objects.all()

    #   check to see if logged in
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        #   authenticate
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "You have been logged in!")
            return redirect('home')
        else:
            messages.success(request, "There was an error logging in, Please try again...")
            return redirect('home')
    else:
        return render(request, 'home.html', {'records': records})


def login_user(request):
    pass


def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out...")
    return redirect('home')


def register_user(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            #   authenticate and login
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, "You have successfully registered!")
            return redirect('home')
    else:
        form = SignUpForm()
        return render(request, 'register.html', {'form': form})

    return render(request, 'register.html', {'form': form})


def patient_record(request, pk):
    if request.user.is_authenticated:
        individual_record = Record.objects.get(id=pk)
        return render(request, 'record.html', {'patient_record': individual_record})
    else:
        messages.success(request, "You must be logged in to view that page...")
        return redirect('home')


def delete_record(request, pk):
    if request.user.is_authenticated:
        delete_it = Record.objects.get(id=pk)
        delete_it.delete()
        messages.success(request, "Record Deleted Successfully...")
        return redirect('home')
    else:
        messages.success(request, "You Must Be Logged In To Do That...")
        return redirect('home')


def add_record(request):
    form = AddRecordForm(request.POST or None)
    if request.user.is_authenticated:
        if request.method == "POST":
            if form.is_valid():
                add_record = form.save()
                messages.success(request, "Record Added...")
                return redirect('home')
        return render(request, 'add_record.html', {'form': form})
    else:
        messages.success(request, "You Must Be Logged In...")
        return redirect('home')


def update_record(request, pk):
    if request.user.is_authenticated:
        current_record = Record.objects.get(id=pk)
        form = AddRecordForm(request.POST or None, instance=current_record)
        if form.is_valid():
            form.save()
            messages.success(request, "Record Has Been Updated!")
            return redirect('home')
        return render(request, 'update_record.html', {'form':form})
    else:
        messages.success(request, "You Must Be Logged In...")
        return redirect('home')


#   STARTING CHATBOT IMPLEMENTATION PART.

load_dotenv()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')


os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

# Configure environment variables
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load embeddings and initialize the Pinecone vector store
embeddings = download_hugging_face_embeddings()
index_name = "medicalbot"

# Set up Pinecone vector store
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)
retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 3})

# Initialize the Gemini model
model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")


def get_gemini_response(question, context):
    prompt = system_prompt.format(context=context)
    full_prompt = f"{prompt}\n\nQuestion: {question}"
    response = model.generate_content(full_prompt)
    return response.text


# Index view (renders the chatbot interface)
def index(request):
    return render(request, 'chatbot.html')


@csrf_exempt
def chat(request):
    if request.method == "POST":
        msg = request.POST.get("msg")
        context_docs = retriever.invoke(msg)
        context = "\n".join([doc.page_content for doc in context_docs])
        answer = get_gemini_response(msg, context)
        print(answer)
        return JsonResponse({"answer": answer})
    return JsonResponse({"error": "Invalid request"}, status=400)


# @csrf_exempt
# def chat(request):
#     try:
#         if request.method == "POST":
#             msg = request.POST.get("msg")
#             if not msg:
#                 return JsonResponse({"answer": "No message provided"}, status=400)
#
#             # Assuming retriever.invoke can raise exceptions
#             context_docs = retriever.invoke(msg)
#             context = "\n".join([doc.page_content for doc in context_docs])
#
#             # Assuming get_gemini_response can raise exceptions
#             answer = get_gemini_response(msg, context)
#             print(answer)
#             return JsonResponse({"answer": answer})
#
#         return JsonResponse({"answer": "Invalid request method. Only POST is allowed."}, status=405)
#
#     except Exception as e:
#         # If an exception occurs, return the error message
#         return JsonResponse({"answer": str(e)}, status=500)
