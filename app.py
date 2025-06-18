from flask import Flask, render_template, jsonify, request
import pandas as pd
from collections import defaultdict
from sqlalchemy import create_engine, text

# ── PostgreSQL connection ──────────────────────────────────────────────────────
DATABASE_CONFIG = {
    "host":     "52.71.150.231",
    "port":     5433,
    "database": "postgres",
    "user":     "n8n",
    "password": "n8n"
}

engine = create_engine(
    f"postgresql+psycopg2://{DATABASE_CONFIG['user']}:"
    f"{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:"
    f"{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
)

app = Flask(__name__)

# ── CSV parsing & hierarchy builder (unchanged) ────────────────────────────────
def parse_csv_data():
    """Parse file1.csv into two flat lists, then build hierarchies."""
    try:
        with open('file1.csv', 'r', encoding='utf-8') as f:
            lines = f.readlines()

        revenue_rows, expense_rows = [], []
        section = None

        for line in lines:
            parts = [p.strip() for p in line.split(',')]
            if parts and 'Revenue:' in parts[0]:
                section = 'revenue'
                continue
            if parts and 'Expenses:' in parts[0]:
                section = 'expenses'
                continue
            if not parts or parts[0].startswith('tree_node_desc') or not parts[0]:
                continue

            if section == 'revenue' and len(parts) >= 7:
                revenue_rows.append({
                    'tree_node_desc': parts[0],
                    'parent_deptid':  parts[1],
                    'deptid':         parts[2],
                    'fund_code':      parts[3],
                    'account':        parts[4],
                    'total_budget_amt': parts[5],
                    'total_rev_amt':    parts[6],
                })
            elif section == 'expenses' and len(parts) >= 11:
                expense_rows.append({
                    'tree_node_desc':            parts[0],
                    'parent_deptid':             parts[1],
                    'deptid':                    parts[2],
                    'fund_code':                 parts[3],
                    'account':                   parts[4],
                    'total_budget_amt':          parts[5],
                    'total_pre_encumbered_amt':  parts[6],
                    'total_encumbered_amt':      parts[7],
                    'total_expenses':            parts[8],
                    'total_exp_variance':        parts[9],
                    'pct_budget_spent':          parts[10],
                })

        return build_hierarchy(revenue_rows), build_hierarchy(expense_rows)

    except Exception as e:
        print("CSV parse error:", e)
        return [], []

def build_hierarchy(data):
    """Convert flat list (with parent_deptid pointers) into nested tree."""
    items = {item['deptid']: item for item in data if item['deptid']}
    children = defaultdict(list)
    for item in data:
        if item['parent_deptid']:
            children[item['parent_deptid']].append(item)
    def recurse(item, lvl=0):
        item['level'] = lvl
        item['children'] = children.get(item['deptid'], [])
        item['has_children'] = bool(item['children'])
        for c in item['children']:
            recurse(c, lvl+1)
    roots = []
    for item in data:
        if not item['parent_deptid'] or item['parent_deptid'] not in items:
            recurse(item)
            roots.append(item)
    return roots

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    revenue_data, expenses_data = parse_csv_data()
    return render_template('index.html',
                           revenue_data=revenue_data,
                           expenses_data=expenses_data)

@app.route('/api/getdata')
def getdata():
    """
    Drill‐down detail from PostgreSQL.
    Expects: fund_code, account, deptid, ledger_type
    """
    fund   = request.args.get('fund_code', '')
    acct   = request.args.get('account', '')
    deptid = request.args.get('deptid', '')
    ledger = request.args.get('ledger_type', 'ZZ_CHD_EX')

    sql = text("""
      SELECT
        FISCAL_YEAR,
        ACCOUNTING_PERIOD,
        KK_TRAN_ID,
        KK_TRAN_DT,
        KK_TRAN_LN,
        LEDGER_GROUP,
        LEDGER,
        GUID,
        KK_SOURCE_TRAN,
        LEDGER_TYPE_KK,
        VOUCHER_ID,
        VOUCHER_LINE_NUM,
        DISTRIB_LINE_NUM,
        INVOICE_ID,
        VENDOR_ID,
        NAME1,
        TRANS_NBR,
        TRANSACTION_DT,
        TRANSACTION_LN,
        JOURNAL_ID,
        JOURNAL_DATE,
        JOURNAL_LINE,
        LINE_DESCR,
        RUN_DT,
        SEQNUM,
        CHECK_NBR,
        FUND_CODE,
        DEPTID,
        ACCOUNT,
        PROGRAM_CODE,
        PROJECT_ID,
        CHARTFIELD1,
        BUDGET_REF,
        CHARTFIELD2,
        AFFILIATE,
        AFFILIATE_INTRA1,
        ACCOUNTING_DT,
        LINE_AMT,
        BUDGET_PERIOD,
        DTTM_STAMP_SEC,
        DEPTID_DESCR,
        ACCOUNT_DESCR,
        RPTCAT_LVL,
        KK_SRC_TRAN_DESCR
      FROM aiw_kk_dept_sum_det
      WHERE BUDGET_PERIOD LIKE '2025%'
        AND FUND_CODE   = :fund
        AND ACCOUNT     = :acct
        AND DEPTID      = :deptid
        AND LEDGER_TYPE_KK = :ledger
      ORDER BY KK_TRAN_DT, KK_TRAN_ID;
    """)

    df = pd.read_sql(sql, engine,
                     params={"fund": fund,
                             "acct": acct,
                             "deptid": deptid,
                             "ledger": ledger})
    return jsonify(df.to_dict(orient="records"))

if __name__ == '__main__':
    app.run(debug=True)
