import os
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun

# 1. API Key
os.environ["GOOGLE_API_KEY"] = "AIzaSyBmDGFNojE5RNAiHY77Dxh5sr-GSN6afKs" 

# 2. Initialize the Gemini Model
# Tip: If "gemini-3.1-flash-lite-preview" throws a 404/400 error, 
# temporarily change this to "gemini-2.0-flash" or "gemini-1.5-flash" to test.
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview")

# 3. Setup the Tool
search = DuckDuckGoSearchRun()

# 4. Create the LangGraph Agent
agent = create_react_agent(llm, tools=[search])

# 5. Run the Agent
inputs = {"messages": [("human", "What are the latest boAt Airdopes PRICES FOR EACH MODEL?")]}

print("--- Agent is thinking and searching ---")

# DEBUG LOOP: Catch the error and print the raw updates
try:
    # stream_mode="updates" shows us exactly which node (agent or tools) is running
    for chunk in agent.stream(inputs, stream_mode="updates"):
        for node, values in chunk.items():
            print(f"\n--- Update from node: {node} ---")
            # If it's a message from the agent, print it
            if "messages" in values:
                print(values["messages"][-1].content or "Tool Call Triggered...")
                
except Exception as e:
    print(f"\n[!] THE AGENT CRASHED. Here is the exact error:")
    print(e)