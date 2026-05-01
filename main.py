import hashlib
import io
import json
import os
from flask import Flask, request, Response, send_file, render_template_string, redirect, session
from supabase import create_client
from html import escape as html_escape
from datetime import datetime

_original_md5 = hashlib.md5

def safe_md5(*args, **kwargs):
    kwargs.pop("usedforsecurity", None)
    return _original_md5(*args, **kwargs)

hashlib.md5 = safe_md5

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = "any-secret-key"
SUPABASE_URL = os.getenv("supabase_url")
SUPABASE_KEY = os.getenv("supabase_key")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("missing Supabase enviroment variables")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
# 👇 Users من Railway فقط
USERS = {
    "Messawy": os.getenv("APP_PASS_MOHAMED"),
    "Ofayez": os.getenv("APP_PASS_OMAR")
}

def check_auth(username, password):
    return (
        username in USERS
        and USERS[username] is not None
        and USERS[username] == password
    )

def authenticate():
    return Response(
        'Login Required', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

# 🔐 حماية كل الموقع
@app.before_request
def global_auth():
    open_paths = []  # لو عايز تستثني صفحات

    if request.path in open_paths:
        return

    auth = request.authorization

    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

#@app.route('/login', methods=['GET', 'POST'])
#def login():
   #if request.method == 'POST':
      #  email = request.form['email']
      #  password = request.form['password']

      #  try:
          #  user = supabase.auth.sign_in_with_password({
              # "email": email,
            #    "password": password
         #   })
          #  session['user'] = email
          #  return redirect("/")
      #  except Exception as e:
       #     return f"Login failed ❌: {str(e)}"

  #  return '''
   # <form method="post">
     #   Email: <input name="email"><br>
      #  Password: <input name="password" type="password"><br>
     #   <button type="submit">Login</button>
  #  </form>
  #  '''

MR_FILE = "mr_data.json"
CUSTOMERS_FILE = "customers.json"
INVOICES_FILE = "invoices.json"
BANKS_FILE = "banks.json"

DEFAULT_MR = {
    "2.05": {
        "molar_ratio": "2.05",
        "sodium_oxide": "32.78%",
        "silicon_oxide": "67.21%",
        "total_solid": "99.99",
        "characters": "Coarse Lumps",
        "color": "Light Blue"
    },
    "2.3": {
        "molar_ratio": "2.3",
        "sodium_oxide": "30%",
        "silicon_oxide": "69%",
        "total_solid": "99%",
        "characters": "Coarse Lumps",
        "color": "White"
    },
    "3": {
        "molar_ratio": "3",
        "sodium_oxide": "25%",
        "silicon_oxide": "75%",
        "total_solid": "100%",
        "characters": "Coarse Lumps",
        "color": "White"
    }
}

def load_json_file(filename, default):
    if not os.path.exists(filename):
        save_json_file(filename, default)
        return default
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, type(default)) else default
    except:
        return default

def save_json_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def make_customer_key(name):
    name = (name or "").strip()
    if not name:
        return ""
    return name.lower().replace(" ", "_")

def load_customers():
    try:
        res = supabase.table("customers").select("*").execute()
        customers = {}
        for c in res.data:
            key = make_customer_key(c.get("name", ""))
            customers[key] = {
                "key":key,
                "name": c.get("name", ""),
                "address": c.get("address", ""),
                "phone": c.get("phone", ""),
                "fax": c.get("fax", ""),
                "email": c.get("email", "")
            }
        return customers
    except Exception as e:
        print("LOAD CUSTOMERS ERROR:", e)
        return {}

def save_customers(customers):
    pass

def save_customer_from_form(form):
    name = form.get("name", "").strip()
    if not name:
        return

    data = {
        "name": name,
        "address": form.get("address", ""),
        "phone": form.get("phone", ""),
        "fax": form.get("fax", ""),
        "email": form.get("email", "")
    }
    try:
        existing = supabase.table("customers").select("*").eq("name", data["name"]).execute()
        if existing.data:
            supabase.table("customers").update(data).eq("name", data["name"]).execute()
        else:
            supabase.table("customers").insert(data).execute()
    except Exception as e:
        print("SAVE CUSTOMER ERROR:", e)  

def make_bank_key(name):
    name = (name or "").strip()
    if not name:
        return ""
    return name.lower().replace(" ", "_")

def load_banks():
    try:
        res = supabase.table("banks").select("*").execute()
        banks = {}
        for b in res.data:
            key = make_bank_key(b.get("name", ""))
            banks[key] = {
                "key":key,
                "name": b.get("name", ""),
                "account": b.get("account", ""),
                "iban": b.get("iban", ""),
                "swift": b.get("swift", ""),
                "address": b.get("address", "")
            }
        return banks
    except Exception as e:
        print("LOAD BANKS ERROR:", e)
        return {}
def save_banks(banks):
    pass

def save_bank_from_form(form):
    name = form.get("bank_name", "").strip()
    if not name:
        return

    data = {
        "name": name,
        "account": form.get("account", ""),
        "iban": form.get("iban", ""),
        "swift": form.get("swift", ""),
        "address": form.get("bank_address", "")
    }
    try:
        existing = supabase.table("banks").select("*").eq("name", data["name"]).execute()
        if existing.data:
            supabase.table("banks").update(data).eq("name", data["name"]).execute()
        else:
            supabase.table("banks").insert(data).execute()
    except Exception as e:
        print("SAVE BANK ERROR:", e)



def load_invoices():
    try:
        res = supabase.table("invoices").select("*").order("id", desc=True).execute()
        return res.data if res.data else []
    except Exception as e:
        print("LOAD INVOICES ERROR:", e)
        return []

def form_to_saved_data(form):
    saved = {}
    for key, values in form.lists():
        saved[key] = list(values)
    return saved

def saved_get(saved, key, default=""):
    value = saved.get(key, default)
    if isinstance(value, list):
        return value[0] if value else default
    return value

def saved_list(saved, key):
    value = saved.get(key, [])
    if isinstance(value, list):
        return value
    return [value] if value else []

def save_invoice_from_form(form):
    common = get_common_data(form)

    data = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "proforma_no": form.get("proforma_no", ""),
        "commercial_no": form.get("commercial_no", ""),
        "date": form.get("date", ""),
        "po": form.get("po", ""),
        "customer": form.get("name", ""),
        "selected_mr": form.get("selected_mr", ""),
        "products": common["products"],
        "grand_total": common["grand_total"],
        "gross_weight": common["gross_weight"],
        "form_data": form_to_saved_data(form)
    }

    try:
        supabase.table("invoices").insert(data).execute()
    except Exception as e:
        print("SAVE INVOICE ERROR:", e)    


def load_mr_data():
    try:
        res = supabase.table("mr_data").select("*").execute()
        rows = res.data or []

        data = {}
        for row in rows:
            key = row.get("mr_code")
            data[key] = {
                "molar_ratio": row.get("molar_ratio", ""),
                "sodium_oxide": row.get("sodium_oxide", ""),
                "silicon_oxide": row.get("silicon_oxide", ""),
                "total_solid": row.get("total_solid", ""),
                "characters": row.get("characters", ""),
                "color": row.get("color", "")
            }

        return data

    except Exception as e:
        print("LOAD MR ERROR:", e)
        return {}

def save_mr_data(data):
    try:
        # نمسح القديم
        supabase.table("mr_data").delete().neq("mr_code", "").execute()

        # نضيف الجديد
        for key, val in data.items():
            supabase.table("mr_data").insert({
                "mr_code": key,
                "molar_ratio": val.get("molar_ratio", ""),
                "sodium_oxide": val.get("sodium_oxide", ""),
                "silicon_oxide": val.get("silicon_oxide", ""),
                "total_solid": val.get("total_solid", ""),
                "characters": val.get("characters", ""),
                "color": val.get("color", "")
            }).execute()

    except Exception as e:
        print("SAVE MR ERROR:", e)

def to_float(v):
    try:
        return float(v)
    except:
        return 0.0

