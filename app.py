import re

from flask import Flask, render_template, request, jsonify
import os
import sqlite3
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import time

from langchain.agents import AgentType
from langchain_community.llms import OpenAI
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()  # Load environment variables

app = Flask(__name__)

# Fetch API key from environment variable
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY is not set. Please configure it in Azure.")

# Initialize LangChain SQL Agent with SQLite database
db = SQLDatabase.from_uri("sqlite:///retails.db")
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key, temperature=0)

# Define prompt to enforce SQL-only responses
prompt = """
You are an AI assistant that converts natural language questions into SQL queries. 
Your task is to generate *only* the SQL query without explanations, comments, or extra text. 

- Database: SQLite  
- Schema: Assume the database structure is already known to you.  
- Constraints: 
    1. *Only return the SQL query.* No extra text, explanations, or comments or final results or outputs.  
    2. *Ensure correctness* with proper column names and table references.  
    3. *Avoid assumptions* if data is unavailable—return a valid, structured SQL query.
    4. *Even if your final answer is a number, still return the SQL query as final answer only.*

Now, generate the SQL query for:
"""

# Modify the agent to use the enforced prompt
agent_executor = create_sql_agent(
    llm=llm,
    db=db,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Function to retrieve query results from database
def read_sql_query(sql, db):
    start_time = time.time()
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    col_names = [description[0] for description in cur.description]
    conn.commit()
    conn.close()
    elapsed_time = time.time() - start_time
    print(f"SQL query execution time: {elapsed_time} seconds")
    return pd.DataFrame(rows, columns=col_names)

def determine_chart_type(question):
    chart_mapping = {
        "bar chart": ["compare", "comparison", "categories", "bar chart"],
        "pie chart": ["distribution", "percentage", "proportion", "pie chart"],
        "line chart": ["trend", "time series", "over time", "line chart"]
    }
    default_chart = "bar chart"
    for chart, keywords in chart_mapping.items():
        if any(keyword in question.lower() for keyword in keywords):
            return chart
    return default_chart

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        question = request.form["question"]
        try:
            # Ensure Gemini receives the structured prompt
            full_prompt = prompt + question
            response = agent_executor.run(full_prompt).strip()
            response = re.sub(r"```sql|```", "", response).strip()

            # Fetch data from the database
            data = read_sql_query(response, "retails.db")

            # Determine chart type based on user input
            recommended_chart = determine_chart_type(question)

            if not data.empty and len(data.columns) > 1:
                if recommended_chart == "bar chart":
                    fig = px.bar(data, x=data.columns[0], y=data.columns[1],
                                 labels={'x': data.columns[0], 'y': data.columns[1]})
                elif recommended_chart == "pie chart":
                    fig = px.pie(data, names=data.columns[0], values=data.columns[1])
                elif recommended_chart == "line chart":
                    fig = px.line(data, x=data.columns[0], y=data.columns[1],
                                  labels={'x': data.columns[0], 'y': data.columns[1]})
                else:
                    fig = None
            else:
                fig = None

            return render_template("index.html", question=question, query=response,
                                   table=data.to_html(classes='table table-striped'),
                                   chart=fig.to_html(full_html=False) if fig else None)

        except Exception as e:
            return render_template("index.html", question=question, error=str(e))

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, threaded=True)
