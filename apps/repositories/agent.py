import os
import shutil
import tempfile
import git
from typing import TypedDict, Annotated, Sequence, Any
from pathlib import Path
import operator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.tools import tool

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_id: str
    repo_path: str
    index_path: str

@tool
def search_codebase(query: str, index_path: str) -> str:
    """Search the codebase for relevant snippets based on the query. Useful for finding bugs, explaining code, etc."""
    if not index_path or not os.path.exists(index_path):
        return "Error: Codebase index not found."
    
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    try:
        vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        docs = vectorstore.similarity_search(query, k=5)
        return "\n\n".join([f"File: {d.metadata.get('source')}\nContent:\n{d.page_content}" for d in docs])
    except Exception as e:
        return f"Error searching codebase: {str(e)}"

@tool
def generate_architecture_diagram(repo_path: str) -> str:
    """Generate a high-level summary of the repository structure to help create an architecture diagram."""
    if not repo_path or not os.path.exists(repo_path):
        return "Error: Repository path not found."
    
    tree = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'venv', 'node_modules', 'dist', 'build')]
        level = root.replace(repo_path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        tree.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if not f.startswith('.') and f.endswith(('.py', '.js', '.ts', '.md', '.json', '.html', '.css', '.yml', '.yaml')):
                tree.append(f"{subindent}{f}")
                
        if len(tree) > 200:
            tree.append(f"{subindent}... (truncated structure)")
            break
            
    return "Repository Structure:\n" + "\n".join(tree)

def get_agent_graph():
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    tools = [search_codebase, generate_architecture_diagram]
    llm_with_tools = llm.bind_tools(tools)
    
    def agent_node(state: AgentState):
        messages = state['messages']
        # Construct system prompt with current state info
        system_msg = f"""You are an advanced GitHub Repository Understanding Agent.
You have access to a Blackboard memory and RAG tools to understand the codebase.
When using tools, you MUST pass these exact parameters:
- index_path: '{state.get('index_path', '')}'
- repo_path: '{state.get('repo_path', '')}'

Use 'search_codebase' to explain modules, find bugs, suggest improvements, or answer questions.
Use 'generate_architecture_diagram' when asked about the structure or to draw diagrams (respond with Mermaid format if applicable).
Always give a thorough, helpful, and insightful response.
"""
        # Ensure system message is included
        if not messages or getattr(messages[0], 'type', None) != 'system':
            messages = [SystemMessage(content=system_msg)] + list(messages)
            
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
        
    def tool_node(state: AgentState):
        from langgraph.prebuilt import ToolNode
        tool_executor = ToolNode(tools)
        return tool_executor.invoke(state)
        
    def should_continue(state: AgentState):
        last_message = state['messages'][-1]
        if last_message.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()

def ingest_repository(repo_url: str, session_id: str) -> tuple[str, str]:
    """Clones the repo and builds a FAISS index. Returns (repo_path, index_path)."""
    base_dir = Path(tempfile.gettempdir()) / "repo_agent"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    repo_path = base_dir / f"repo_{session_id}"
    index_path = base_dir / f"index_{session_id}"
    
    if repo_path.exists():
        shutil.rmtree(repo_path)
        
    # Use depth=1 to clone instantly without the entire git history!
    git.Repo.clone_from(repo_url, str(repo_path), depth=1)
    
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    
    for root, _, files in os.walk(repo_path):
        if len(documents) >= 250:
            break
            
        if any(ignored in root for ignored in ['.git', '__pycache__', 'node_modules', 'venv', 'env']):
            continue
        for file in files:
            if len(documents) >= 250:
                break
                
            if file.startswith('.') or not file.endswith(('.py', '.js', '.ts', '.md', '.txt', '.html', '.css', '.json', '.rs', '.go', '.java', '.cpp', '.h')):
                continue
            
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                chunks = text_splitter.split_text(content)
                for chunk in chunks:
                    from langchain_core.documents import Document
                    documents.append(Document(
                        page_content=chunk,
                        metadata={"source": os.path.relpath(file_path, repo_path)}
                    ))
                    if len(documents) >= 250:
                        break
            except Exception:
                pass
        
    if documents:
        embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        vectorstore = FAISS.from_documents(documents, embeddings)
        vectorstore.save_local(str(index_path))
        
    return str(repo_path), str(index_path)
