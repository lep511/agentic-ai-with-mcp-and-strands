#!/usr/bin/env python3
"""
# Agentic Workflow: Research Assistant

This example demonstrates an agentic workflow using Strands agents with web research capabilities.

## Key Features
- Specialized agent roles working in sequence
- Direct passing of information between workflow stages
- Web research using http_request and retrieve tools
- Fact-checking and information synthesis

## How to Run
1. Navigate to the example directory
2. Run: python research_assistant.py
3. Enter queries or claims at the prompt

## Example Queries
- "Thomas Edison invented the light bulb"
- "Tuesday comes before Monday in the week"

## Workflow Process
1. Researcher Agent: Gathers web information using multiple tools
2. Analyst Agent: Verifies facts and synthesizes findings
3. Writer Agent: Creates final report

If a Exa API key is provided, this agent will use Exa for web search.
Otherwise, it will check for a Tavily API key for performing a web search with Tavily.
If neither key is present, the agent will fall back to a web search with Duck Duck Go, that does not require an API key
"""

# Dependencies:
# pip install tavily-python duckduckgo_search

import json
import logging
import os

from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import http_request

logging.getLogger("strands").setLevel(logging.INFO)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s", 
    handlers=[logging.StreamHandler()],
    level = logging.INFO
)
logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', None)
EXA_API_KEY = os.getenv('EXA_API_KEY', None)

TAVILY_SYSTEM_PROMPT = """
You are a search assistant with access to the Tavily API.
You can:
1. Search the internet with a query

When displaying responses:
- Format data in a human-readable way
- Highlight important information
- Include source URLs and keep findings under 500 words
"""

EXA_SYSTEM_PROMPT = """
You are a search assistant with access to the Exa API.
You can:
1. Search the internet with a query
2. Filter results by relevance and credibility 
3. Extract key information from multiple sources

When displaying responses:
- Format data in a clear, structured way
- Highlight important information with bullet points
- Include source URLs and publication dates
- Keep findings under 500 words
- Prioritize recent and authoritative sources
"""

DUCKDUCKGO_SYSTEM_PROMPT = """
You are a search assistant with access to the Duck Duck Go API.
You can:
1. Search the internet with a query

When displaying responses:
- Format data in a human-readable way
- Highlight important information
- Include source URLs and keep findings under 500 words
"""

RESEARCHER_SYSTEM_PROMPT = """
You are a Researcher Agent that gathers information from the web.
1. Determine if the input is a research query or factual claim
2. Use your research tools (web_search, http_request, retrieve) to find relevant information
3. Include source URLs and keep findings under 500 words
"""

if EXA_API_KEY:
    from exa_py import Exa
    exa = Exa(api_key=EXA_API_KEY)
    SYSTEM_PROMPT = EXA_SYSTEM_PROMPT
    DEFAULT_SEARCH_ENGINE = "exa"
    logger.info("Exa API key found. Using the Exa API for search queries")
elif TAVILY_API_KEY:
    from tavily import TavilyClient
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    SYSTEM_PROMPT = TAVILY_SYSTEM_PROMPT
    DEFAULT_SEARCH_ENGINE = "tavily"
    logger.info("Tavily API key found. Using the Tavily API for search queries")
else:
    from duckduckgo_search import DDGS
    SYSTEM_PROMPT = DUCKDUCKGO_SYSTEM_PROMPT
    DEFAULT_SEARCH_ENGINE = "duckduckgo"
    logger.info("Tavily and EXA API keys not found. Falling back to the Duck Duck Go API for search queries")

bedrock_model = BedrockModel(
    model_id="us.amazon.nova-lite-v1:0",
    max_tokens = 2048,
    boto_client_config = Config(
        read_timeout = 120,
        connect_timeout = 120,
        retries = dict(max_attempts=3, mode="adaptive"),
    ),
    temperature=0.1
)

@tool
def web_search(query: str, max_results: int = 3, engine=DEFAULT_SEARCH_ENGINE):
    """
    Perform an internet search with the specified query using Exa, Tavily or DuckDuckGo APIs
    
    Args:
        query: A question or search phrase to perform a search with
        max_results: Maximum number of search results to return (default: 3)
        engine: Search engine to use - "exa", "tavily" or "duckduckgo" (default: "exa")
        
    Returns:
        Search results containing relevant web pages from the specified search engine
    """

    if engine == "exa":
        response = exa.search_and_contents(
            query,
            type="auto",
            text=True,
            num_results = max_results
        )
    elif engine == "tavily":
        response = tavily_client.search(
            query,
            max_results = max_results
        )
    else:
        response = DDGS().text(
            query,
            max_results = max_results
        )
    print(json.dumps(response, indent=2, default=str))
    return response

