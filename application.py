from flask import Flask, redirect, send_file, request, render_template, g
import sqlite3
from datetime import datetime
from xlwt import Workbook

app = Flask(__name__, static_folder="static")
# Change if you host on a different port or on the web
DOMAIN = "http://localhost:5000"
PATH = ""
DATABASE = PATH + "static/database/database.db"


# CONNECTING DATABASE
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# APIS IF NEEDED
@app.route('/bikes/api/<type>', methods=["POST", "GET"])
def apiList(type):
    query = "SELECT * FROM " + type
    cur = get_db().execute(query, ())
    rv = cur.fetchall()
    cur.close()
    dict = {}
    for tup in rv:
        dict[tup[0]] = tup[:]
    return dict


@app.route('/bikes/api/<type>/<id>', methods=["POST", "GET"])
def apiIndividual(type, id):
    query1 = "PRAGMA table_info(" + type + ");"
    cur = get_db().execute(query1, ())
    colData = cur.fetchall()
    cur.close()
    dict = {}
    for tup in colData:
        query2 = "SELECT " + tup[1] + " FROM " + type + " WHERE " + type[:-1] + "Id == " + id
        cur = get_db().execute(query2, ())
        itemData = cur.fetchall()
        cur.close()
        dict[tup[1]] = (tup[2], itemData[0][0])
    return dict


# TEMPLATE LOADERS
@app.route('/bikes', methods=["POST", "GET"])
def openHome():
    # GETTING SALES
    startDateComp = 0
    endDateComp = 100000000
    isFirstPage = False
    try:
        startDate = request.form["startDate"].split("-")
        endDate = request.form["endDate"].split("-")
    except KeyError:
        startDate = []
        endDate = []
    if len(startDate) == 3:
        startDateComp = int(str(startDate[0]) + str(startDate[1]) + str(startDate[2]))
    if len(endDate) == 3:
        endDateComp = int(str(endDate[0]) + str(endDate[1]) + str(endDate[2]))
    query = "SELECT * FROM Sales"
    cur = get_db().execute(query, ())
    data = cur.fetchall()
    dict = {}
    for (salesId, productId, salespersonId, customerId, date) in data:
        dateList = date.split("/")
        currDateComp = int(str("20" + str(dateList[2])) + str(dateList[0]) + str(dateList[1]))
        if currDateComp > endDateComp or currDateComp < startDateComp:
            continue
        try:
            productTup = get_db().execute("SELECT * FROM Products WHERE productId == " + str(productId), ()).fetchall()[
                0]
            customerTup = \
            get_db().execute("SELECT * FROM Customers WHERE customerId == " + str(customerId), ()).fetchall()[0]
            salespersonTup = \
            get_db().execute("SELECT * FROM Salespersons WHERE salespersonId == " + str(salespersonId), ()).fetchall()[
                0]
        except(IndexError):
            print("Invalid data for Sale with ID " + str(salesId))
            continue
        product = productTup[1] + " by " + productTup[2]
        commission = "$" + str(round(productTup[7] / 100 * productTup[5],2))
        price = "$" + str(productTup[5])
        customer = customerTup[1] + " " + customerTup[2]
        salesperson = salespersonTup[1] + " " + salespersonTup[2]
        date = date
        dict[salesId] = (product, customer, date, price, salesperson, commission)
    cur.close()

    # CREATE SALE FORM
    queryProducts = "SELECT productid , name, manufacturer FROM PRODUCTS WHERE QtyOnHand > 1"
    cur = get_db().execute(queryProducts, ())
    products = {}
    for (id, name, manufacturer) in cur.fetchall():
        products[id] = name + " by " + manufacturer + " (ID: " + str(id) + ")"

    querySalespersons = "SELECT SalespersonID, FirstName, LastName FROM Salespersons"
    cur = get_db().execute(querySalespersons, ())
    salespersons = {}
    for (id, fname, lname) in cur.fetchall():
        salespersons[id] = fname + " " + lname + " (ID: " + str(id) + ")"

    queryCustomers = "SELECT CustomerID, FirstName, LastName FROM Customers"
    cur = get_db().execute(queryCustomers, ())
    customers = {}
    for (id, fname, lname) in cur.fetchall():
        customers[id] = fname + " " + lname + " (ID: " + str(id) + ")"
    cur.close()

    return render_template("index.html", data=dict, domain=DOMAIN, products=products, salespersons=salespersons,
                           customers=customers)


# REDIRECTS
@app.route('/bikes/data/<type>', methods=["POST", "GET"])
def display(type):
    query = "SELECT * FROM " + type
    cur = get_db().execute(query, ())
    rv = cur.fetchall()
    cur.close()
    dict = {}
    for tup in rv:
        dict[tup[0]] = tup[:]
    return render_template("display.html", data=dict, domain=DOMAIN, category=type)