def add_3_years(date_text):
    if not date_text:
        return ""
    try:
        d = datetime.strptime(date_text, "%Y-%m-%d")
        return d.replace(year=d.year + 3).strftime("%Y-%m-%d")
    except:
        return ""

def draw_wrapped(c, x, y, text, max_chars=60, line_height=12):
    text = text or ""
    lines = [text[i:i+max_chars] for i in range(0, len(text), max_chars)] or [""]
    for i, line in enumerate(lines):
        c.drawString(x, y - (i * line_height), line)
    return y - ((len(lines) - 1) * line_height)

def build_hidden_fields(form):
    parts = []
    for key, values in form.lists():
        for value in values:
            parts.append(
                f'<input type="hidden" name="{html_escape(key)}" value="{html_escape(value)}">'
            )
    return "\n".join(parts)

def base_page(c):
    w, h = A4

    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bg_path = os.path.join(base_dir, "bg.png")

    try:
        if os.path.exists(bg_path):
            c.drawImage(bg_path, 0, 0, width=w, height=h)
        else:
            print("BG NOT FOUND:", bg_path)
    except Exception as e:
        print("BG ERROR:", e)

    return w, h

def get_products(form):
    names = form.getlist("product_name")
    qtys = form.getlist("product_qty")
    prices = form.getlist("product_price")

    products = []
    for name, qty, price in zip(names, qtys, prices):
        name = (name or "").strip()
        qty_f = to_float(qty)
        price_f = to_float(price)

        if name and qty_f > 0:
            products.append({
                "name": name,
                "qty": qty_f,
                "price": price_f,
                "total": qty_f * price_f
            })

    return products

def get_common_data(form):
    products = get_products(form)
    products_total = sum(p["total"] for p in products)
    goods_weight = sum(p["qty"] for p in products)

    palletization = form.get("palletization", "no")
    pallet_qty = to_float(form.get("pallet_qty"))
    pallet_price = to_float(form.get("pallet_price"))
    show_pallets = palletization == "yes" and pallet_qty > 0
    pallet_total = pallet_qty * pallet_price if show_pallets else 0

    bags_count = to_float(form.get("bags_count"))
    bag_weight_unit = to_float(form.get("bag_weight_unit")) or 0.003
    pallet_weight_unit = to_float(form.get("pallet_weight_unit")) or 0.05

    bags_weight_total = bags_count * bag_weight_unit
    pallets_weight_total = pallet_qty * pallet_weight_unit if show_pallets else 0
    gross_weight = goods_weight + bags_weight_total + pallets_weight_total

    packing_weight = form.get("packing_weight", "1.35")
    packing_text = f"{packing_weight} MT / JUMBO BAGS ON PALLETS" if show_pallets else f"{packing_weight} MT / JUMBO BAGS"

    return {
        "products": products,
        "goods_weight": round(goods_weight, 3),
        "show_pallets": show_pallets,
        "pallet_qty": round(pallet_qty, 2),
        "pallet_price": round(pallet_price, 2),
        "pallet_total": round(pallet_total, 2),
        "bags_count": round(bags_count, 2),
        "bags_weight_total": round(bags_weight_total, 3),
        "pallets_weight_total": round(pallets_weight_total, 3),
        "gross_weight": round(gross_weight, 3),
        "packing_text": packing_text,
        "grand_total": round(products_total + pallet_total, 2),
        "expiry_text": add_3_years(form.get("date", ""))
    }

FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Export Documents</title>
<style>
body { font-family: Arial, sans-serif; margin: 24px; line-height: 1.5; }
input, select { margin: 4px 0 10px 0; padding: 6px; width: 280px; }
button { padding: 8px 14px; margin-top: 8px; }
.products input { width: 180px; }
.product-line { margin-bottom: 6px; }
.box { border:1px solid #ddd; padding:15px; margin:15px 0; width: 720px; }
</style>
</head>
<body>

<h2>Export Documents</h2>

<form method="post" action="/generate">

<div class="box">
<h3>Invoice</h3>
Proforma No:<br><input name="proforma_no"><br>
Commercial No:<br><input name="commercial_no"><br>
Date:<br><input type="date" name="date"><br>
PO Number:<br><input name="po"><br>

Delivery Terms:<br>
<select name="delivery_terms">
<option value="">Select Delivery Term</option>
<option value="EXW">EXW</option>
<option value="FOB">FOB</option>
<option value="CFR">CFR</option>
<option value="CIF">CIF</option>
<option value="DAP">DAP</option>
<option value="DDP">DDP</option>
</select><br>
</div>

<div class="box">
<h3>Customer</h3>

Saved Customer:<br>
<select id="saved_customer" onchange="fillCustomer()">
<option value="">Select saved customer</option>
{% for key, customer in customers.items() %}
<option value="{{ key }}">{{ customer.name }}</option>
{% endfor %}
</select><br>

Name:<br><input id="customer_name" name="name"><br>
Address:<br><input id="customer_address" name="address"><br>
Phone:<br><input id="customer_phone" name="phone"><br>
Fax:<br><input id="customer_fax" name="fax"><br>
Email:<br><input id="customer_email" name="email"><br>
<small>Customer data will be saved/updated automatically when you click Generate.</small>
</div>

<div class="box">
<h3>Products</h3>
<div id="products" class="products">
<div class="product-line">
<input name="product_name" placeholder="Product Name">
<input name="product_qty" placeholder="Qty MT">
<input name="product_price" placeholder="Price">
</div>
</div>
<button type="button" onclick="addProduct()">+ Add Product</button>
</div>

<div class="box">
<h3>Pallets</h3>
Palletization:<br>
<select name="palletization">
<option value="no">No</option>
<option value="yes">Yes</option>
</select><br>
Wooden Pallets Qty:<br><input name="pallet_qty"><br>
Wooden Pallets Price:<br><input name="pallet_price"><br>
</div>

<div class="box">
<h3>Packing Data</h3>
Packing Weight Text Value:<br><input name="packing_weight" value="1.35"><br>
Jumbo Bags Count:<br><input name="bags_count"><br>
Weight Per Jumbo Bag (MT):<br><input name="bag_weight_unit" value="0.003"><br>
Weight Per Pallet (MT):<br><input name="pallet_weight_unit" value="0.05"><br>
</div>

<div class="box">
<h3>COA Data</h3>
MR:<br>
<select name="selected_mr">
{% for mr in mr_data.keys() %}
<option value="{{ mr }}">{{ mr }}</option>
{% endfor %}
</select><br>

Lot Number:<br><input name="lot_number"><br>
</div>

<div class="box">
<h3>Payment</h3>
<select name="payment">
<option>BY 100% ADVANCE T/T</option>
<option>LC AT SIGHT</option>
<option>30% ADVANCE / 70% AGAINST DOCS</option>
</select>
</div>

<div class="box">
<h3>Bank</h3>

Saved Bank:<br>
<select id="saved_bank" onchange="fillBank()">
<option value="">Select saved bank</option>
{% for key, bank in banks.items() %}
<option value="{{ key }}">{{ bank.name }}</option>
{% endfor %}
</select><br>

Bank Name:<br><input id="bank_name" name="bank_name"><br>
Account No:<br><input id="bank_account" name="account"><br>
IBAN No:<br><input id="bank_iban" name="iban"><br>
SWIFT Code:<br><input id="bank_swift" name="swift"><br>
Bank Address:<br><input id="bank_address" name="bank_address"><br>
<small>Bank data will be saved/updated automatically when you click Generate.</small>
</div>

<div class="box">
<h3>Origin</h3>
Goods Origin:<br><input name="goods_origin" value="Egypt"><br>
Supplier Origin:<br><input name="supplier_origin" value="Egypt"><br>
HS Code:<br><input name="hs"><br>
</div>

<button type="submit">Generate</button>
</form>

<br>
<a href="/mr">Manage MR Data</a> | <a href="/history">Invoice History</a> | <a href="/customers">Manage Customers</a> | <a href="/banks">Manage Banks</a>

<script>
const savedCustomers = {{ customers|tojson }};
const savedBanks = {{ banks|tojson }};

function fillCustomer() {
    const key = document.getElementById("saved_customer").value;
    if (!key || !savedCustomers[key]) return;

    const c = savedCustomers[key];
    document.getElementById("customer_name").value = c.name || "";
    document.getElementById("customer_address").value = c.address || "";
    document.getElementById("customer_phone").value = c.phone || "";
    document.getElementById("customer_fax").value = c.fax || "";
    document.getElementById("customer_email").value = c.email || "";
}

function fillBank() {
    const key = document.getElementById("saved_bank").value;
    if (!key || !savedBanks[key]) return;

    const b = savedBanks[key];
    document.getElementById("bank_name").value = b.name || "";
    document.getElementById("bank_account").value = b.account || "";
    document.getElementById("bank_iban").value = b.iban || "";
    document.getElementById("bank_swift").value = b.swift || "";
    document.getElementById("bank_address").value = b.address || "";
}

function addProduct() {
    const div = document.createElement("div");
    div.className = "product-line";
    div.innerHTML = `
        <input name="product_name" placeholder="Product Name">
        <input name="product_qty" placeholder="Qty MT">
        <input name="product_price" placeholder="Price">
    `;
    document.getElementById("products").appendChild(div);
}
</script>

</body>
</html>
"""

RESULT_HTML = """
<!DOCTYPE html>
<html>
<body>
<h2>Done</h2>

<form method="post" action="/proforma">
{{ hidden_fields|safe }}
<button>Download Proforma</button>
</form><br>

<form method="post" action="/commercial">
{{ hidden_fields|safe }}
<button>Download Commercial</button>
</form><br>

<form method="post" action="/packing">
{{ hidden_fields|safe }}
<button>Download Packing List</button>
</form><br>

<form method="post" action="/coa">
{{ hidden_fields|safe }}
<button>Download COA</button>
</form><br>

<a href="/">Back</a> | <a href="/history">Invoice History</a>
</body>
</html>
"""

MR_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>MR Management</title>
<style>
body { font-family: Arial; margin: 30px; }
input, select { width: 300px; padding: 6px; margin: 5px 0 12px; }
button { padding: 8px 14px; margin-right: 6px; }
.box { border: 1px solid #ccc; padding: 15px; width: 420px; margin-bottom: 20px; }
</style>
</head>
<body>

<h2>MR Management</h2>
<a href="/">Back to Documents</a><br><br>

<div class="box">
<form method="post" action="/mr/show">
Select MR:<br>
<select name="selected_mr">
{% for mr in mr_data.keys() %}
<option value="{{ mr }}">{{ mr }}</option>
{% endfor %}
</select><br>
<button>Show MR Data</button>
</form>
</div>

<div class="box">
<h3>Add New MR</h3>
<form method="post" action="/mr/add">
MR Name:<br><input name="mr_name"><br>
Molar Ratio:<br><input name="molar_ratio"><br>
Sodium Oxide:<br><input name="sodium_oxide"><br>
Silicon Oxide:<br><input name="silicon_oxide"><br>
Total Solid:<br><input name="total_solid"><br>
Characters:<br><input name="characters"><br>
Color:<br><input name="color"><br>
<button>Save</button>
</form>
</div>

{% if selected %}
<div class="box">
<h3>MR Details</h3>
<p><b>MR:</b> {{ selected }}</p>
<p><b>Molar Ratio:</b> {{ details.molar_ratio }}</p>
<p><b>Sodium Oxide:</b> {{ details.sodium_oxide }}</p>
<p><b>Silicon Oxide:</b> {{ details.silicon_oxide }}</p>
<p><b>Total Solid:</b> {{ details.total_solid }}</p>
<p><b>Characters:</b> {{ details.characters }}</p>
<p><b>Color:</b> {{ details.color }}</p>

<form method="get" action="/mr/edit/{{ selected }}">
<button>Edit</button>
</form>

<form method="post" action="/mr/delete/{{ selected }}" onsubmit="return confirm('Delete this MR?');">
<button>Delete</button>
</form>
</div>
{% endif %}

</body>
</html>
"""

EDIT_MR_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Edit MR</title>
<style>
body { font-family: Arial; margin: 30px; }
input { width: 300px; padding: 6px; margin: 5px 0 12px; }
button { padding: 8px 14px; }
</style>
</head>
<body>

<h2>Edit MR: {{ mr_name }}</h2>

<form method="post" action="/mr/update/{{ mr_name }}">
Molar Ratio:<br><input name="molar_ratio" value="{{ details.molar_ratio }}"><br>
Sodium Oxide:<br><input name="sodium_oxide" value="{{ details.sodium_oxide }}"><br>
Silicon Oxide:<br><input name="silicon_oxide" value="{{ details.silicon_oxide }}"><br>
Total Solid:<br><input name="total_solid" value="{{ details.total_solid }}"><br>
Characters:<br><input name="characters" value="{{ details.characters }}"><br>
Color:<br><input name="color" value="{{ details.color }}"><br>
<button>Update</button>
</form>

<br>
<a href="/mr">Back</a>

</body>
</html>
"""

HISTORY_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Invoice History</title>
<style>
body { font-family: Arial; margin: 30px; }
input { padding: 7px; width: 360px; margin-bottom: 15px; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 8px; font-size: 13px; }
th { background: #f3f3f3; }
</style>
</head>
<body>

<h2>Invoice History</h2>
<a href="/">Back to Documents</a><br><br>

<input id="search" placeholder="Search by customer, proforma, commercial, or PO" onkeyup="filterTable()">

<table id="history_table">
<thead>
<tr>
<th>Date Saved</th>
<th>Customer</th>
<th>Proforma No</th>
<th>Commercial No</th>
<th>Date</th>
<th>PO</th>
<th>MR</th>
<th>Products</th>
<th>Total</th>
<th>Gross Weight</th>
<th>Status</th>
<th>Dashboard</th>
<th>Download</th>
<th>Edit</th>
<th>Delete</th>
</tr>
</thead>
<tbody>
{% for idx, inv in invoice_items %}
<tr>
<td>{{ inv.created_at }}</td>
<td>{{ inv.customer }}</td>
<td>{{ inv.proforma_no }}</td>
<td>{{ inv.commercial_no }}</td>
<td>{{ inv.date }}</td>
<td>{{ inv.po }}</td>
<td>{{ inv.selected_mr }}</td>
<td>
{% for p in inv.products %}
{{ p.name }} ({{ p.qty }} MT)<br>
{% endfor %}
</td>
<td>{{ inv.grand_total }}</td>
<td>{{ inv.gross_weight }}</td>
<!-- Status -->
<td>
    <a href="/status/{{ idx }}">
        {% if inv.get("status_booking_date") or inv.get("status_payment") or inv.get("status_bl_co") %}
            Edit Status
        {% else %}
            Add Status
        {% endif %}
    </a>
</td>

<!-- Dashboard -->
<td>
    <a href="/dashboard/{{ idx }}">Dashboard</a>
</td>

<!-- Download -->
<td>
    <form method="post" action="/invoice/download/{{ idx }}/proforma" style="display:inline;">
        <button type="submit">Proforma</button>
    </form>

    {% if inv.get("is_complete") %}
        <form method="post" action="/invoice/download/{{ idx }}/commercial" style="display:inline;">
            <button type="submit">Commercial</button>
        </form>

        <form method="post" action="/invoice/download/{{ idx }}/packing" style="display:inline;">
            <button type="submit">Packing</button>
        </form>

        <form method="post" action="/invoice/download/{{ idx }}/coa" style="display:inline;">
            <button type="submit">COA</button>
        </form>
    {% else %}
        <button disabled>Commercial</button>
        <button disabled>Packing</button>
        <button disabled>COA</button>
    {% endif %}
</td>

<!-- Edit -->
<td>
    <a href="/invoice/edit/{{ idx }}">Edit</a>
</td>

<!-- Delete -->
<td>
    <form method="post" action="/invoice/delete/{{ inv.id }}">
        <button type="submit">Delete</button>
    </form>
</td>
</tr>
{% endfor %}
</tbody>
</table>

<script>
function filterTable() {
    const value = document.getElementById("search").value.toLowerCase();
    const rows = document.querySelectorAll("#history_table tbody tr");
    rows.forEach(row => {
        row.style.display = row.innerText.toLowerCase().includes(value) ? "" : "none";
    });
}
</script>

</body>
</html>
"""

EDIT_INVOICE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Edit Invoice</title>
<style>
body { font-family: Arial, sans-serif; margin: 24px; line-height: 1.5; }
input, select { margin: 4px 0 10px 0; padding: 6px; width: 280px; }
button { padding: 8px 14px; margin-top: 8px; }
.products input { width: 180px; }
.product-line { margin-bottom: 6px; }
.box { border:1px solid #ddd; padding:15px; margin:15px 0; width: 720px; }
.notice { background:#fff7d6; border:1px solid #e0c56b; padding:10px; width:720px; }
</style>
</head>
<body>

<h2>Edit Invoice</h2>
<div class="notice">
This will create a new updated copy when you click Generate. The old invoice will stay in history.
</div>

<form method="post" action="/generate">

<div class="box">
<h3>Invoice</h3>
Proforma No:<br><input name="proforma_no" value="{{ g('proforma_no') }}"><br>
Commercial No:<br><input name="commercial_no" value="{{ g('commercial_no') }}"><br>
Date:<br><input type="date" name="date" value="{{ g('date') }}"><br>
PO Number:<br><input name="po" value="{{ g('po') }}"><br>

Delivery Terms:<br>
<select name="delivery_terms">
<option value="">Select Delivery Term</option>
{% for term in ["EXW","FOB","CFR","CIF","DAP","DDP"] %}
<option value="{{ term }}" {% if g('delivery_terms') == term %}selected{% endif %}>{{ term }}</option>
{% endfor %}
</select><br>
</div>

<div class="box">
<h3>Customer</h3>

Saved Customer:<br>
<select id="saved_customer" onchange="fillCustomer()">
<option value="">Select saved customer</option>
{% for key, customer in customers.items() %}
<option value="{{ key }}">{{ customer.name }}</option>
{% endfor %}
</select><br>

Name:<br><input id="customer_name" name="name" value="{{ g('name') }}"><br>
Address:<br><input id="customer_address" name="address" value="{{ g('address') }}"><br>
Phone:<br><input id="customer_phone" name="phone" value="{{ g('phone') }}"><br>
Fax:<br><input id="customer_fax" name="fax" value="{{ g('fax') }}"><br>
Email:<br><input id="customer_email" name="email" value="{{ g('email') }}"><br>
</div>

<div class="box">
<h3>Products</h3>
<div id="products" class="products">
{% for p in products %}
<div class="product-line">
<input name="product_name" placeholder="Product Name" value="{{ p.name }}">
<input name="product_qty" placeholder="Qty MT" value="{{ p.qty }}">
<input name="product_price" placeholder="Price" value="{{ p.price }}">
</div>
{% endfor %}
{% if products|length == 0 %}
<div class="product-line">
<input name="product_name" placeholder="Product Name">
<input name="product_qty" placeholder="Qty MT">
<input name="product_price" placeholder="Price">
</div>
{% endif %}
</div>
<button type="button" onclick="addProduct()">+ Add Product</button>
</div>

<div class="box">
<h3>Pallets</h3>
Palletization:<br>
<select name="palletization">
<option value="no" {% if g('palletization','no') == 'no' %}selected{% endif %}>No</option>
<option value="yes" {% if g('palletization') == 'yes' %}selected{% endif %}>Yes</option>
</select><br>
Wooden Pallets Qty:<br><input name="pallet_qty" value="{{ g('pallet_qty') }}"><br>
Wooden Pallets Price:<br><input name="pallet_price" value="{{ g('pallet_price') }}"><br>
</div>

<div class="box">
<h3>Packing Data</h3>
Packing Weight Text Value:<br><input name="packing_weight" value="{{ g('packing_weight','1.35') }}"><br>
Jumbo Bags Count:<br><input name="bags_count" value="{{ g('bags_count') }}"><br>
Weight Per Jumbo Bag (MT):<br><input name="bag_weight_unit" value="{{ g('bag_weight_unit','0.003') }}"><br>
Weight Per Pallet (MT):<br><input name="pallet_weight_unit" value="{{ g('pallet_weight_unit','0.05') }}"><br>
</div>

<div class="box">
<h3>COA Data</h3>
MR:<br>
<select name="selected_mr">
{% for mr in mr_data.keys() %}
<option value="{{ mr }}" {% if g('selected_mr') == mr %}selected{% endif %}>{{ mr }}</option>
{% endfor %}
</select><br>

Lot Number:<br><input name="lot_number" value="{{ g('lot_number') }}"><br>
</div>

<div class="box">
<h3>Payment</h3>
<select name="payment">
{% for pay in ["BY 100% ADVANCE T/T","LC AT SIGHT","30% ADVANCE / 70% AGAINST DOCS"] %}
<option {% if g('payment') == pay %}selected{% endif %}>{{ pay }}</option>
{% endfor %}
</select>
</div>

<div class="box">
<h3>Bank</h3>

Saved Bank:<br>
<select id="saved_bank" onchange="fillBank()">
<option value="">Select saved bank</option>
{% for key, bank in banks.items() %}
<option value="{{ key }}">{{ bank.name }}</option>
{% endfor %}
</select><br>

Bank Name:<br><input id="bank_name" name="bank_name" value="{{ g('bank_name') }}"><br>
Account No:<br><input id="bank_account" name="account" value="{{ g('account') }}"><br>
IBAN No:<br><input id="bank_iban" name="iban" value="{{ g('iban') }}"><br>
SWIFT Code:<br><input id="bank_swift" name="swift" value="{{ g('swift') }}"><br>
Bank Address:<br><input id="bank_address" name="bank_address" value="{{ g('bank_address') }}"><br>
</div>

<div class="box">
<h3>Origin</h3>
Goods Origin:<br><input name="goods_origin" value="{{ g('goods_origin','Egypt') }}"><br>
Supplier Origin:<br><input name="supplier_origin" value="{{ g('supplier_origin','Egypt') }}"><br>
HS Code:<br><input name="hs" value="{{ g('hs') }}"><br>
</div>

<button type="submit" formaction="/invoice/update/{{ invoice_id }}">
Update Same Invoice
</button>

<button type="submit" formaction="/generate">
Save as New Invoice
</button>
</form>

<br>
<a href="/history">Back to History</a> | <a href="/">Back to Documents</a>

<script>
const savedCustomers = {{ customers|tojson }};
const savedBanks = {{ banks|tojson }};

function fillCustomer() {
    const key = document.getElementById("saved_customer").value;
    if (!key || !savedCustomers[key]) return;

    const c = savedCustomers[key];
    document.getElementById("customer_name").value = c.name || "";
    document.getElementById("customer_address").value = c.address || "";
    document.getElementById("customer_phone").value = c.phone || "";
    document.getElementById("customer_fax").value = c.fax || "";
    document.getElementById("customer_email").value = c.email || "";
}

function fillBank() {
    const key = document.getElementById("saved_bank").value;
    if (!key || !savedBanks[key]) return;

    const b = savedBanks[key];
    document.getElementById("bank_name").value = b.name || "";
    document.getElementById("bank_account").value = b.account || "";
    document.getElementById("bank_iban").value = b.iban || "";
    document.getElementById("bank_swift").value = b.swift || "";
    document.getElementById("bank_address").value = b.address || "";
}

function addProduct() {
    const div = document.createElement("div");
    div.className = "product-line";
    div.innerHTML = `
        <input name="product_name" placeholder="Product Name">
        <input name="product_qty" placeholder="Qty MT">
        <input name="product_price" placeholder="Price">
    `;
    document.getElementById("products").appendChild(div);
}
</script>

</body>
</html>
"""


CUSTOMERS_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Customer Management</title>
<style>
body { font-family: Arial; margin: 30px; }
input { width: 360px; padding: 6px; margin: 5px 0 12px; }
button { padding: 8px 14px; margin-right: 6px; }
table { border-collapse: collapse; width: 100%; margin-top: 15px; }
th, td { border: 1px solid #ddd; padding: 8px; font-size: 13px; }
th { background: #f3f3f3; }
.box { border:1px solid #ddd; padding:15px; width:450px; margin-bottom:20px; }
</style>
</head>
<body>

<h2>Customer Management</h2>
<a href="/">Back to Documents</a><br><br>

<div class="box">
<h3>Add / Update Customer</h3>
<form method="post" action="/customers/save">
Name:<br><input name="name"><br>
Address:<br><input name="address"><br>
Phone:<br><input name="phone"><br>
Fax:<br><input name="fax"><br>
Email:<br><input name="email"><br>
<button type="submit">Save Customer</button>
</form>
</div>

<table>
<thead>
<tr>
<th>Name</th>
<th>Address</th>
<th>Phone</th>
<th>Fax</th>
<th>Email</th>
<th>Edit</th>
<th>Delete</th>
</tr>
</thead>
<tbody>
{% for key, customer in customers.items() %}
<tr>
<td>{{ customer.name }}</td>
<td>{{ customer.address }}</td>
<td>{{ customer.phone }}</td>
<td>{{ customer.fax }}</td>
<td>{{ customer.email }}</td>
<td><a href="/customers/edit/{{ customer.key }}">Edit</a></td>
<td>
<form method="post" action="/customers/delete/{{ key }}" onsubmit="return confirm('Delete this customer?');">
<button type="submit">Delete</button>
</form>
</td>
</tr>
{% endfor %}
</tbody>
</table>

</body>
</html>
"""

EDIT_CUSTOMER_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Edit Customer</title>
<style>
body { font-family: Arial; margin: 30px; }
input { width: 360px; padding: 6px; margin: 5px 0 12px; }
button { padding: 8px 14px; }
.box { border:1px solid #ddd; padding:15px; width:450px; }
</style>
</head>
<body>

<h2>Edit Customer</h2>

<div class="box">
<form method="post" action="/customers/update/{{ customer.key }}">
Name:<br><input name="name" value="{{ customer.name }}"><br>
Address:<br><input name="address" value="{{ customer.address }}"><br>
Phone:<br><input name="phone" value="{{ customer.phone }}"><br>
Fax:<br><input name="fax" value="{{ customer.fax }}"><br>
Email:<br><input name="email" value="{{ customer.email }}"><br>
<button type="submit">Update Customer</button>
</form>
</div>

<br>
<a href="/customers">Back to Customers</a> | <a href="/">Back to Documents</a>

</body>
</html>
"""

BANKS_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Bank Management</title>
<style>
body { font-family: Arial; margin: 30px; }
input { width: 420px; padding: 6px; margin: 5px 0 12px; }
button { padding: 8px 14px; margin-right: 6px; }
table { border-collapse: collapse; width: 100%; margin-top: 15px; }
th, td { border: 1px solid #ddd; padding: 8px; font-size: 13px; }
th { background: #f3f3f3; }
.box { border:1px solid #ddd; padding:15px; width:500px; margin-bottom:20px; }
</style>
</head>
<body>

<h2>Bank Management</h2>
<a href="/">Back to Documents</a><br><br>

<div class="box">
<h3>Add / Update Bank</h3>
<form method="post" action="/banks/save">
Bank Name:<br><input name="bank_name"><br>
Account No:<br><input name="account"><br>
IBAN No:<br><input name="iban"><br>
SWIFT Code:<br><input name="swift"><br>
Bank Address:<br><input name="bank_address"><br>
<button type="submit">Save Bank</button>
</form>
</div>

<table>
<thead>
<tr>
<th>Bank Name</th>
<th>Account</th>
<th>IBAN</th>
<th>SWIFT</th>
<th>Address</th>
<th>Edit</th>
<th>Delete</th>
</tr>
</thead>
<tbody>
{% for key, bank in banks.items() %}
<tr>
<td>{{ bank.name }}</td>
<td>{{ bank.account }}</td>
<td>{{ bank.iban }}</td>
<td>{{ bank.swift }}</td>
<td>{{ bank.address }}</td>
<td><a href="/banks/edit/{{ bank.key }}">Edit</a></td>
<td>
<form method="post" action="/banks/delete/{{ key }}" onsubmit="return confirm('Delete this bank?');">
<button type="submit">Delete</button>
</form>
</td>
</tr>
{% endfor %}
</tbody>
</table>

</body>
</html>
"""

EDIT_BANK_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Edit Bank</title>
<style>
body { font-family: Arial; margin: 30px; }
input { width: 420px; padding: 6px; margin: 5px 0 12px; }
button { padding: 8px 14px; }
.box { border:1px solid #ddd; padding:15px; width:500px; }
</style>
</head>
<body>

<h2>Edit Bank</h2>

<div class="box">
<form method="post" action="/banks/update/{{ bank.key }}">
Bank Name:<br><input name="bank_name" value="{{ bank.name }}"><br>
Account No:<br><input name="account" value="{{ bank.account }}"><br>
IBAN No:<br><input name="iban" value="{{ bank.iban }}"><br>
SWIFT Code:<br><input name="swift" value="{{ bank.swift }}"><br>
Bank Address:<br><input name="bank_address" value="{{ bank.address }}"><br>
<button type="submit">Update Bank</button>
</form>
</div>

<br>
<a href="/banks">Back to Banks</a> | <a href="/">Back to Documents</a>

</body>
</html>
"""


def draw_invoice_header(c, title, invoice_no, form, show_po):
    w, h = base_page(c)

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, 660, title)

    c.setFont("Helvetica", 10)
    if "PROFORMA" in title.upper():
         label = "PROFORMA INVOICE NO:"
    elif "COMMERCIAL" in title.upper():
        label = "COMMERCIAL INVOICE NO:"
    else:
        label = "INVOICE NO:"

    c.drawString(60, 600, f"{label} {invoice_no}")
    c.drawString(340, 600, f"Date: {form.get('date','')}")
    
    y = 575
    customer_text = f"Customer: {form.get('name','')}"
    y = draw_wrapped(c, 60, y, customer_text, max_chars=60)
    y -= 10
    y = draw_wrapped(c, 60, y, f"Address: {form.get('address','')}", max_chars=55)
    y -= 20

    c.drawString(60, y, f"Phone: {form.get('phone','')}")
    c.drawString(240, y, f"Fax: {form.get('fax','')}")
    y -= 20

    if show_po and form.get("po"):
        c.drawString(60, y, f"PO: {form.get('po')}")
        y -= 18

    return y - 12

def draw_justified_text(c, x_start, x_end, y, text):
    text = text.upper()
    words = text.split()

    if len(words) <= 1:
        c.drawString(x_start, y, text)
        return

    total_width = x_end - x_start
    words_width = sum(c.stringWidth(word, "Helvetica-Bold", 14) for word in words)
    space_between_words = ((total_width - words_width) / (len(words) - 1))*0.7

    x = x_start
    for word in words:
        c.drawString(x, y, word)
        x += c.stringWidth(word, "Helvetica-Bold", 16) + space_between_words

def draw_invoice_table(c, y, common):
    c.setFont("Helvetica-Bold", 10)
    c.drawString(80, y, "Item")
    c.drawString(250, y, "Qty")
    c.drawString(330, y, "Price")
    c.drawString(430, y, "Total")

    y -= 10
    c.line(80, y, 500, y)
    y -= 18

    c.setFont("Helvetica", 10)
    for p in common["products"]:
        c.drawString(80, y, p["name"])
        c.drawString(250, y, str(round(p["qty"], 2)))
        c.drawString(330, y, str(round(p["price"], 2)))
        c.drawString(430, y, str(round(p["total"], 2)))
        y -= 16

    if common["show_pallets"]:
        c.drawString(80, y, "WOODEN PALLETS")
        c.drawString(250, y, str(common["pallet_qty"]))
        c.drawString(330, y, str(common["pallet_price"]))
        c.drawString(430, y, str(common["pallet_total"]))
        y -= 16

    c.line(80, y, 500, y)
    y -= 16

    c.setFont("Helvetica-Bold", 11)
    c.drawString(350, y, "TOTAL")
    c.drawString(430, y, str(common["grand_total"]))
    return y - 24

def draw_invoice_footer(c, y, form, common, show_bank=True):
    c.setFont("Helvetica", 10)

    c.drawString(60, y, f"Delivery Terms: {form.get('delivery_terms','')}")
    y -= 14

    c.drawString(60, y, f"Packing: {common['packing_text']}")
    y -= 14

    c.drawString(60, y, f"Payment: {form.get('payment','')}")
    y -= 18

    if show_bank:
        c.drawString(60, y, f"Bank: {form.get('bank_name','')}")
        y -= 14
        c.drawString(60, y, f"Account: {form.get('account','')}")
        y -= 14
        c.drawString(60, y, f"IBAN: {form.get('iban','')}")
        y -= 14
        c.drawString(60, y, f"SWIFT: {form.get('swift','')}")
        y -= 14
        y = draw_wrapped(c, 60, y, f"Address: {form.get('bank_address','')}", max_chars=58)
        y -= 18

    c.drawString(60, y, f"Goods Origin: {form.get('goods_origin','')}")
    y -= 14
    c.drawString(60, y, f"Supplier Origin: {form.get('supplier_origin','')}")
    y -= 14
    c.drawString(60, y, f"HS Code: {form.get('hs','')}")

def draw_packing_list(c, form, common):
    w, h = base_page(c)

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, 660, "PACKING LIST")
    y = 600
    c.setFont("Helvetica", 10)

    to_text = f"To: {form.get('name','')}"
    y = draw_wrapped(c, 60, y, to_text,max_chars=65)
    y -= 10
    y = draw_wrapped(c, 60, y, form.get("address", ""), max_chars=55)
    y -= 15

    c.drawString(60, y, f"Tel: {form.get('phone','')}")
    y -= 14
 
    c.drawString(60, y, f"Fax: {form.get('fax','')}")
    y -= 18

    c.drawString(60, y, f"AS PER P/I NO: {form.get('proforma_no','')}")
    c.drawString(300, y, f"DATED: {form.get('date','')}")
    y -= 16

    c.drawString(60, y, f"Expiry Date: {common['expiry_text']}")
    y -= 16

    c.drawString(60, y, f"PO: {form.get('po','')}")
    y -= 26

    product_names = ", ".join([p["name"] for p in common["products"]])
    left_x = 95
    right_x = 500
    product_names = ", ".join([p["name"] for p in common["products"]]) or "ALKALINE SOLID SODIUM SILICATE"
    from reportlab.pdfbase.pdfmetrics import stringWidth
    text = product_names
    c.setFont("Helvetica-Bold", 16)
    text_width = stringWidth(text, "Helvetica-Bold", 16)
    center_x = (left_x + right_x) / 2
    x_position = center_x - (text_width / 2)
    c.drawString(x_position, y, text)
    y -= 25

    c.setFont("Helvetica-Bold", 10)
    c.drawString(80, y, "Description")
    c.drawString(360, y, "Weight (MT)")
    y -= 10
    c.line(80, y, 470, y)
    y -= 18

    c.setFont("Helvetica", 10)
    c.drawString(80, y, "WEIGHT OF GOODS")
    c.drawString(360, y, f"{common['goods_weight']} MT NET")
    y -= 16

    c.drawString(80, y, f"{common['bags_count']} JUMBO BAGS")
    c.drawString(360, y, f"{common['bags_weight_total']} MT NET")
    y -= 16

    if common["show_pallets"]:
        c.drawString(80, y, f"{common['pallet_qty']} WOODEN PALLETS")
        c.drawString(360, y, f"{common['pallets_weight_total']} MT NET")
        y -= 16

    c.line(80, y, 470, y)
    y -= 18

    c.setFont("Helvetica-Bold", 11)
    c.drawString(80, y, "TOTAL")
    c.drawString(360, y, f"{common['gross_weight']} MT GROSS")
    y -= 24

    c.setFont("Helvetica", 10)
    c.drawString(80, y, f"PACKING: {common['packing_text']}")

def draw_coa(c, form):
    mr_data = load_mr_data()
    selected_mr = form.get("selected_mr", "")
    details = mr_data.get(selected_mr, {})

    w, h = base_page(c)

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2, 650, "Certificate of Analysis")
    c.line(220, 645, 375, 645)

    y = 615
    c.setFont("Helvetica", 10)
    
    to_text = f"To: {form.get('name','')}"
    y = draw_wrapped(c, 60, y, to_text,max_chars=65)
    y -= 10
    y = draw_wrapped(c, 60, y, form.get("address", ""), max_chars=55)
    y -= 10
    c.drawString(60, y, f"E-mail: {form.get('email','')}")
    y -= 13
    c.drawString(60, y, f"Tel: {form.get('phone','')}")
    y -= 13
    c.drawString(60, y, f"PO Number: {form.get('po','')}")

    y -= 25
    date_text = form.get("date", "")
    expiry_text = add_3_years(date_text)

    c.drawString(60, y, f"Production Date: {date_text}")
    c.drawString(330, y, f"Expiry Date: {expiry_text}")
    y -= 14
    c.drawString(60, y, f"Analysis Date: {date_text}")
    y -= 14
    c.drawString(60, y, f"Lot Number: {form.get('lot_number','')}")

    y -= 30

    product_names = ", ".join([p["name"] for p in get_products(form)]) or "ALKALINE SOLID SODIUM SILICATE"
    mr_value = details.get("molar_ratio", selected_mr)
    
    left_x = 95
    right_x = 500

    from reportlab.pdfbase.pdfmetrics import stringWidth

    text = f"{product_names} {mr_value}"

    c.setFont("Helvetica-Bold", 16)

    text_width = stringWidth(text, "Helvetica-Bold", 17)

    center_x = (left_x + right_x) / 2
    x_position = center_x - (text_width / 2)

    c.drawString(x_position, y, text)
    y -= 25
    # الخط اللي تحتها
    text = "Chemical Analysis:"
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, text)
    text_width = c.stringWidth(text, "Helvetica-Bold", 12)
    c.line(60, y-2, 60 + text_width, y-2)
    y -= 20
       
    rows = [
        ("Analysis", "Results"),
        ("Molar Ratio", details.get("molar_ratio", "")),
        ("Sodium oxide (wt%Na2O)", details.get("sodium_oxide", "")),
        ("Silicon oxide (wt%SiO2)", details.get("silicon_oxide", "")),
        ("Total Solid", details.get("total_solid", "")),
        ("Characters", details.get("characters", "")),
        ("Color", details.get("color", "")),
    ]
    left_x = 95
    right_x = 500
    top_y = y
    table_w = right_x - left_x
    col_w = table_w / 2
    bottom_limit = 145
    available_h = top_y - bottom_limit
    row_h = min(38, available_h / len(rows))
    row_h = max(row_h, 24)

    table_h = row_h * len(rows)
    c.rect(left_x, top_y - table_h, table_w, table_h)
    c.line(left_x + col_w, top_y, left_x + col_w, top_y - table_h)

    for i in range(1, len(rows)):
        yy = top_y - (row_h * i)
        c.line(left_x, yy, right_x, yy)

    for i, (a, r) in enumerate(rows):
        yy = top_y - (row_h * i) - (row_h / 2 + 4 )
        if i == 0:
            c.setFont("Helvetica-BoldOblique", 11)
        else:
            c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(left_x + col_w/2, yy, a)
        c.drawCentredString(left_x + col_w + col_w/2, yy, r)

@app.route("/")
def home():
    return render_template_string(FORM_HTML, mr_data=load_mr_data(), customers=load_customers(), banks=load_banks())

@app.route("/generate", methods=["POST"])
def generate():
    save_customer_from_form(request.form)
    save_bank_from_form(request.form)
    save_invoice_from_form(request.form)
    return render_template_string(RESULT_HTML, hidden_fields=build_hidden_fields(request.form))

@app.route("/history")
def history():
    invoices = load_invoices()
    invoice_items = list(reversed(list(enumerate(invoices))))
    return render_template_string(HISTORY_HTML, invoice_items=invoice_items)

@app.route("/invoice/edit/<int:invoice_index>")
def edit_invoice(invoice_index):
    invoices = load_invoices()
    if invoice_index < 0 or invoice_index >= len(invoices):
        return "Invoice not found"

    invoice = invoices[invoice_index]
    saved = invoice.get("form_data", {})
    

    if not saved:
        saved = {
            "proforma_no": [invoice.get("proforma_no", "")],
            "commercial_no": [invoice.get("commercial_no", "")],
            "date": [invoice.get("date", "")],
            "po": [invoice.get("po", "")],
            "name": [invoice.get("customer", "")],
            "selected_mr": [invoice.get("selected_mr", "")],
            "product_name": [p.get("name", "") for p in invoice.get("products", [])],
            "product_qty": [str(p.get("qty", "")) for p in invoice.get("products", [])],
            "product_price": [str(p.get("price", "")) for p in invoice.get("products", [])],
        }

    names = saved_list(saved, "product_name")
    qtys = saved_list(saved, "product_qty")
    prices = saved_list(saved, "product_price")
    products = []
    max_len = max(len(names), len(qtys), len(prices), 1)
    for i in range(max_len):
        products.append({
            "name": names[i] if i < len(names) else "",
            "qty": qtys[i] if i < len(qtys) else "",
            "price": prices[i] if i < len(prices) else ""
        })

    def g(key, default=""):
        return saved_get(saved, key, default)

    return render_template_string(
        EDIT_INVOICE_HTML,
        g=g,
        products=products,
        mr_data=load_mr_data(),
        customers=load_customers(),
        banks=load_banks(),
        invoice_id=invoice.get("id")
    )
    
@app.route("/invoice/update/<int:invoice_id>", methods=["POST"])
def update_invoice(invoice_id):
    common = get_common_data(request.form)
    data = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "proforma_no": request.form.get("proforma_no", ""),
        "commercial_no": request.form.get("commercial_no", ""),
        "date": request.form.get("date", ""),
        "po": request.form.get("po", ""),
        "customer": request.form.get("name", ""),
        "selected_mr": request.form.get("selected_mr", ""),
        "products": common["products"],
        "grand_total": common["grand_total"],
        "gross_weight": common["gross_weight"],
        "form_data": form_to_saved_data(request.form)
    }

    try:
        supabase.table("invoices").update(data).eq("id", invoice_id).execute()
    except Exception as e:
        print("UPDATE INVOICE ERROR:", e)

    return redirect("/history")


class SavedForm:
    def __init__(self, saved):
        self.saved = saved or {}

    def get(self, key, default=""):
        return saved_get(self.saved, key, default)

    def getlist(self, key):
        return saved_list(self.saved, key)

    def lists(self):
        for key, value in self.saved.items():
            if isinstance(value, list):
                yield key, value
            else:
                yield key, [value]

def get_saved_form_from_invoice(invoice_index):
    invoices = load_invoices()
    if invoice_index < 0 or invoice_index >= len(invoices):
        return None
    invoice = invoices[invoice_index]
    saved = invoice.get("form_data", {})
    if not saved:
        saved = {
            "proforma_no": [invoice.get("proforma_no", "")],
            "commercial_no": [invoice.get("commercial_no", "")],
            "date": [invoice.get("date", "")],
            "po": [invoice.get("po", "")],
            "name": [invoice.get("customer", "")],
            "selected_mr": [invoice.get("selected_mr", "")],
            "product_name": [p.get("name", "") for p in invoice.get("products", [])],
            "product_qty": [str(p.get("qty", "")) for p in invoice.get("products", [])],
            "product_price": [str(p.get("price", "")) for p in invoice.get("products", [])],
        }
    return SavedForm(saved)

@app.route("/invoice/download/<int:invoice_index>/<doc_type>", methods=["POST"])
def download_saved_invoice(invoice_index, doc_type):
    form = get_saved_form_from_invoice(invoice_index)
    if form is None:
        return "Invoice not found"

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    if doc_type == "proforma":
        common = get_common_data(form)
        y = draw_invoice_header(c, "PROFORMA INVOICE", form.get("proforma_no", ""), form, show_po=False)
        y = draw_invoice_table(c, y, common)
        draw_invoice_footer(c, y, form, common, show_bank=True)
        filename = "proforma.pdf"

    elif doc_type == "commercial":
        common = get_common_data(form)
        y = draw_invoice_header(c, "COMMERCIAL INVOICE", form.get("commercial_no", ""), form, show_po=True)
        y = draw_invoice_table(c, y, common)
        draw_invoice_footer(c, y, form, common, show_bank=False)
        filename = "commercial.pdf"

    elif doc_type == "packing":
        common = get_common_data(form)
        draw_packing_list(c, form, common)
        filename = "packing.pdf"

    elif doc_type == "coa":
        draw_coa(c, form)
        filename = "coa.pdf"

    else:
        return "Invalid document type"

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=filename)

@app.route("/invoice/delete/<int:invoice_id>", methods=["POST"])
def delete_invoice(invoice_id):
    try:
        supabase.table("invoices").delete().eq("id", invoice_id).execute()
    except Exception as e:
        print("DELETE INVOICE ERROR:", e)

    return redirect("/history")


@app.route("/proforma", methods=["POST"])
def proforma():
    common = get_common_data(request.form)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    y = draw_invoice_header(c, "PROFORMA INVOICE", request.form.get("proforma_no", ""), request.form, show_po=False)
    y = draw_invoice_table(c, y, common)
    draw_invoice_footer(c, y, request.form, common, show_bank=True)

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="proforma.pdf")

@app.route("/commercial", methods=["POST"])
def commercial():
    common = get_common_data(request.form)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    y = draw_invoice_header(c, "COMMERCIAL INVOICE", request.form.get("commercial_no", ""), request.form, show_po=True)
    y = draw_invoice_table(c, y, common)
    draw_invoice_footer(c, y, request.form, common, show_bank=False)

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="commercial.pdf")

@app.route("/packing", methods=["POST"])
def packing():
    common = get_common_data(request.form)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    draw_packing_list(c, request.form, common)

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="packing.pdf")

@app.route("/coa", methods=["POST"])
def coa():
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    draw_coa(c, request.form)

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="coa.pdf")

@app.route("/mr")
def mr_home():
    return render_template_string(MR_HTML, mr_data=load_mr_data(), selected=None)

@app.route("/mr/show", methods=["POST"])
def mr_show():
    data = load_mr_data()
    selected = request.form.get("selected_mr")
    details = data.get(selected, {})
    return render_template_string(MR_HTML, mr_data=data, selected=selected, details=details)

@app.route("/mr/add", methods=["POST"])
def mr_add():
    data = load_mr_data()
    mr_name = request.form.get("mr_name", "").strip()

    if mr_name:
        data[mr_name] = {
            "molar_ratio": request.form.get("molar_ratio", ""),
            "sodium_oxide": request.form.get("sodium_oxide", ""),
            "silicon_oxide": request.form.get("silicon_oxide", ""),
            "total_solid": request.form.get("total_solid", ""),
            "characters": request.form.get("characters", ""),
            "color": request.form.get("color", "")
        }
        save_mr_data(data)

    return redirect("/mr")

@app.route("/mr/edit/<mr_name>")
def mr_edit(mr_name):
    data = load_mr_data()
    details = data.get(mr_name)
    if not details:
        return "MR not found"
    return render_template_string(EDIT_MR_HTML, mr_name=mr_name, details=details)

@app.route("/mr/update/<mr_name>", methods=["POST"])
def mr_update(mr_name):
    data = load_mr_data()

    if mr_name in data:
        data[mr_name] = {
            "molar_ratio": request.form.get("molar_ratio", ""),
            "sodium_oxide": request.form.get("sodium_oxide", ""),
            "silicon_oxide": request.form.get("silicon_oxide", ""),
            "total_solid": request.form.get("total_solid", ""),
            "characters": request.form.get("characters", ""),
            "color": request.form.get("color", "")
        }
        save_mr_data(data)

    return redirect("/mr")

@app.route("/mr/delete/<mr_name>", methods=["POST"])
def mr_delete(mr_name):
    data = load_mr_data()

    if mr_name in data:
        del data[mr_name]
        save_mr_data(data)

    return redirect("/mr")


@app.route("/customers")
def customers_home():
    return render_template_string(CUSTOMERS_HTML, customers=load_customers())

@app.route("/customers/save", methods=["POST"])
def customers_save():
    save_customer_from_form(request.form)
    return redirect("/customers")

@app.route("/customers/edit/<customer_key>")                                                                
def customers_edit(customer_key):
    customers = load_customers()
    customer = customers.get(customer_key)
    if not customer:
        return "Customer not found"
    return render_template_string(EDIT_CUSTOMER_HTML, customer_key=customer_key, customer=customer)

@app.route("/customers/update/<customer_key>", methods=["POST"])
def customers_update(customer_key):
    customers = load_customers()
    customer = customers.get(customer_key)

    # نجيب الاسم الجديد وننضفه
    new_name = request.form.get("name", "").strip()

    # مفيش عميل أو الاسم فاضي نرجع
    if not customer or not new_name:
        return redirect("/customers")

    # update في Supabase
    supabase.table("customers").update({
        "name": new_name,
        "address": request.form.get("address", ""),
        "phone": request.form.get("phone", ""),
        "fax": request.form.get("fax", ""),
        "email": request.form.get("email", "")
    }).eq("name", customer.get("name")).execute()

    return redirect("/customers")

@app.route("/customers/delete/<customer_key>", methods=["POST"])
def customers_delete(customer_key):
    customers = load_customers()
    customer = customers.get(customer_key)

    print("KEY:", customer_key)

    if customer:
        print("REAL NAME:", customer.get("name"))

        res = supabase.table("customers").delete().eq("name", customer.get("name")).execute()
        print("DELETE RESULT:", res.data)

    return redirect("/customers")
    
@app.route("/banks")
def banks_home():
    return render_template_string(BANKS_HTML, banks=load_banks())

@app.route("/banks/save", methods=["POST"])
def banks_save():
    save_bank_from_form(request.form)
    return redirect("/banks")

@app.route("/banks/edit/<bank_key>")
def banks_edit(bank_key):
    banks = load_banks()
    bank = banks.get(bank_key)
    if not bank:
        return "Bank not found"
    return render_template_string(EDIT_BANK_HTML, bank_key=bank_key, bank=bank)

@app.route("/banks/update/<bank_key>", methods=["POST"])
def banks_update(bank_key):
    banks = load_banks()
    bank = banks.get(bank_key)

    new_name = request.form.get("bank_name", "").strip()

    if not bank or not new_name:
        return redirect("/banks")

    supabase.table("banks").update({
        "name": new_name,
        "account": request.form.get("account", ""),
        "iban": request.form.get("iban", ""),
        "swift": request.form.get("swift", ""),
        "address": request.form.get("bank_address", "")
    }).eq("name", bank.get("name", "")).execute()

    return redirect("/banks")

@app.route("/banks/delete/<bank_key>", methods=["POST"])
def banks_delete(bank_key):
    banks = load_banks()
    bank = banks.get(bank_key)

    if bank:
        supabase.table("banks").delete().eq("name", bank.get("name", "")).execute()

    return redirect("/banks")
@app.route("/status/<int:idx>", methods=["GET", "POST"])
def status_page(idx):
    invoices = load_invoices()

    if idx < 0 or idx >= len(invoices):
        return "Invoice not found"

    inv = invoices[idx]

    if request.method == "POST":
        data = {
            "status_booking_date": request.form.get("booking_date") or None,
            "status_production": request.form.get("production") or "not done",
            "status_payment": request.form.get("payment") or "none",
            "status_bl_co": request.form.get("bl_co") or "none",
            "dhl_no": request.form.get("dhl_no") or "",
            "is_complete": False
        }

        supabase.table("invoices").update(data).eq("id", inv["id"]).execute()
        return redirect("/history")

    return f"""
    <h2>Invoice Status</h2>
    <p><b>Customer:</b> {inv.get('customer','')}</p>
    <p><b>Proforma No:</b> {inv.get('proforma_no','')}</p>

    <form method="post">
        Booking Date:
       <input type="datetime-local" name="booking_date" value="{inv.get('status_booking_date','')[:16]}">

        Production:
        <select name="production">
          <option value="not done" {"selected" if inv.get("status_production") == "not done" else ""}>Not Done</option>
          <option value="done" {"selected" if inv.get("status_production") == "done" else ""}>Done</option>
        </select>
    
        Payment:
        <select name="payment">
           <option value="none" {"selected" if inv.get("status_payment") == "none" else ""}>None</option>
           <option value="swift" {"selected" if inv.get("status_payment") == "swift" else ""}>Swift</option>
           <option value="cash" {"selected" if inv.get("status_payment") == "cash" else ""}>Cash</option>
        </select>

        B/L & CO:
        <select name="bl_co">
           <option value="none" {"selected" if inv.get("status_bl_co") == "none" else ""}>None</option>
           <option value="draft" {"selected" if inv.get("status_bl_co") == "draft" else ""}>Draft</option>
           <option value="confirmed" {"selected" if inv.get("status_bl_co") == "confirmed" else ""}>Confirmed</option>
        </select>

        DHL No:
       <input type="text" name="dhl_no" value="{inv.get('dhl_no','')}">    
        <br><br>


        <button type="submit">Save Status</button>
    </form>

    <br>
    <a href="/invoice-history">Back</a>
    """
@app.route("/dashboard/<int:idx>", methods=["GET", "POST"])
def dashboard(idx):
    invoices = load_invoices()

    if idx < 0 or idx >= len(invoices):
        return "Invoice not found"

    inv = invoices[idx]

    if request.method == "POST":
        supabase.table("invoices").update({
            "is_complete": True
        }).eq("id", inv["id"]).execute()

        return redirect("/history")

    return f"""
    <h2>Proforma Dashboard</h2>

    <p><b>Proforma No:</b> {inv.get('proforma_no','')}</p>
    <p><b>Customer:</b> {inv.get('customer','')}</p>
    <p><b>MR:</b> {inv.get('selected_mr','')}</p>
    <p><b>Total:</b> {inv.get('grand_total','')}</p>
    <p><b>Gross Weight:</b> {inv.get('gross_weight','')}</p>

    <h3>Status Data</h3>
    <p><b>Booking Date:</b> {inv.get('status_booking_date','')}</p>
    <p><b>Production:</b> {inv.get('status_production','')}</p>
    <p><b>Payment:</b> {inv.get('status_payment','')}</p>
    <p><b>B/L & CO:</b> {inv.get('status_bl_co','')}</p>
    <p><b>DHL No:</b> {inv.get('dhl_no','')}</p>

    <br>

    {'''
    <form method="post">
        <button type="submit">Complete</button>
    </form>
    ''' if not inv.get('is_complete') else '<h3 style="color:green;">Completed ✅</h3>'}

    <br>
    <a href="/history">Back to History</a>
    """    
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
