import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

st.set_page_config(page_title="Workforce Planner", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
[data-testid="stSidebar"]{background:#0f1117;border-right:1px solid #1e2433;}
[data-testid="stSidebar"] *{color:#e2e8f0 !important;}
.main{background:#f8fafc;}
.metric-card{background:white;border:1px solid #e2e8f0;border-radius:12px;padding:18px 22px;box-shadow:0 1px 3px rgba(0,0,0,0.06);}
.metric-value{font-size:2rem;font-weight:700;color:#0f172a;line-height:1;}
.metric-label{font-size:0.74rem;font-weight:500;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-top:4px;}
.metric-sub{font-size:.78rem;font-weight:500;margin-top:5px;}
.c-green{color:#10b981;} .c-amber{color:#f59e0b;} .c-red{color:#ef4444;} .c-blue{color:#3b82f6;}
.sh{font-size:.70rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.10em;
    padding-bottom:8px;border-bottom:1px solid #e2e8f0;margin-bottom:14px;margin-top:4px;}
.aw{background:#fffbeb;border:1px solid #fde68a;border-left:4px solid #f59e0b;
    border-radius:8px;padding:12px 16px;margin:6px 0;font-size:.86rem;color:#78350f;}
.ad{background:#fef2f2;border:1px solid #fecaca;border-left:4px solid #ef4444;
    border-radius:8px;padding:12px 16px;margin:6px 0;font-size:.86rem;color:#7f1d1d;}
.ag{background:#f0fdf4;border:1px solid #bbf7d0;border-left:4px solid #10b981;
    border-radius:8px;padding:12px 16px;margin:6px 0;font-size:.86rem;color:#14532d;}
.ai{background:#eff6ff;border:1px solid #bfdbfe;border-left:4px solid #3b82f6;
    border-radius:8px;padding:12px 16px;margin:6px 0;font-size:.86rem;color:#1e3a5f;}
.rc{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:14px 18px;
    margin:6px 0;box-shadow:0 1px 3px rgba(0,0,0,.04);}
.rc h4{margin:0 0 5px 0;font-size:.92rem;color:#0f172a;}
.rc p{margin:0;font-size:.82rem;color:#475569;}
.tag{display:inline-block;padding:2px 8px;border-radius:12px;font-size:.70rem;font-weight:600;margin-right:4px;}
.tg{background:#dcfce7;color:#166534;} .ty{background:#fef9c3;color:#713f12;} .tr{background:#fef2f2;color:#991b1b;}
.hero-tab{border:2px solid #e2e8f0;border-radius:12px;padding:6px 12px;background:white;}
#MainMenu{visibility:hidden;}footer{visibility:hidden;}
</style>""", unsafe_allow_html=True)

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_data")

# ── helpers ────────────────────────────────────────────────────────────────────
def load_staffing_export(f):
    if f is not None:
        raw = pd.read_csv(f)
    else:
        p = os.path.join(SAMPLE_DIR, "staffing_export.csv")
        raw = pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()
    if not raw.empty:
        raw.columns = [c.strip() for c in raw.columns]
    return raw

def load_pipeline_csv(f):
    if f is not None:
        return pd.read_csv(f)
    p = os.path.join(SAMPLE_DIR, "pipeline.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

def parse_dates(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")
    return df

def parse_roles(s):
    out = []
    for item in str(s).split(","):
        item = item.strip()
        if not item or item == "nan": continue
        try:
            p = item.split("x", 1)
            out.append((p[1].strip() if len(p) > 1 else item, int(p[0].strip())))
        except:
            out.append((item, 1))
    return out

def build_tables(raw):
    raw = parse_dates(raw, ["Project Start Date","Project End Date",
                             "Assignment Start Date","Assignment End Date"])
    today = pd.Timestamp(datetime.today().date())

    su = raw.drop_duplicates(subset=["Person Assigned"]).copy()
    su = su.rename(columns={
        "Person Assigned":"name", "Role":"role", "Role Description":"role_desc",
        "Current Project Name":"current_project", "Project Status":"project_status",
        "Assignment Start Date":"assign_start", "Assignment End Date":"assign_end",
        "Next Project Name":"next_project",
    })
    su["staff_id"] = "S" + (pd.RangeIndex(len(su)) + 1).astype(str).str.zfill(3)

    def is_assigned(row):
        proj = str(row.get("current_project","")).strip()
        if not proj or proj == "nan": return False
        s, e = row.get("assign_start"), row.get("assign_end")
        if pd.isna(s) or pd.isna(e): return True   # project but no dates = assume assigned
        return s <= today <= e

    su["assigned"] = su.apply(is_assigned, axis=1)
    su["status_label"] = su["assigned"].map({True: "Assigned", False: "Available"})
    su["total_allocation_pct"] = su["assigned"].map({True: 100, False: 0})

    proj_raw = raw[raw["Current Project Name"].notna() & (raw["Current Project Name"].str.strip() != "")]
    projects = proj_raw.groupby("Current Project Name").agg(
        start_date=("Project Start Date","first"),
        end_date=("Project End Date","first"),
        status=("Project Status","first"),
        headcount=("Person Assigned","nunique"),
    ).reset_index().rename(columns={"Current Project Name":"name"})
    projects["project_id"] = "P" + (pd.RangeIndex(len(projects)) + 1).astype(str).str.zfill(3)

    alloc = proj_raw.copy().rename(columns={
        "Person Assigned":"name", "Current Project Name":"project_name",
        "Assignment Start Date":"start_date", "Assignment End Date":"end_date", "Role":"role",
    })
    alloc = alloc.merge(su[["name","staff_id"]], on="name", how="left")
    alloc = alloc.merge(projects[["name","project_id"]].rename(columns={"name":"project_name"}),
                        on="project_name", how="left")
    alloc["allocation_pct"] = 100
    return su, projects, alloc

# ── sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Workforce Planner")
    st.markdown("<div style='color:#475569;font-size:.76rem;margin-bottom:20px;'>Resource Planning & Hiring Intelligence</div>", unsafe_allow_html=True)
    st.markdown("<div class='sh'>Upload Data</div>", unsafe_allow_html=True)
    st.caption("Leave blank to use sample data")
    up_staff    = st.file_uploader("Staffing export", type="csv", key="staff",
        help="Columns: Current Project Name, Project Start Date, Project End Date, Project Status, Role, Role Description, Person Assigned, Assignment Start Date, Assignment End Date, Next Project Name")
    up_pipeline = st.file_uploader("Pipeline projects", type="csv", key="pipe",
        help="Columns: name, client, probability_pct, est_start_date, est_end_date, est_budget, type, region, roles_needed, notes")
    if not any([up_staff, up_pipeline]):
        st.info("📋 Using sample data")
    st.markdown("---")
    st.markdown("<div class='sh'>CSV Templates</div>", unsafe_allow_html=True)
    t1 = "Current Project Name,Project Start Date,Project End Date,Project Status,Role,Role Description,Person Assigned,Assignment Start Date,Assignment End Date,Next Project Name\nDowntown Transit Hub,01/01/2025,31/12/2025,Active,Project Manager,Leads project delivery,Jane Smith,01/01/2025,31/12/2025,Future Project\n,,,Unassigned,Analyst,Data analysis,Sam Lee,,,"
    t2 = "name,client,probability_pct,est_start_date,est_end_date,est_budget,type,region,roles_needed,notes\nHighway Extension,State DOT,80,01/06/2025,01/06/2027,18000000,Infrastructure,North,\"2x Engineer,1x Project Manager\",In negotiations"
    st.download_button("⬇ staffing_export_template.csv", t1, "staffing_export_template.csv", "text/csv", use_container_width=True)
    st.download_button("⬇ pipeline_template.csv",        t2, "pipeline_template.csv",        "text/csv", use_container_width=True)

# ── load data ──────────────────────────────────────────────────────────────────
raw      = load_staffing_export(up_staff)
pipeline = load_pipeline_csv(up_pipeline)

if raw.empty:
    st.error("Could not load staffing data. Check your CSV or ensure sample_data/staffing_export.csv exists.")
    st.stop()

if not pipeline.empty:
    pipeline = parse_dates(pipeline, ["est_start_date","est_end_date"])

staff_util, projects, allocations = build_tables(raw)
today_dt = pd.Timestamp(datetime.today().date())

active_projects = projects[projects["status"].str.lower() == "active"] if "status" in projects.columns else projects

alloc_active = pd.DataFrame()
if not allocations.empty and "start_date" in allocations.columns:
    alloc_active = allocations[
        (allocations["start_date"] <= today_dt) & (allocations["end_date"] >= today_dt)
    ]

total_staff   = len(staff_util)
assigned_n    = staff_util["assigned"].sum()
available_n   = total_staff - assigned_n
util_rate     = assigned_n / total_staff * 100 if total_staff else 0
active_proj_n = len(active_projects)
pursuit_n     = len(pipeline) if not pipeline.empty else 0

# ── kpi card renderer ──────────────────────────────────────────────────────────
def kpi(col, value, label, sub="", sub_class="c-blue"):
    sub_html = f'<div class="metric-sub {sub_class}">{sub}</div>' if sub else ""
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-label">{label}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True
    )

# ── header ─────────────────────────────────────────────────────────────────────
st.markdown("# Workforce Planning Dashboard")
st.markdown(
    f"<p style='color:#94a3b8;font-size:.84rem;margin-bottom:24px;'>"
    f"As of {today_dt.strftime('%B %d, %Y')}</p>",
    unsafe_allow_html=True
)

c1,c2,c3,c4,c5,c6 = st.columns(6)
kpi(c1, total_staff,          "Total Staff")
kpi(c2, active_proj_n,        "Active Projects")
kpi(c3, pursuit_n,            "Pursuits",
    "In pipeline" if pursuit_n else "No pipeline loaded", "c-blue")
kpi(c4, f"{util_rate:.0f}%",  "Assignment Rate",
    "⚠ High demand" if util_rate > 90 else "✓ Healthy",
    "c-amber" if util_rate > 90 else "c-green")
kpi(c5, int(assigned_n),      "Currently Assigned", "On a project", "c-green")
kpi(c6, int(available_n),     "Available",
    "⚠ Deploy them" if available_n == 0 else f"{available_n} on bench",
    "c-amber" if available_n == 0 else "c-green")

st.markdown("<br>", unsafe_allow_html=True)

# ── tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋  Staff",
    "🏗  Projects",
    "🎯  Scenario Modeller",
    "📅  Capacity Forecast",
    "📊  Hiring Planner",
    "⚠️  Alerts",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — STAFF
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    cl, cr = st.columns([2, 1])
    with cl:
        st.markdown("<div class='sh'>Staff Roster</div>", unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        roles_list   = ["All"] + sorted(staff_util["role"].dropna().unique().tolist())
        status_opts  = ["All", "Assigned", "Available"]
        nxt_opts     = ["All", "Has next project", "No next project"]
        sel_role   = r1.selectbox("Role",         roles_list)
        sel_status = r2.selectbox("Status",        status_opts)
        sel_nxt    = r3.selectbox("Next project",  nxt_opts)

        disp = staff_util.copy()
        if sel_role   != "All": disp = disp[disp["role"] == sel_role]
        if sel_status != "All": disp = disp[disp["status_label"] == sel_status]
        if sel_nxt == "Has next project":
            disp = disp[disp["next_project"].notna() & (disp["next_project"].astype(str).str.strip() != "")]
        elif sel_nxt == "No next project":
            disp = disp[disp["next_project"].isna() | (disp["next_project"].astype(str).str.strip() == "")]

        cols = [c for c in ["name","role","current_project","status_label","assign_end","next_project"] if c in disp.columns]

        def style_status(val):
            if val == "Assigned":  return "background-color:#f0fdf4;color:#166534;font-weight:500"
            if val == "Available": return "background-color:#fef9c3;color:#713f12;font-weight:500"
            return ""

        styled = disp[cols].rename(columns={
            "name":"Name","role":"Role","current_project":"Current Project",
            "status_label":"Status","assign_end":"Ends","next_project":"Next Project"
        }).style.applymap(style_status, subset=["Status"])
        st.dataframe(styled, use_container_width=True, height=460)
        st.caption(f"Showing {len(disp)} of {total_staff} staff")

    with cr:
        st.markdown("<div class='sh'>Assignment Overview</div>", unsafe_allow_html=True)
        sc = staff_util["status_label"].value_counts().reset_index()
        sc.columns = ["Status","Count"]
        fig_pie = px.pie(sc, values="Count", names="Status", hole=0.58,
            color="Status", color_discrete_map={"Assigned":"#10b981","Available":"#f59e0b"})
        fig_pie.update_traces(textposition="outside", textinfo="percent+label")
        fig_pie.update_layout(showlegend=False, margin=dict(t=10,b=10,l=10,r=10),
            height=220, paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("<div class='sh'>Assignment Rate by Role</div>", unsafe_allow_html=True)
        ra = staff_util.groupby("role").agg(
            total=("name","count"),
            assigned=("assigned", "sum")
        ).reset_index()
        ra["pct"] = (ra["assigned"] / ra["total"] * 100).round(1)
        ra = ra.sort_values("pct", ascending=True)
        fig_ra = px.bar(ra, x="pct", y="role", orientation="h",
            color="pct", color_continuous_scale=["#10b981","#f59e0b","#ef4444"],
            range_color=[50,100],
            labels={"pct":"Assignment %","role":""},
            custom_data=["total","assigned"])
        fig_ra.update_traces(hovertemplate="<b>%{y}</b><br>%{x:.0f}% assigned (%{customdata[1]} of %{customdata[0]})<extra></extra>")
        fig_ra.add_vline(x=100, line_dash="dash", line_color="#ef4444", opacity=0.4)
        fig_ra.update_layout(height=300, margin=dict(t=0,b=0,l=0,r=10),
            paper_bgcolor="white", plot_bgcolor="white", coloraxis_showscale=False,
            xaxis=dict(range=[0,110]), yaxis=dict(showgrid=False))
        st.plotly_chart(fig_ra, use_container_width=True)

        st.markdown("<div class='sh'>Next Project Lined Up</div>", unsafe_allow_html=True)
        has_nxt = (staff_util["next_project"].notna() & (staff_util["next_project"].astype(str).str.strip() != "")).sum()
        no_nxt  = total_staff - has_nxt
        c_a, c_b = st.columns(2)
        c_a.metric("Have next project", int(has_nxt))
        c_b.metric("No next project",   int(no_nxt),  delta=f"⚠ {no_nxt} at risk" if no_nxt > 15 else None, delta_color="inverse")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PROJECTS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("<div class='sh'>Active Projects</div>", unsafe_allow_html=True)
    pa, pb = st.columns([3, 2])
    with pa:
        show_proj = [c for c in ["name","status","start_date","end_date","headcount"] if c in projects.columns]
        st.dataframe(
            projects[show_proj].rename(columns={"name":"Project","status":"Status",
                "start_date":"Start","end_date":"End","headcount":"# Staff"}),
            use_container_width=True, height=400
        )
    with pb:
        st.markdown("<div class='sh'>Timeline</div>", unsafe_allow_html=True)
        gantt = projects.dropna(subset=["start_date","end_date"]).sort_values("start_date")
        if not gantt.empty:
            fig_g = go.Figure()
            for _, row in gantt.iterrows():
                lbl = row.get("name","")
                fig_g.add_trace(go.Bar(
                    x=[(row["end_date"]-row["start_date"]).days], y=[lbl],
                    base=[row["start_date"]], orientation="h",
                    marker_color="#3b82f6", marker_line_width=0, showlegend=False,
                    hovertemplate=f"<b>{lbl}</b><br>Start: {row['start_date'].date()}<br>End: {row['end_date'].date()}<br>{int(row.get('headcount',0))} staff<extra></extra>"
                ))
            fig_g.add_shape(type="line",
                x0=str(today_dt.date()), x1=str(today_dt.date()),
                y0=0, y1=1, xref="x", yref="paper",
                line=dict(color="#ef4444", width=2, dash="dot"))
            fig_g.add_annotation(
                x=str(today_dt.date()), y=1, xref="x", yref="paper",
                text="Today", showarrow=False,
                font=dict(color="#ef4444", size=11),
                xanchor="left", yanchor="bottom")
            fig_g.update_layout(height=420, barmode="overlay",
                margin=dict(t=10,b=10,l=0,r=10), paper_bgcolor="white", plot_bgcolor="white",
                xaxis=dict(type="date", showgrid=True, gridcolor="#f1f5f9"),
                yaxis=dict(showgrid=False, autorange="reversed"), font=dict(size=10))
            st.plotly_chart(fig_g, use_container_width=True)

    st.markdown("<div class='sh'>Role Composition per Project</div>", unsafe_allow_html=True)
    piv_src = staff_util[staff_util["current_project"].notna() & (staff_util["current_project"].astype(str).str.strip() != "")]
    if not piv_src.empty:
        piv = piv_src.groupby(["current_project","role"])["name"].count().reset_index()
        pw  = piv.pivot_table(index="current_project", columns="role", values="name", fill_value=0)
        pw["TOTAL"] = pw.sum(axis=1)
        st.dataframe(pw.sort_values("TOTAL", ascending=False), use_container_width=True, height=280)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SCENARIO MODELLER
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("## 🎯 Scenario Modeller")
    st.markdown(
        "Simulate winning one or more pipeline projects — or define a custom role requirement — "
        "and instantly see whether your current bench can cover it, who to assign, and where gaps exist."
    )

    # ── Step 1: pick from pipeline or enter manually
    sc_col1, sc_col2 = st.columns([3, 1])
    with sc_col1:
        scenario_name = st.text_input("Scenario name", "Scenario A", key="sc_name")
    with sc_col2:
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<div class='sh'>Step 1 — Select Pipeline Projects to Win</div>", unsafe_allow_html=True)

    if not pipeline.empty and "name" in pipeline.columns:
        # Show pipeline table for reference
        pipe_ref_cols = [c for c in ["name","client","probability_pct","est_start_date","roles_needed"] if c in pipeline.columns]
        def hl_prob(val):
            if isinstance(val,(int,float)):
                if val >= 80: return "background-color:#dcfce7;color:#166534"
                if val >= 50: return "background-color:#fef9c3;color:#713f12"
                return "background-color:#fef2f2;color:#991b1b"
            return ""
        pipe_styled = pipeline[pipe_ref_cols].rename(columns={
            "name":"Project","client":"Client","probability_pct":"Prob %",
            "est_start_date":"Est Start","roles_needed":"Roles Needed"
        })
        if "Prob %" in pipe_styled.columns:
            st.dataframe(pipe_styled.style.applymap(hl_prob, subset=["Prob %"]),
                use_container_width=True, height=220)
        else:
            st.dataframe(pipe_styled, use_container_width=True, height=220)

        selected_projects = st.multiselect(
            "Select one or more pipeline projects to include in this scenario:",
            options=pipeline["name"].tolist()
        )

        # Pre-fill roles from selected projects
        prefill_roles = {}
        for _, row in pipeline[pipeline["name"].isin(selected_projects)].iterrows():
            for role, count in parse_roles(row.get("roles_needed","")):
                prefill_roles[role] = prefill_roles.get(role, 0) + count
        prefill_str = ", ".join(f"{v}x {k}" for k,v in prefill_roles.items()) if prefill_roles else ""
    else:
        selected_projects = []
        prefill_str = ""
        st.markdown("<div class='ai'>ℹ️ No pipeline CSV loaded — enter roles manually below.</div>", unsafe_allow_html=True)

    st.markdown("<div class='sh'>Step 2 — Define Role Requirements</div>", unsafe_allow_html=True)
    st.caption("Auto-filled from selected pipeline projects. Edit freely, or enter manually. Format: `2x Engineer, 1x Project Manager`")
    roles_input = st.text_area("Roles needed for this scenario", value=prefill_str, height=80,
        placeholder="2x Engineer, 1x Project Manager, 1x Analyst, 1x Project Coordinator",
        key="roles_input")

    if st.button("▶  Run Scenario", type="primary"):
        if not roles_input.strip():
            st.warning("Enter at least one role requirement to run the scenario.")
        else:
            scenario_demand = {}
            for role, count in parse_roles(roles_input):
                scenario_demand[role] = scenario_demand.get(role, 0) + count

            avail_by_role = (
                staff_util[staff_util["assigned"] == False]
                .groupby("role")["name"].count().to_dict()
            )
            total_by_role = staff_util.groupby("role")["name"].count().to_dict()

            results = []
            for role, needed in scenario_demand.items():
                avail   = avail_by_role.get(role, 0)
                total   = total_by_role.get(role, 0)
                gap     = needed - avail
                status  = "✅ Covered" if gap <= 0 else ("⚠️ Partial gap" if gap <= 2 else "🔴 Hire needed")
                results.append({
                    "Role": role, "Needed": needed,
                    "Available (bench)": avail, "Total in Team": total,
                    "Gap": gap, "Status": status
                })
            res_df = pd.DataFrame(results).sort_values("Gap", ascending=False)

            # ── Result KPIs
            st.markdown(f"<div class='sh'>Results — {scenario_name}</div>", unsafe_allow_html=True)
            k1,k2,k3,k4 = st.columns(4)
            covered  = len(res_df[res_df["Gap"] <= 0])
            partial  = len(res_df[(res_df["Gap"]>0)&(res_df["Gap"]<=2)])
            need_hire= len(res_df[res_df["Gap"]>2])
            total_needed = int(res_df["Needed"].sum())
            total_avail  = int(res_df["Available (bench)"].sum())

            kpi(k1, total_needed,  "Total Roles Needed",  "")
            kpi(k2, total_avail,   "Covered from Bench",  "No hire needed" if total_avail >= total_needed else f"{total_needed - total_avail} shortfall", "c-green" if total_avail >= total_needed else "c-amber")
            kpi(k3, partial,       "Partial Gaps",        "Reallocation possible", "c-amber")
            kpi(k4, need_hire,     "Roles Needing Hire",  "Recruitment required" if need_hire else "✓ None", "c-red" if need_hire else "c-green")
            st.markdown("<br>", unsafe_allow_html=True)

            # ── Breakdown table + chart side-by-side
            rc1, rc2 = st.columns([3, 2])
            with rc1:
                st.markdown("<div class='sh'>Role Gap Breakdown</div>", unsafe_allow_html=True)
                def sc_gap_color(val):
                    if isinstance(val,(int,float)):
                        if val > 2:  return "background-color:#fef2f2;color:#991b1b;font-weight:700"
                        if val > 0:  return "background-color:#fef9c3;color:#713f12;font-weight:600"
                        return "background-color:#f0fdf4;color:#166534"
                    return ""
                st.dataframe(
                    res_df.style.applymap(sc_gap_color, subset=["Gap"]),
                    use_container_width=True, height=300
                )
            with rc2:
                st.markdown("<div class='sh'>Available vs Needed</div>", unsafe_allow_html=True)
                fig_sc = go.Figure()
                fig_sc.add_trace(go.Bar(name="Available (bench)",
                    x=res_df["Role"], y=res_df["Available (bench)"],
                    marker_color="#10b981", marker_line_width=0))
                fig_sc.add_trace(go.Bar(name="Needed",
                    x=res_df["Role"], y=res_df["Needed"],
                    marker_color="#3b82f6", opacity=0.75, marker_line_width=0))
                fig_sc.update_layout(
                    barmode="group", height=300, paper_bgcolor="white", plot_bgcolor="white",
                    margin=dict(t=10,b=10,l=0,r=0),
                    legend=dict(orientation="h", y=-0.3),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="#f1f5f9")
                )
                st.plotly_chart(fig_sc, use_container_width=True)

            # ── Staff recommendations
            st.markdown("<div class='sh'>Recommended Staff Assignments</div>", unsafe_allow_html=True)
            st.caption("Best available staff per role, ranked by seniority. Stars indicate top picks.")
            for role, needed in sorted(scenario_demand.items()):
                candidates = staff_util[
                    (staff_util["role"].str.lower() == role.lower()) &
                    (staff_util["assigned"] == False)
                ]
                gap_n = needed - len(candidates)
                st.markdown(f"**{role}** — need {needed} &nbsp;·&nbsp; {len(candidates)} available on bench"
                    + (f" &nbsp;<span style='color:#ef4444;font-weight:600;font-size:.85rem;'>⚠ {gap_n} shortfall — hire needed</span>" if gap_n > 0 else ""),
                    unsafe_allow_html=True)
                if candidates.empty:
                    st.markdown("<div class='ad'>No available staff in this role. Consider hiring or retraining.</div>", unsafe_allow_html=True)
                else:
                    show_n = min(needed + 1, len(candidates))
                    for i, (_, c) in enumerate(candidates.head(show_n).iterrows()):
                        nxt = str(c.get("next_project","")).strip()
                        nxt_html = f" &nbsp;·&nbsp; Next: <em>{nxt}</em>" if nxt and nxt != "nan" else ""
                        star = "⭐ " if i == 0 else ""
                        st.markdown(
                            f"<div class='rc'><h4>{star}{c['name']} &nbsp;<span class='tag tg'>Available</span></h4>"
                            f"<p>{c.get('role','')} · {c.get('role_desc','')}{nxt_html}</p></div>",
                            unsafe_allow_html=True
                        )

            # ── Export
            st.markdown("<br>", unsafe_allow_html=True)
            dl_col, _ = st.columns([1,3])
            dl_col.download_button(
                "⬇ Export Scenario (CSV)",
                res_df.to_csv(index=False),
                f"{scenario_name.replace(' ','_')}_scenario.csv",
                "text/csv"
            )
    else:
        st.markdown("<div class='ai'>ℹ️ Select pipeline projects or enter roles above, then click Run Scenario.</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CAPACITY FORECAST
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("## 📅 Capacity Forecast")
    st.markdown("Month-by-month view of how your available staff changes as current assignments end — and when pipeline demand will absorb that capacity.")

    f1, f2 = st.columns(2)
    horizon  = f1.slider("Forecast horizon (months)", 3, 24, 12)
    min_prob = f2.slider("Include pipeline projects with win probability ≥", 0, 100, 50, step=5)

    months = pd.date_range(start=today_dt, periods=horizon, freq="MS")
    roles_in_data = sorted(staff_util["role"].dropna().unique().tolist())

    fc_rows = []
    for month in months:
        month_end = month + pd.offsets.MonthEnd(0)
        if not allocations.empty and "start_date" in allocations.columns:
            am    = allocations[(allocations["start_date"] <= month_end) & (allocations["end_date"] >= month)]
            busy  = am["staff_id"].nunique() if not am.empty else 0
        else:
            busy = int(assigned_n)
        free = total_staff - busy

        pipe_demand = 0
        if not pipeline.empty and "est_start_date" in pipeline.columns:
            starting = pipeline[
                (pipeline.get("probability_pct", pd.Series(100, index=pipeline.index)) >= min_prob) &
                (pipeline["est_start_date"] >= month) &
                (pipeline["est_start_date"] <= month_end)
            ]
            for _, r in starting.iterrows():
                pipe_demand += sum(c for _,c in parse_roles(r.get("roles_needed","")))

        fc_rows.append({
            "Month": month.strftime("%b %Y"), "Month_dt": month,
            "On Projects": busy, "Available": free,
            "Pipeline Demand": pipe_demand, "Net Capacity": free - pipe_demand,
        })
    fc_df = pd.DataFrame(fc_rows)

    # ── Main forecast chart
    st.markdown("<div class='sh'>Available Capacity vs Pipeline Demand</div>", unsafe_allow_html=True)
    fig_fc = go.Figure()
    fig_fc.add_trace(go.Scatter(
        x=fc_df["Month"], y=fc_df["Available"], mode="lines+markers",
        name="Available Staff", line=dict(color="#10b981", width=2.5),
        fill="tozeroy", fillcolor="rgba(16,185,129,0.07)"
    ))
    fig_fc.add_trace(go.Scatter(
        x=fc_df["Month"], y=fc_df["Pipeline Demand"], mode="lines+markers",
        name=f"Pipeline Demand (≥{min_prob}%)", line=dict(color="#f59e0b", width=2, dash="dot")
    ))
    fig_fc.add_trace(go.Bar(
        x=fc_df["Month"], y=fc_df["Net Capacity"], name="Net Capacity",
        marker_color=["#10b981" if v >= 0 else "#ef4444" for v in fc_df["Net Capacity"]],
        opacity=0.45
    ))
    fig_fc.add_hline(y=0, line_color="#ef4444", line_width=1, opacity=0.3)
    fig_fc.update_layout(
        height=380, paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(t=10,b=10), legend=dict(orientation="h", y=-0.22),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Headcount"),
        barmode="relative"
    )
    st.plotly_chart(fig_fc, use_container_width=True)
    st.dataframe(
        fc_df.drop(columns=["Month_dt"]).rename(columns={
            "On Projects":"On Projects","Available":"Available","Pipeline Demand":"Pipeline Demand",
            "Net Capacity":"Net Capacity (green = surplus)"
        }),
        use_container_width=True, height=220
    )

    # ── Who frees up in next 90 days
    st.markdown("<div class='sh'>Staff Completing Assignments — Next 90 Days</div>", unsafe_allow_html=True)
    d90 = today_dt + pd.Timedelta(days=90)
    if not allocations.empty and "end_date" in allocations.columns:
        ending = allocations[(allocations["end_date"] >= today_dt) & (allocations["end_date"] <= d90)].copy()
        if not ending.empty:
            ending = ending[["staff_id","project_id","end_date"]].drop_duplicates().merge(
                staff_util[["staff_id","name","role","next_project"]].drop_duplicates("staff_id"),
                on="staff_id", how="left"
            ).merge(
                projects[["project_id","name"]].rename(columns={"name":"proj_name"}),
                on="project_id", how="left"
            )
            ending["Days Until Free"] = (ending["end_date"] - today_dt).dt.days
            ending = ending.sort_values("end_date")
            show_e = [c for c in ["name","role","proj_name","end_date","Days Until Free","next_project"] if c in ending.columns]
            st.dataframe(
                ending[show_e].rename(columns={
                    "name":"Staff","role":"Role","proj_name":"Project Ending",
                    "end_date":"End Date","next_project":"Next Project"
                }),
                use_container_width=True, height=300
            )
        else:
            st.markdown("<div class='ai'>No assignments completing in the next 90 days.</div>", unsafe_allow_html=True)

    # ── Role heatmap
    st.markdown("<div class='sh'>Available Headcount by Role — Month by Month</div>", unsafe_allow_html=True)
    st.caption("Green = more available · Red = fewer available. Use this to spot capacity bottlenecks by role.")
    if not allocations.empty and roles_in_data:
        hm_rows = []
        for month in months[:12]:
            month_end = month + pd.offsets.MonthEnd(0)
            am = allocations[(allocations["start_date"] <= month_end) & (allocations["end_date"] >= month)]
            busy_r = {}
            if not am.empty:
                am_slim = am[["staff_id"]].drop_duplicates()
                br = am_slim.merge(staff_util[["staff_id","role"]].drop_duplicates("staff_id"), on="staff_id", how="left")
                busy_r = br.groupby("role")["staff_id"].nunique().to_dict()
            total_r = staff_util.groupby("role")["name"].count().to_dict()
            row_d = {"Month": month.strftime("%b %Y")}
            for r in roles_in_data:
                row_d[r] = max(0, total_r.get(r,0) - busy_r.get(r,0))
            hm_rows.append(row_d)
        hm_df = pd.DataFrame(hm_rows).set_index("Month")
        fig_hm = px.imshow(hm_df.T,
            color_continuous_scale=["#fef2f2","#fef9c3","#dcfce7","#10b981"],
            labels=dict(x="Month", y="Role", color="Available"), aspect="auto")
        fig_hm.update_layout(height=320, margin=dict(t=10,b=10), paper_bgcolor="white")
        st.plotly_chart(fig_hm, use_container_width=True)

    dl2, _ = st.columns([1,4])
    dl2.download_button("⬇ Export Forecast (CSV)", fc_df.drop(columns=["Month_dt"]).to_csv(index=False), "capacity_forecast.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — HIRING PLANNER
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("## 📊 Hiring Planner")
    st.markdown(
        "Understand the **delta between what you have and what you need** — "
        "based on current project demand, pipeline wins, and current assignment rates."
    )

    # ── Current state: role inventory
    st.markdown("<div class='sh'>Current Workforce vs Assignment Rate</div>", unsafe_allow_html=True)
    inv = staff_util.groupby("role").agg(
        total=("name","count"),
        assigned=("assigned","sum"),
    ).reset_index()
    inv["available"]    = inv["total"] - inv["assigned"]
    inv["assign_rate"]  = (inv["assigned"] / inv["total"] * 100).round(1)
    inv["hire_signal"]  = inv["assign_rate"].apply(
        lambda x: "🔴 Strong signal" if x >= 95 else ("🟡 Watch" if x >= 80 else "✅ OK")
    )

    hi1, hi2 = st.columns(2)
    with hi1:
        fig_inv = go.Figure()
        inv_s = inv.sort_values("total", ascending=True)
        fig_inv.add_trace(go.Bar(name="Assigned",  y=inv_s["role"], x=inv_s["assigned"],
            orientation="h", marker_color="#3b82f6", marker_line_width=0))
        fig_inv.add_trace(go.Bar(name="Available", y=inv_s["role"], x=inv_s["available"],
            orientation="h", marker_color="#10b981", marker_line_width=0))
        fig_inv.update_layout(
            barmode="stack", height=320, paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(t=10,b=10,l=0,r=10), legend=dict(orientation="h", y=-0.2),
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Headcount"),
            yaxis=dict(showgrid=False), title="Roster: Assigned vs Available by Role"
        )
        st.plotly_chart(fig_inv, use_container_width=True)

    with hi2:
        st.markdown("<div class='sh'>Role Inventory & Hire Signals</div>", unsafe_allow_html=True)
        st.dataframe(
            inv[["role","total","assigned","available","assign_rate","hire_signal"]].rename(columns={
                "role":"Role","total":"Total","assigned":"Assigned","available":"Available",
                "assign_rate":"Assign %","hire_signal":"Signal"
            }).sort_values("Assign %", ascending=False),
            use_container_width=True, height=320
        )

    # ── Pipeline demand delta
    st.markdown("<div class='sh'>Pipeline-Driven Role Delta — How Many Do You Need to Hire?</div>", unsafe_allow_html=True)
    st.markdown(
        "This table shows the **net gap** between what the pipeline demands and what you currently have available on bench. "
        "A positive gap = you need to hire. Adjust the probability threshold to stress-test different scenarios."
    )

    if not pipeline.empty and "roles_needed" in pipeline.columns:
        hp1, hp2 = st.columns(2)
        min_prob_hire = hp1.slider("Min win probability to include", 0, 100, 60, step=10, key="hire_prob")
        lead_weeks    = hp2.slider("Hiring lead time (weeks)", 4, 24, 8, help="How early you need to start recruiting before project start")

        pipe_f = pipeline[pipeline["probability_pct"] >= min_prob_hire] if "probability_pct" in pipeline.columns else pipeline

        # Aggregate demand from filtered pipeline
        raw_demand, wtd_demand = {}, {}
        for _, row in pipe_f.iterrows():
            prob = row.get("probability_pct", 100) / 100
            for role, count in parse_roles(row.get("roles_needed","")):
                raw_demand[role] = raw_demand.get(role,0) + count
                wtd_demand[role] = wtd_demand.get(role,0) + count * prob

        if raw_demand:
            total_r  = staff_util.groupby("role")["name"].count().to_dict()
            avail_r  = staff_util[staff_util["assigned"]==False].groupby("role")["name"].count().to_dict()

            hire_rows = []
            for role in sorted(raw_demand, key=lambda r: -raw_demand[r]):
                have_total   = total_r.get(role,0)
                have_avail   = avail_r.get(role,0)
                demand_raw   = raw_demand[role]
                demand_wtd   = round(wtd_demand[role],1)
                gap_avail    = demand_raw - have_avail    # vs bench only
                gap_total    = demand_raw - have_total    # vs entire team
                hires_needed = max(0, gap_avail)
                urgency      = "🔴 Urgent" if hires_needed >= 3 else ("🟡 Soon" if hires_needed > 0 else "✅ Covered")
                hire_rows.append({
                    "Role":             role,
                    "Pipeline Demand":  demand_raw,
                    "Weighted Demand":  demand_wtd,
                    "In Team (Total)":  have_total,
                    "On Bench":         have_avail,
                    "Gap vs Bench":     gap_avail,
                    "Hires Needed":     hires_needed,
                    "Urgency":          urgency,
                })
            hire_df = pd.DataFrame(hire_rows)

            hc1, hc2 = st.columns([3, 2])
            with hc1:
                def clr_hire(val):
                    if isinstance(val,(int,float)):
                        if val >= 3: return "background-color:#fef2f2;color:#991b1b;font-weight:700"
                        if val > 0:  return "background-color:#fef9c3;color:#713f12;font-weight:600"
                        return "background-color:#f0fdf4;color:#166534"
                    return ""
                st.dataframe(
                    hire_df.style.applymap(clr_hire, subset=["Gap vs Bench","Hires Needed"]),
                    use_container_width=True, height=360
                )
                total_hires  = int(hire_df["Hires Needed"].sum())
                urgent_roles = len(hire_df[hire_df["Hires Needed"] >= 3])
                cls = "ad" if total_hires > 5 else ("aw" if total_hires > 0 else "ag")
                ico = "🔴" if total_hires > 5 else ("⚠️" if total_hires > 0 else "✅")
                st.markdown(
                    f"<div class='{cls}'>{ico} <b>{total_hires} hires recommended</b> across "
                    f"{urgent_roles} urgent role(s) based on pipeline ≥{min_prob_hire}% probability. "
                    f"Begin recruiting at least {lead_weeks} weeks before estimated project start dates.</div>",
                    unsafe_allow_html=True
                )

            with hc2:
                hn = hire_df[hire_df["Hires Needed"] > 0]
                if not hn.empty:
                    fig_hire = go.Figure()
                    fig_hire.add_trace(go.Bar(
                        x=hn["Hires Needed"], y=hn["Role"], orientation="h",
                        marker_color=["#ef4444" if v >= 3 else "#f59e0b" for v in hn["Hires Needed"]],
                        marker_line_width=0,
                        text=hn["Hires Needed"], textposition="outside"
                    ))
                    fig_hire.update_layout(
                        height=360, paper_bgcolor="white", plot_bgcolor="white",
                        margin=dict(t=10,b=10,l=0,r=40),
                        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Hires Needed"),
                        yaxis=dict(showgrid=False),
                        title="Recommended Hires by Role"
                    )
                    st.plotly_chart(fig_hire, use_container_width=True)
                else:
                    st.markdown("<div class='ag'>✅ No hires needed at this probability threshold.</div>", unsafe_allow_html=True)

            # ── Demand vs capacity waterfall per role
            st.markdown("<div class='sh'>Full Role Delta View — Demand vs Capacity</div>", unsafe_allow_html=True)
            st.caption("Shows pipeline demand against your entire team headcount and available bench — gives the full picture of where gaps exist now vs structurally.")
            all_roles_delta = hire_df.copy()
            fig_delta = go.Figure()
            fig_delta.add_trace(go.Bar(name="In Team (Total)",
                x=all_roles_delta["Role"], y=all_roles_delta["In Team (Total)"],
                marker_color="#bfdbfe", marker_line_width=0))
            fig_delta.add_trace(go.Bar(name="On Bench",
                x=all_roles_delta["Role"], y=all_roles_delta["On Bench"],
                marker_color="#10b981", marker_line_width=0))
            fig_delta.add_trace(go.Scatter(name="Pipeline Demand",
                x=all_roles_delta["Role"], y=all_roles_delta["Pipeline Demand"],
                mode="markers+lines", marker=dict(color="#ef4444", size=10, symbol="diamond"),
                line=dict(color="#ef4444", width=1.5, dash="dot")))
            fig_delta.update_layout(
                barmode="overlay", height=360, paper_bgcolor="white", plot_bgcolor="white",
                margin=dict(t=10,b=10), legend=dict(orientation="h", y=-0.22),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Headcount")
            )
            st.plotly_chart(fig_delta, use_container_width=True)

            dl3, _ = st.columns([1,4])
            dl3.download_button("⬇ Export Hiring Plan (CSV)", hire_df.to_csv(index=False), "hiring_plan.csv", "text/csv")

        else:
            st.markdown("<div class='ai'>ℹ️ No roles found in the filtered pipeline projects.</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            "<div class='ai'>ℹ️ Upload a pipeline CSV to see hiring recommendations. "
            "The pipeline CSV needs a <b>roles_needed</b> column formatted as "
            "<code>2x Engineer, 1x Project Manager</code>.</div>",
            unsafe_allow_html=True
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — ALERTS
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown("## ⚠️ Alerts & Action Items")

    alerts = []

    # Roles at capacity
    for _, row in inv[inv["assign_rate"] >= 95].iterrows():
        alerts.append(("ad", f"🔴 <b>{row['role']}</b> is at <b>{row['assign_rate']:.0f}%</b> assignment rate — only {int(row['available'])} of {int(row['total'])} available."))

    # Staff with no next project and assignment ending within 30 days
    if not allocations.empty and "end_date" in allocations.columns:
        ending30 = allocations[(allocations["end_date"] >= today_dt) & (allocations["end_date"] <= today_dt + pd.Timedelta(days=30))]
        if not ending30.empty:
            e30 = ending30[["staff_id"]].drop_duplicates().merge(staff_util[["staff_id","name","next_project"]].drop_duplicates("staff_id"), on="staff_id", how="left")
            no_nxt = e30[e30["next_project"].isna() | (e30["next_project"].astype(str).str.strip().isin(["","nan"]))]
            if not no_nxt.empty:
                names_30 = ", ".join(no_nxt["name"].head(6).tolist()) + ("..." if len(no_nxt) > 6 else "")
                alerts.append(("aw", f"⏰ <b>{len(no_nxt)} staff</b> finish their assignment within 30 days with no next project: {names_30}"))

    # High bench count
    if available_n > total_staff * 0.20:
        bench_names = ", ".join(staff_util[staff_util["assigned"]==False]["name"].head(8).tolist()) + ("..." if available_n > 8 else "")
        alerts.append(("aw", f"🟡 <b>{available_n} staff ({available_n/total_staff*100:.0f}%)</b> are currently unassigned: {bench_names}"))

    # Pipeline gaps for high-probability pursuits
    if not pipeline.empty and "roles_needed" in pipeline.columns and "probability_pct" in pipeline.columns:
        high_prob = pipeline[pipeline["probability_pct"] >= 75]
        for _, row in high_prob.iterrows():
            for role, count in parse_roles(row.get("roles_needed","")):
                avail_r = staff_util[(staff_util["role"].str.lower()==role.lower()) & (staff_util["assigned"]==False)]
                if len(avail_r) < count:
                    alerts.append(("aw", f"⚠️ Pursuit <b>{row.get('name','')}</b> ({int(row['probability_pct'])}% win) needs <b>{count}x {role}</b> — only <b>{len(avail_r)}</b> on bench."))

    if not alerts:
        st.markdown("<div class='ag'>✅ No critical alerts at this time. All systems healthy.</div>", unsafe_allow_html=True)
    else:
        for cls, msg in alerts:
            st.markdown(f"<div class='{cls}'>{msg}</div>", unsafe_allow_html=True)

    # Summary snapshot
    st.markdown("<br><div class='sh'>Snapshot</div>", unsafe_allow_html=True)
    a1,a2,a3,a4 = st.columns(4)
    kpi(a1, int(assigned_n),  "Assigned",           "On active project", "c-green")
    kpi(a2, int(available_n), "Available",           "On bench", "c-amber" if available_n < 5 else "c-green")
    kpi(a3, int((staff_util["next_project"].notna() & (staff_util["next_project"].astype(str).str.strip().ne(""))).sum()),
        "Have Next Project", "Continuity covered", "c-green")
    kpi(a4, int((staff_util["next_project"].isna() | staff_util["next_project"].astype(str).str.strip().isin(["","nan"])).sum()),
        "No Next Project", "Needs planning", "c-amber")

    st.markdown("<br><div class='sh'>Export</div>", unsafe_allow_html=True)
    exp = staff_util[["name","role","current_project","status_label","assign_end","next_project"]].copy()
    exp.columns = ["Name","Role","Current Project","Status","Assignment End","Next Project"]
    st.download_button("⬇ Download Staff Status Report (CSV)", exp.to_csv(index=False), "staff_status_report.csv", "text/csv")
