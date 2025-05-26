"""Application to manage part inventory."""

import logging
import sqlite3
import os

from flask import Flask, g, redirect, render_template, request

# --- Variable setup ---
app = Flask(__name__)
PARTLIST = []  # type: ignore
MESSAGE = ""

# Asegurarse de que el directorio de la base de datos exista
DB_DIR = "homework"
DB_PATH = os.path.join(DB_DIR, "inventory.db")
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

# --- Logging setup ---
logging.basicConfig(
    filename="homework/opdb-app.log",
    format="%(asctime)s %(levelname)-8s [%(filename)-12s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

log = logging.getLogger("inventory-app")

# --- Database connection ---
def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if "db" not in g:
        try:
            log.info("Database Connection")
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
        except Exception as d:
            raise Exception("Failed to connect to the database.") from d
    return g.db

@app.teardown_appcontext
def teardown_db(exception):
    """Close database connection."""
    print(exception)
    db = g.pop("db", None)
    if db is not None:
        db.close()
        log.info("Closed DB Connection")

# --- Inventory parts management ---
def getparts():
    """Retrieve current part inventory."""
    result = (
        get_db()
        .execute("SELECT part_no, quant FROM part_inventory_app")
        .fetchall()
    )
    log.info("GETPARTS() – CURRENT PART INVENTORY:\n\t\t%s", result)
    return result

@app.route("/requestparts", methods=["POST"])
def requestparts():
    """Update part quantity for given part number."""

    global PARTLIST
    global MESSAGE

    part_no = request.form.get("part_requested")
    req_amt = request.form.get("amount_requested")

    log.info("RECEIVED FORM DATA:\n\t\tPART = %s\n\t\tQUANTITY = %s", part_no, req_amt)

    if part_no and req_amt:
        try:
            req_amt = int(req_amt)
        except ValueError:
            MESSAGE = "QUANTITY MUST BE A VALID INTEGER"
            return render_template("index.html", partlist=PARTLIST, message=MESSAGE)

        db = get_db()

        result = db.execute(
            "SELECT quant FROM part_inventory_app WHERE part_no = ?", (part_no,)
        ).fetchone()

        log.info("REQUESTPARTS() - results = %s", result)

        if result is not None:
            cur_val = result["quant"]
            print("cur_val =", cur_val)

            if cur_val >= req_amt:
                new_amt = cur_val - req_amt
                print("new amount is", new_amt)
                db.execute(
                    "UPDATE part_inventory_app SET quant = ? WHERE part_no = ?",
                    (new_amt, part_no)
                )
                db.commit()
                return redirect("/")
            else:
                MESSAGE = (
                    f"INSUFFICIENT QUANTITY FOR {part_no}; inventory = {cur_val}, "
                    f"requested = {req_amt}"
                )
        else:
            MESSAGE = f"PART NOT FOUND: {part_no}"
    else:
        MESSAGE = "INVALID PART NUMBER / QUANTITY"

    return render_template("index.html", partlist=PARTLIST, message=MESSAGE)

@app.route("/")
def index():
    """Render index.html using parts from the database."""

    global PARTLIST
    global MESSAGE

    log.info("PAGE REFRESH")
    MESSAGE = ""
    PARTLIST = getparts()
    PARTLIST = [dict(row) for row in PARTLIST]

    return render_template("index.html", partlist=PARTLIST, message=MESSAGE)

# --- Entry point ---
if __name__ == "__main__":
    log.info("BEGIN PROGRAM")
    try:
        app.run(host="127.0.0.1", debug=True)
    except Exception as e:
        print(f"ERROR: unable to run application:\n {str(e)}")
    log.info("END PROGRAM")