def run_research_workflow(user_input):
    """
    Run a three-agent workflow for research and fact-checking with web sources.
    Shows progress logs during execution but presents only the final report to the user.
    
    Args:
        user_input: Research query or claim to verify
        
    Returns:
        str: The final report from the Writer Agent
    """
    
    print(f"\nProcessing: '{user_input}'")
    
    # Step 1: Researcher Agent with enhanced web capabilities
    print("\nStep 1: Researcher Agent gathering web information...")

    researcher_agent = Agent(
        model = bedrock_model,
        system_prompt = RESEARCHER_SYSTEM_PROMPT,
        tools = [web_search, http_request],
        callback_handler = None
    )
    
    researcher_response = researcher_agent(
        f"Research: '{user_input}'. Use your available tools to gather information from reliable sources. "
        f"Focus on being concise and thorough, but limit web requests to 1-2 sources.",
    )
    
    # Extract only the relevant content from the researcher response
    research_findings = str(researcher_response)
    
    print("Research complete")
    print("Passing research findings to Analyst Agent...\n")
    
    # Step 2: Analyst Agent to verify facts
    print("Step 2: Analyst Agent analyzing findings...")
    
    analyst_agent = Agent(
        model=bedrock_model,
        system_prompt=(
            "You are an Analyst Agent that verifies information. "
            "1. For factual claims: Rate accuracy from 1-5 and correct if needed "
            "2. For research queries: Identify 3-5 key insights "
            "3. Evaluate source reliability and keep analysis under 400 words"
        ),
        callback_handler=None
    )

    analyst_response = analyst_agent(
        f"Analyze these findings about '{user_input}':\n\n{research_findings}",
    )
    
    # Extract only the relevant content from the analyst response
    analysis = str(analyst_response)
    
    print("Analysis complete")
    print("Passing analysis to Writer Agent...\n")
    
    # Step 3: Writer Agent to create report
    print("Step 3: Writer Agent creating final report...")
    
    writer_agent = Agent(
        model=bedrock_model,
        system_prompt=(
            "You are a Writer Agent that creates clear reports. "
            "1. For fact-checks: State whether claims are true or false "
            "2. For research: Present key insights in a logical structure "
            "3. Keep reports under 500 words with brief source mentions"
        )
    )
    
    # Execute the Writer Agent with the analysis (output is shown to user)
    final_report = writer_agent(
        f"Create a report on '{user_input}' based on this analysis:\n\n{analysis}"
    )
    
    print("Report creation complete")
    
    # Return the final report
    return final_report


if __name__ == "__main__":
    # Print welcome message
    print("\nAgentic Workflow: Research Assistant\n")
    print("This demo shows Strands agents in a workflow with web research")
    print("using web search APIs: Tavily (if an API key is available) and")
    print("fallback to the Duck Duck Go or httpe_request tools")
    print("\nOptions:")
    print("  'demo' - Demonstrate search example")
    print("  'exit' - Exit the program")
    print("  'web search on [search item]' - Perform web search on search item")
    print("\nTry research questions or fact-check claims.")
    print("\nExamples:")
    print("- \"What are quantum computers?\"")
    print("- \"Lemon cures cancer\"")
    print("- \"What is the news right now vibe coding?\"")
    print("- \"Web search on interest rates\"")
    
    # Interactive loop
    while True:
        try:
            user_input = input("\n> ")

            if user_input.lower() in [ "exit", "quit" ]:
                print("\nGoodbye! 👋")
                break
            
            if user_input.lower().startswith("web search on"):
                # Perform regular web search
                web_agent = Agent(
                    model = bedrock_model,
                    system_prompt = SYSTEM_PROMPT,
                    tools = [web_search],
                    callback_handler = None
                )
                response = web_agent(user_input)
                print(response)
            else:
                # Process the input through the workflow of agents
                final_report = run_research_workflow(user_input)
        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try a different request.")
