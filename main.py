from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Load environment variables
load_dotenv()
uri = "bolt://localhost:7687"
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

# Connect to Neo4j
driver = GraphDatabase.driver(uri, auth=(username, password))

# Load LLM
llm = Ollama(model="mistral")

# Improved prompt: restrict to known relationships
extraction_prompt = PromptTemplate.from_template(
    "From the user query: '{query}', extract:\n"
    "1. One **specific real node name** (like Fever, Dengue, Liver — not general types like 'disease', 'symptom').\n"
    "2. One valid relationship from this list: HAS_SYMPTOM, AFFECTS, TREATED_BY, TAKES, OCCURS_IN, CAUSED_BY.\n"
    "Respond in exactly this format (no extra explanation):\nNode: <value>\nRelation: <value>"
)


extraction_chain = LLMChain(llm=llm, prompt=extraction_prompt)

# Sentence generator
sentence_prompt = PromptTemplate.from_template(
    "Given this node: '{node}', this relationship: '{relation}', and this result: '{target}', write a short simple sentence."
)
sentence_chain = LLMChain(llm=llm, prompt=sentence_prompt)

# Clean or map relations from LLM to valid ones
def clean_relation(relation):
    relation = relation.upper().strip()
    if "(" in relation:
        relation = relation.split("(")[0].strip()
    # Synonym mapping
    mapping = {
        "IS_A_SYMPTOM_OF": "HAS_SYMPTOM",
        "SYMPTOM_OF": "HAS_SYMPTOM",
        "TREATED_WITH": "TREATED_BY",
        "IS_CAUSED_BY": "CAUSED_BY",
        "AFFECTED_PART": "AFFECTS",
        "USED_FOR": "TREATED_BY"
    }
    return mapping.get(relation, relation)

# Check if relation exists in DB
def is_valid_relation(relation):
    with driver.session(database="medical") as session:
        result = session.run("CALL db.relationshipTypes()")
        available = [rel.upper() for record in result for rel in record.values()]
        return relation.upper() in available

# Forward direction
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

# Reverse direction
def get_reverse_connected_nodes(end_node, relation):
    if not is_valid_relation(relation):
        print(f"⚠️ '{relation}' is not a valid relationship type in the database.")
        return []
    query = f"""
    MATCH (a)-[:{relation}]->(b {{name: $end_name}})
    RETURN a.name AS result
    """
    with driver.session(database="medical") as session:
        results = session.run(query, end_name=end_node)
        return [record["result"] for record in results]

# Extract using LLM
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
            relation = clean_relation(line.split(":")[-1].strip())
    return node, relation

# Sentence generator
def generate_sentence(node, relation, target):
    return sentence_chain.run(node=node, relation=relation, target=target)

# Main loop
while True:
    user_input = input("\n🟢 Ask me anything about medical knowledge (or type 'exit'): ").strip()

    if user_input.lower() in ["exit", "quit"]:
        print("👋 Exiting chatbot.")
        break

    extracted_node, relation = extract_node_and_relation(user_input)

    if not extracted_node or not relation:
        print("⚠️ Could not extract node or relation.")
        continue

    # Try forward query
    results = get_connected_nodes(extracted_node, relation)

    if not results:
        # Try reverse query
        results = get_reverse_connected_nodes(extracted_node, relation)
        if not results:
            print(f"❌ No match found for: ? -[{relation}]-> {extracted_node}")
            continue
        else:
            for result_node in results:
                sentence = generate_sentence(result_node, relation, extracted_node)
                print("🔁", sentence)
    else:
        for result_node in results:
            sentence = generate_sentence(extracted_node, relation, result_node)
            print("🗣️", sentence)
