# 🍽️ Zomato Refund Fraud Detection — Analytics Project

### 🔗 [**Live Dashboard →**](https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/)

Explore flagged high-risk customers, filter by city/date/risk tier, and see the risk-score breakdown for any account — no local setup required.

## 📌 Business Problem

Online food delivery platforms lose significant revenue due to fraudulent refund requests. While genuine customers occasionally request refunds, some users repeatedly exploit refund policies by submitting false complaints. The objective of this project is to identify suspicious customer behavior using data analytics, SQL, Python, and interactive dashboards to help businesses reduce financial losses.

---

## 💡 Why This Matters

Fraudulent refunds directly impact business profitability and customer trust. Instead of manually reviewing thousands of orders, this project uses behavioral analytics to detect high-risk customers based on refund patterns, complaint history, and purchasing behavior. The insights can help fraud investigation teams prioritize suspicious accounts while ensuring genuine customers continue receiving quality support.

---

## 📊 Dataset

The dataset contains **45,584 food delivery orders** with information including:

- Customer ID
- Order ID
- Order Value
- Restaurant
- City
- Delivery Partner Ratings
- Delivery Time
- Refund Requested
- Refund Amount
- Refund Reason
- Complaint Description
- Multiple Deliveries
- Customer Ratings
- Order Date

---

## 🏗️ Project Architecture

Raw Dataset
⬇
Data Cleaning & Preprocessing (Python + Pandas)
⬇
Exploratory Data Analysis (EDA)
⬇
Behavioral Pattern Analysis
⬇
Refund Risk Scoring
⬇
SQL Validation & Business Queries
⬇
Interactive Dashboard
⬇
Business Recommendations

---

## 🔍 Key Findings

- Analyzed **45,584 food delivery orders** to identify refund fraud patterns.
- Found that only a small percentage of customers generated a large share of refund losses.
- "Wrong Item" was the most common refund reason.
- "Item Not Received" showed repeated patterns among high-risk customers.
- Developed a behavioral risk scoring model using refund frequency, refund rate, repeated reasons, and complaint patterns.
- Categorized customers into Low, Medium, and High Risk segments.
- Identified accounts requiring manual investigation before approving future refunds.

---

## 💼 Business Impact

- Reduced manual fraud investigation effort by prioritizing high-risk customers.
- Enabled faster decision-making through interactive dashboards.
- Helped identify potential fraudulent refund behavior using data-driven evidence instead of assumptions.
- Demonstrated how analytics can support fraud prevention while maintaining a positive customer experience.

---

## 🛠️ Tech Stack

### Programming
- Python

### Libraries
- Pandas
- NumPy
- Matplotlib

### Database
- PostgreSQL
- SQL

### Dashboard
- Streamlit (deployed on Streamlit Community Cloud)

### Tools
- Jupyter Notebook
- VS Code
- Git
- GitHub

---

## 🚀 How to Run

**Live dashboard:** just open the [link above](https://zomato-refund-fraud-analytics-3xu24nq5hwbml78hkyirje.streamlit.app/) — nothing to install.

**To run locally:**

1. Clone the repository.
2. Install the required Python libraries: `pip install -r requirements.txt`
3. Launch the dashboard: `streamlit run dashboard/app.py`
4. (Optional) Open the Jupyter notebooks in `notebooks/` to see the underlying data generation, EDA, and risk-scoring steps.
5. Execute the SQL queries in PostgreSQL for the raw fraud-detection queries.

---

## 🗄️ SQL Queries

The project includes SQL queries for:

- Refund Analysis
- Customer Refund Frequency
- High-Risk Customer Identification
- Refund Amount Analysis
- Refund Reason Distribution
- Business KPIs
- Fraud Detection Reports

---

## 📈 Dashboard

The dashboard provides insights into:

- Total Orders
- Refund Rate
- Refund Amount
- Refund Reasons
- High-Risk Customers
- Customer Risk Distribution
- Fraud Indicators
- Business KPIs

---

## 📄 Resume Bullets

- Analyzed **45,584** food delivery orders to detect refund fraud using Python, SQL, and behavioral analytics.
- Developed a customer risk scoring framework by analyzing refund frequency, complaint patterns, and refund behavior.
- Built interactive dashboards to monitor refund trends, high-risk customers, and business KPIs.
- Automated fraud analysis workflows using Python and SQL to support data-driven business decisions.

---

## 👨‍💻 Author

**Rishi Dappu**

🎓 B.Tech – Computer Science (Data Science)

📧 Email: rishidappu16@gmail.com

🔗 LinkedIn: https://www.linkedin.com/in/rishidappu1603/

💻 GitHub: https://github.com/rishi-1603