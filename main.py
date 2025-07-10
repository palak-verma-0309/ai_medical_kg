from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()

uri = "bolt://localhost:7687"

username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(username, password))

def is_valid_relation(relation):
    with driver.session(database="medical") as session:
        result = session.run("CALL db.relationshipTypes()")
        available = []
        for record in result:
            available.extend(record.values())
        return relation in available

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

while True:
    user_input = input("\n🟢 Ask me (format: Node RELATION): ").strip()

    if user_input.lower() in ["exit", "quit"]:
        print("👋 Exiting chatbot.")
        break

    parts = user_input.split()
    if len(parts) < 2:
        print("⚠️ Please enter in format: <Node> <RELATION>")
        continue

    start_node = parts[0]
    relation = "_".join(parts[1:]).upper()

    results = get_connected_nodes(start_node, relation)

    if results:
        print(f"🔎 {start_node} {relation} → {', '.join(results)}")
    else:
        print(f"❌ No matching result found for: {start_node} -[{relation}]-> ?")
