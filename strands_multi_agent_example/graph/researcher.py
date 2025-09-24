#!/usr/bin/env python3
"""
Multi-Agent Research System using Strands Graph Pattern

This example demonstrates how to use the Graph multi-agent pattern to create
a research system where specialized agents work together in a structured workflow.
"""

import logging

from strands import Agent
from strands.multiagent import GraphBuilder
from strands_tools import http_request


# Enable debug logs
logging.getLogger("strands.multiagent").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)


def create_research_graph():
    """Create a multi-agent research graph with specialized agents."""
    
    # Create specialized agents
    researcher = Agent(
        name="researcher",
        system_prompt=("""
            You are a research specialist. Your job is to gather information about the given topic.
            Use the http_request tool to search one reliable source and collect the relevant data.
            Provide a well-structured research summary with source citations.
            Keep findings under 500 words.
        """),
        tools=[http_request],
        callback_handler=None  # Suppress intermediate output
    )
    
    analyst = Agent(
        name="analyst", 
        system_prompt=("""
            You are a data analysis specialist. Your job is to analyze the research findings provided to you.
            Identify key insights, patterns, and important conclusions from the research data.
            Evaluate the credibility of sources and highlight the most significant findings.
            Provide a structured analysis with clear conclusions.
            Keep analysis under 500 words.
        """),
        callback_handler=None
    )
    
    fact_checker = Agent(
        name="fact_checker",
        system_prompt=("""
            You are a fact-checking specialist. Your job is to verify the accuracy of information.
            Cross-reference claims with reliable sources and identify any potential inaccuracies.
            Rate the reliability of information and flag any questionable claims.
            Provide a fact-check report with confidence ratings.
            Keep report under 500 words.
        """),
        callback_handler=None
    )
    
    report_writer = Agent(
        name="report_writer",
        system_prompt=("""
            You are a report writing specialist. Your job is to create a comprehensive final report.
            Synthesize the research findings, analysis, and fact-check results into a coherent report.
            Structure the information logically and present it in a clear, professional format.
            Include executive summary, key findings, and conclusions.
            Keep report under 500 words.
        """)
    )
    
    # Build the graph
    builder = GraphBuilder()
    
    # Add nodes
    builder.add_node(researcher, "research")
    builder.add_node(analyst, "analysis") 
    builder.add_node(fact_checker, "fact_check")
    builder.add_node(report_writer, "report")
    
    # Add edges (dependencies)
    builder.add_edge("research", "analysis")
    builder.add_edge("research", "fact_check")
    builder.add_edge("analysis", "report")
    builder.add_edge("fact_check", "report")
    
    # Set entry point
    builder.set_entry_point("research")
    
    # Configure execution limits
    builder.set_execution_timeout(600)  # 10 minute timeout
    
    # Build and return the graph
    return builder.build()

def main():
    """Main function to run the research system."""
    print("\n🔬 Multi-Agent Research System")
    print("=" * 50)
    print("This system uses a Graph pattern with specialized agents:")
    print("• Researcher: Gathers information from web sources")
    print("• Analyst: Analyzes findings and identifies insights") 
    print("• Fact Checker: Verifies accuracy and reliability")
    print("• Report Writer: Creates comprehensive final report")
    print("=" * 50)
    
    # Create the research graph
    research_graph = create_research_graph()
    
    while True:
        try:
            # Get user input
            topic = input("\n📝 Enter research topic (or 'exit' to quit): ").strip()
            
            if topic.lower() == 'exit':
                print("\n👋 Goodbye!")
                break
                
            if not topic:
                print("Please enter a valid research topic.")
                continue
            
            print(f"\n🚀 Starting research on: {topic}")
            print("⏳ This may take a few minutes...")
            
            # Execute the graph
            result = research_graph(f"Research the following topic: {topic}")
            
            # Display results
            print(f"\n📊 Research Status: {result.status}")
            print(f"🔄 Execution Order: {[node.node_id for node in result.execution_order]}")
            print(f"⏱️  Total Time: {result.execution_time}ms")
            print(f"📈 Token Usage: {result.accumulated_usage}")
            
            # Show final report
            if "report" in result.results:
                print("\n" + "="*60)
                print("📋 FINAL RESEARCH REPORT")
                print("="*60)
                print(result.results["report"].result)
            else:
                print("\n❌ No final report generated")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Research interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")
            print("Please try a different topic.")

if __name__ == "__main__":
    main()
