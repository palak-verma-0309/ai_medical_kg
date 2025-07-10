from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Load .env values
load_dotenv()
uri = "bolt://localhost:7687"
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

# Neo4j driver setup
driver = GraphDatabase.driver(uri, auth=(username, password))

# LLM setup for Mistral
llm = Ollama(model="mistral")

# Prompt: only extract node and relation, no explanation
extraction_prompt = PromptTemplate.from_template(
    "From the user query: '{query}', extract only the node (like a disease, symptom, etc.) and relationship (like AFFECTS, HAS_SYMPTOM, etc.).\n"
    "Respond only in this format:\nNode: <value>\nRelation: <value>"
)
extraction_chain = LLMChain(llm=llm, prompt=extraction_prompt)

# Prompt to form a sentence
sentence_prompt = PromptTemplate.from_template(
    "Given this node: '{node}', this relationship: '{relation}', and this result: '{target}', write a short simple sentence."
)
sentence_chain = LLMChain(llm=llm, prompt=sentence_prompt)

# Neo4j: validate relation type
def is_valid_relation(relation):
    with driver.session(database="medical") as session:
        result = session.run("CALL db.relationshipTypes()")
        available = []
        for record in result:
            available.extend(record.values())
        return relation in available

# Neo4j: fetch connected nodes
def get_connected_nodes(start_node, relation):
    if not is_valid_relation(relation):
        print(f"⚠️ '{relation}' is not a valid relationship type in the database.")
        return []
    query = f"""
    MATCH (a {{name: $start_name}})-[:{relation}]->(b)
    RETURN b.name AS result
    """
    with driver.session(database="medical") as session:
        results = session.run(query, start_name=start_node)
        return [record["result"] for record in results]

# Use LLM to extract node and relation
def extract_node_and_relation(user_input):
    response = extraction_chain.run(query=user_input)
    print("🧠 Extracted:\n", response)
    lines = response.strip().split("\n")
    node = None
    relation = None
    for line in lines:
        if "node" in line.lower():
            node = line.split(":")[-1].strip().capitalize()
        elif "relation" in line.lower():
            relation = line.split(":")[-1].strip().upper()
    return node, relation

# Form a sentence from result
def generate_sentence(node, relation, target):
    return sentence_chain.run(node=node, relation=relation, target=target)

# Main loop
while True:
    user_input = input("\n🟢 Ask me anything about medical knowledge: ").strip()

    if user_input.lower() in ["exit", "quit"]:
        print("👋 Exiting chatbot.")
        break

    start_node, relation = extract_node_and_relation(user_input)

    if not start_node or not relation:
        print("⚠️ Could not extract node or relation.")
        continue

    results = get_connected_nodes(start_node, relation)

    if not results:
        print(f"❌ No match found for: {start_node} -[{relation}]-> ?")
        continue

    for result_node in results:
        sentence = generate_sentence(start_node, relation, result_node)
        print("🗣️", sentence)
