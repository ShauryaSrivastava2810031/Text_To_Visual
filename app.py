from flask import Flask, render_template, request, jsonify
import os
import sqlite3
import google.generativeai as genai
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import time

load_dotenv()  # Load environment variables

app = Flask(__name__)

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))



# Function to load gemini model and provide SQL query as response
def get_gemini_response(question, prompt):
    start_time = time.time()
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt[0], question])
    elapsed_time = time.time() - start_time
    print(f"Gemini API response time: {elapsed_time} seconds")

    clean_response = response.text.replace("`", "").strip()
    if clean_response.lower().startswith("sql"):
        clean_response = clean_response[3:].strip()

    return clean_response

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


# Prompt definition
prompt = [
    """
    You are an expert in SQL and can translate any English question into a precise and accurate 
    SQL query, even if the input contains grammatical errors, punctuation mistakes, or poorly 
    structured sentences. You have a comprehensive understanding of SQL, including SELECT, 
    INSERT, UPDATE, DELETE, JOIN, GROUP BY, ORDER BY, WHERE, HAVING, aggregate functions 
    (e.g., COUNT, AVG, SUM), string functions (e.g., CONCAT, SUBSTRING), date and time functions, 
    subqueries, indexing, and advanced techniques like window functions and CTEs 
    (Common Table Expressions).

    Make sure the SQL Query should and must not have any or at both the start and end of the 
    query. Also, it should not contain "sql" at the beginning of the query.

    **IMPORTANT RULE**:
    - The correct format is: SELECT * FROM retails_sales;

    The SQL database has the name retails and includes the following table retails_sales with 
    columns and data types:    
    Transaction_ID INT,
    Date DATE,
    Customer_ID VARCHAR(10),
    Gender VARCHAR(10),
    Age INT,
    Product_Category VARCHAR(50),
    Quantity INT,
    Price_per_Unit DECIMAL(10, 2),
    Total_Amount DECIMAL(10, 2).

    Examples:
    Question 1: How many records are in the table?
    SQL Query: SELECT COUNT(*) FROM retails_sales;

    Question 2: List all transactions for male customers.
    SQL Query: SELECT * FROM retails_sales WHERE Gender = "Male";

    Question 3: Find the average total amount spent by customers in the "Electronics" category.
    SQL Query: SELECT AVG(Total_Amount) FROM retails_sales WHERE Product_Category = "Electronics";

    Question 4: Show customer IDs and their total spending, ordered by spending in descending 
    order.
    SQL Query: SELECT Customer_ID, SUM(Total_Amount) AS Total_Spending FROM retails_sales GROUP BY Customer_ID ORDER BY Total_Spending DESC;

    Question 5: Retrieve total quantities sold grouped by product category.
    SQL Query: SELECT Product_Category, SUM(Quantity) AS Total_Quantity FROM retails_sales GROUP BY Product_Category;

    Question 6: Retrieve all records.
    SQL Query: SELECT * FROM retails_sales;

    Question 7: Add a column in the table named "Discount" with a default value of 0.
    SQL Query: ALTER TABLE retails_sales ADD COLUMN Discount DECIMAL(10, 2) DEFAULT 0;

    Always ensure the SQL query is optimized and adheres to best practices. Correct any 
    grammatical or sequence errors in the input and generate the most appropriate SQL query. 
    Handle all SQL-related questions, including complex joins, subqueries, and database 
    management tasks, with precision and efficiency.
"""
]


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        question = request.form["question"]
        response = get_gemini_response(question, prompt)

        try:
            # Fetch data from the database
            data = read_sql_query(response, "retails.db")

            # Determine chart type based on user input
            recommended_chart = determine_chart_type(question)

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

            return render_template("index.html", question=question, query=response,
                                   table=data.to_html(classes='table table-striped'),
                                   chart=fig.to_html(full_html=False) if fig else None)

        except Exception as e:
            return render_template("index.html", question=question, error=str(e))

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, threaded=True)
