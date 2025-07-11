import streamlit as st
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

load_dotenv()
uri = "bolt://localhost:7687"
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(username, password))
llm = Ollama(model="mistral")

extraction_prompt = PromptTemplate.from_template(
    "From the user query: '{query}', extract:\n"
    "1. One **specific real node name** (like Fever, Dengue, Liver — not general types like 'disease').\n"
    "2. One valid relationship from this list: HAS_SYMPTOM, AFFECTS, TREATED_BY, TAKES, OCCURS_IN, CAUSED_BY.\n"
    "Respond only in this format:\nNode: <value>\nRelation: <value>"
)
extraction_chain = LLMChain(llm=llm, prompt=extraction_prompt)

sentence_prompt = PromptTemplate.from_template(
    "Given this node: '{node}', this relationship: '{relation}', and this result: '{target}', write a short simple sentence."
)
sentence_chain = LLMChain(llm=llm, prompt=sentence_prompt)

def clean_relation(relation):
    relation = relation.upper().strip()
    if "(" in relation:
        relation = relation.split("(")[0].strip()
    mapping = {
        "IS_A_SYMPTOM_OF": "HAS_SYMPTOM",
        "SYMPTOM_OF": "HAS_SYMPTOM",
        "TREATED_WITH": "TREATED_BY"
    }
    return mapping.get(relation, relation)

def is_valid_relation(relation):
    with driver.session(database="medical") as session:
        result = session.run("CALL db.relationshipTypes()")
        available = [rel.upper() for record in result for rel in record.values()]
        return relation.upper() in available

def is_existing_node(node_name):
    with driver.session(database="medical") as session:
        result = session.run("MATCH (n {name: $name}) RETURN COUNT(n) > 0 AS exists", name=node_name)
        return result.single()["exists"]

def get_connected_nodes(start_node, relation):
    if not is_valid_relation(relation):
        return []
    query = f"""
    MATCH (a {{name: $start_name}})-[:{relation}]->(b)
    RETURN b.name AS result
    """
    with driver.session(database="medical") as session:
        results = session.run(query, start_name=start_node)
        return [record["result"] for record in results]

def get_reverse_connected_nodes(end_node, relation):
    if not is_valid_relation(relation):
        return []
    query = f"""
    MATCH (a)-[:{relation}]->(b {{name: $end_name}})
    RETURN a.name AS result
    """
    with driver.session(database="medical") as session:
        results = session.run(query, end_name=end_node)
        return [record["result"] for record in results]

def extract_node_and_relation(user_input):
    response = extraction_chain.invoke({"query": user_input})
    lines = response["text"].strip().split("\n")
    node = None
    relation = None
    for line in lines:
        if "node" in line.lower():
            node = line.split(":")[-1].strip().capitalize()
        elif "relation" in line.lower():
            relation = clean_relation(line.split(":")[-1].strip())
    return node, relation

def generate_sentence(node, relation, target):
    return sentence_chain.invoke({"node": node, "relation": relation, "target": target})

st.set_page_config(page_title="🧠 Medical Graph Chatbot", page_icon="🩺")
st.title("🩺 Medical Knowledge Graph Chatbot")

user_input = st.text_input("Ask something about symptoms, diseases, treatments, etc.")

if user_input:
    with st.spinner("Thinking..."):
        node, relation = extract_node_and_relation(user_input)
        if not node or not relation:
            st.error("❌ Could not extract node or relation.")
        elif not is_existing_node(node):
            st.error(f"❌ '{node}' is not a valid node in the graph.")
        else:
            results = get_connected_nodes(node, relation)
            if not results:
                results = get_reverse_connected_nodes(node, relation)
                if not results:
                    st.warning(f"⚠️ No match found for: ? -[{relation}]-> {node}")
                else:
                    for r in results:
                        sentence = generate_sentence(r, relation, node)
                        if isinstance(sentence, dict) and "text" in sentence:
                            st.success(sentence["text"].strip())
                        else:
                            st.success(sentence.strip())
            else:
                for r in results:
                    sentence = generate_sentence(node, relation, r)
                    if isinstance(sentence, dict) and "text" in sentence:
                        st.success(sentence["text"].strip())
                    else:
                        st.success(sentence.strip())