@app.route('/bikes/data/<type>/<id>', methods=["POST", "GET"])
def edit(type, id):
    query1 = "PRAGMA table_info(" + type + ");"
    cur = get_db().execute(query1, ())
    colData = cur.fetchall()
    cur.close()
    dict = {}

    for tup in colData:
        query2 = "SELECT " + tup[1] + " FROM " + type + " WHERE " + type[:-1] + "Id == " + id
        cur = get_db().execute(query2, ())
        itemData = cur.fetchall()
        cur.close()
        dict[tup[1]] = (tup[2], itemData[0][0])
    return render_template("edit.html", data=dict, domain=DOMAIN, type=type, id=id)


@app.route("/bikes/data/<type>/<id>/save", methods=["POST", "GET"])
def saveData(type, id):
    query1 = "PRAGMA table_info(" + type + ");"
    cur = get_db().execute(query1, ())
    colData = cur.fetchall()
    cur.close()
    dict = {}
    for tup in colData:
        query2 = "SELECT " + tup[1] + " FROM " + type + " WHERE " + type[:-1] + "Id == " + id
        cur = get_db().execute(query2, ())
        itemData = cur.fetchall()
        cur.close()
        dict[tup[1]] = (tup[2], itemData[0][0])
    cols = "("
    vals = "("
    for (col, tup) in dict.items():
        val = str(request.form[col])
        if len(val) != 0:
            if tup[0] == "TEXT":
                val = "'" + val + "'"
            cols += str(col) + ", "
            vals += val + ", "
    cols = cols[:-2] + ")"
    vals = vals[:-2] + ")"
    q = "REPLACE INTO " + type + cols + " VALUES" + vals
    get_db().execute(q, ())
    get_db().commit()
    return redirect(DOMAIN + '/bikes/data/' + type)


@app.route('/bikes/createSale/save', methods=["POST", "GET"])
def saveSale():
    productId = str(request.form['product'])
    salespersonId = str(request.form['salesperson'])
    customerId = str(request.form['customer'])
    date = (datetime.now()).strftime("%m/%d/%y")
    if salespersonId == 'Choose...' or customerId == 'Choose...' or productId == 'Choose...':
        return redirect(DOMAIN + '/bikes/createSale')
    queryUpdateProducts = "UPDATE Products SET QtyOnHand = QtyOnHand - 1 WHERE productId == " + productId
    cur = get_db().execute(queryUpdateProducts, ())
    get_db().commit()
    queryCreateSale = "INSERT INTO Sales(ProductId, SalesPersonId, CustomerId, StartDate) VALUES(?,?,?,?)"
    cur = get_db().execute(queryCreateSale, (productId, salespersonId, customerId, date))
    get_db().commit()
    cur.close()
    return redirect(DOMAIN + '/bikes')


# DOWNLOADS
@app.route('/bikes/report', methods=["POST", "GET"])
def generateReport():
    query = "SELECT * FROM Salespersons JOIN Sales ON Salespersons.SalespersonId = Sales.SalesPersonId"
    cur = get_db().execute(query, ())
    data = cur.fetchall()
    cur.close()
    dict = {}
    for item in data:
        date = item[12].split("/")
        month = date[0]
        try:
            productTup = get_db().execute("SELECT * FROM Products WHERE productId == " + str(item[9]), ()).fetchall()[
                0];
        except(IndexError):
            print("Invalid data for Detected in Product")
        name = item[1] + " " + item[2]
        commission = "$" + str(round(productTup[7] / 100 * productTup[5], 2))
        year = "20" + date[2]
        quarter = (int(month) - 1) // 3 + 1
        if year not in dict:
            dict[year] = {1: {}, 2: {}, 3: {}, 4: {}}
            dict[year][quarter][name] = commission
        else:
            if name not in dict[year][quarter]:
                dict[year][quarter][name] = commission
            else:
                dict[year][quarter][name] += commission
    wb = Workbook()
    for year, data in dict.items():
        rowIndex = 0
        sheet = wb.add_sheet(year + "Report", cell_overwrite_ok=True)
        sheet.write_merge(rowIndex, rowIndex, 0, 4, (year + " Quarterly Salesperson Commission Report"))
        rowIndex += 1
        sheet.write(rowIndex, 0, "Quarter")
        sheet.write(rowIndex, 1, "Salesperson")
        sheet.write(rowIndex, 2, "Commission")
        rowIndex += 1
        for i in range(1, 5):
            sheet.write(rowIndex, 0, i)
            for name, commission in data[i].items():
                sheet.write(rowIndex, 1, name)
                sheet.write(rowIndex, 2, commission)
                rowIndex += 1
    path = "static/downloads/CommissionReport.xls"
    wb.save(path)
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.debug = True
    app.run()
