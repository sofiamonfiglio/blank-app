# 📊 Workforce Planner — Phase 1

A browser-based staffing & resource allocation dashboard built with Streamlit.

---

## 🚀 Quick Start (5 steps)

### 1. Install Python
Download from https://www.python.org/downloads/ (version 3.10 or higher)
Make sure to check ✅ "Add Python to PATH" during installation.

### 2. Download this folder
Save the entire `workforce_planner/` folder somewhere on your computer (e.g. Desktop).

### 3. Open a terminal / command prompt
- **Windows**: Press `Win + R`, type `cmd`, press Enter
- **Mac**: Press `Cmd + Space`, type `Terminal`, press Enter

Navigate to the folder:
```
cd Desktop/workforce_planner
```

### 4. Install dependencies (one time only)
```
pip install -r requirements.txt
```

### 5. Run the app
```
streamlit run app.py
```

Your browser will automatically open to `http://localhost:8501` 🎉

---

## 📂 File Structure

```
workforce_planner/
├── app.py                  ← Main dashboard application
├── requirements.txt        ← Python packages needed
├── README.md               ← This file
└── sample_data/            ← Sample CSVs (replace with your real data)
    ├── staff.csv
    ├── projects.csv
    ├── allocations.csv
    └── pipeline.csv
```

---

## 📋 Your Data Files

Replace the sample CSVs with your real data. Use the templates downloadable from the sidebar in the app.

### staff.csv
| Column | Description | Example |
|--------|-------------|---------|
| staff_id | Unique ID | S001 |
| name | Full name | Jane Smith |
| role | Job title/role | Engineer |
| level | Seniority | Senior |
| department | Team/dept | Engineering |
| hourly_cost | Billing/cost rate | 90 |
| availability_status | active / leave | active |
| skills | Comma-separated | "structural,civil" |

### projects.csv
| Column | Description | Example |
|--------|-------------|---------|
| project_id | Unique ID | P001 |
| name | Project name | City Bridge Retrofit |
| client | Client name | Metro Authority |
| status | active / completed | active |
| type | Project type | Infrastructure |
| start_date | YYYY-MM-DD | 2025-01-15 |
| end_date | YYYY-MM-DD | 2026-06-30 |
| budget | Total budget $ | 4500000 |
| region | Geographic region | North |
| priority | High/Medium/Low | High |

### allocations.csv
| Column | Description | Example |
|--------|-------------|---------|
| allocation_id | Unique ID | A001 |
| staff_id | Links to staff.csv | S001 |
| project_id | Links to projects.csv | P001 |
| role_on_project | Role on this project | Lead Engineer |
| start_date | YYYY-MM-DD | 2025-01-15 |
| end_date | YYYY-MM-DD | 2026-06-30 |
| hours_per_week | Hours/week | 32 |
| allocation_pct | % of capacity | 80 |

### pipeline.csv
| Column | Description | Example |
|--------|-------------|---------|
| pipeline_id | Unique ID | PL001 |
| name | Project name | Highway Extension |
| client | Potential client | State DOT |
| probability_pct | Win probability 0-100 | 75 |
| est_start_date | YYYY-MM-DD | 2025-06-01 |
| est_end_date | YYYY-MM-DD | 2027-01-31 |
| est_budget | Estimated budget $ | 18000000 |
| type | Project type | Infrastructure |
| region | Region | North |
| roles_needed | Format: "2x Engineer,1x PM" | "2x Engineer,1x Project Manager" |
| notes | Any notes | In final negotiations |

---

## 🗺 Dashboard Tabs

| Tab | What it shows |
|-----|---------------|
| 📋 Staff Overview | Full roster with allocation %, filterable by role/dept/status |
| 🏗 Projects | Active project list + Gantt timeline + headcount per project |
| 📈 Utilisation | Allocation distribution, dept averages, individual spotlight |
| 🔮 Pipeline | Upcoming bids with probability, demand vs available staff |
| ⚠️ Alerts & Gaps | Automated flags: over-allocation, projects ending, role shortages |

---

## 🔮 Coming in Phase 2

- Forecasting: who frees up when, and when projects start
- Scenario modelling: "what if we win Project X?"
- AI chat assistant (ask questions in plain English)
- Historical trend analysis

---

## 💡 Tips

- **Allocation % > 100** = over-allocated (shown in red — needs attention)
- **Allocation % 80–100** = fully allocated (shown in yellow)
- **Allocation % < 80** = has available capacity (shown in green)
- The Pipeline tab uses **weighted demand** = headcount needed × win probability
- All CSV uploads are processed locally — your data never leaves your machine
