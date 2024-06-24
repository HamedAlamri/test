import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from helpers import *
from random import randint, choice
from string import ascii_letters
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta
from phonenumbers import is_valid_number, parse
from keys import *
from twilio.rest import Client

# flask run
app = Flask(__name__)


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = "dfjka;jskdfojiwejifojiifjsdo823j2jeopujfewjf823as32#dsaf2@"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///football.db")



# define the all available sizes for fields:
FIELD_SIZE_TYPE = ["Half field*A","Half field*B", "Half field*C",  "Full Field", "Small Field"]
PROFIT_PERCENTAGE = 1/100


# general functions
def calculate_money(infos):
    # count the total money and the profit
    total = 0.0
    try:
        for inf in infos:
            total += int(inf["price"])
    except:
        total = 0

    return total

def calculate_profit(totalMoney):
    profit = round(totalMoney * PROFIT_PERCENTAGE, 3)
    return profit



# send message to the custor
def sendMessage(text, phoneNumber):
    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body= text,
            from_= twilio_PhoneNumber,
            to = ("+968" + phoneNumber)
        )
    except:
        return False

    return True



# register the username and the password of mangers
def login_info(field_id, username, password, confirm_password):

    # get username and password from the data base which my match the new username and password
    # get the username if any, to check if the username is valid
    username_db = db.execute("SELECT username FROM mangers WHERE username = ?", username)


    # check if there any error
    # check if there is an empty gap
    if not username or not password or not confirm_password:
        return False

    # check if password and confirm_password are same
    elif not (password == confirm_password):
        return False

    # check if username are valid
    # first check if it exist
    elif len(username_db) == 1:
        if username in username_db[0]["username"]:
            return False

    # hash the new password
    password_hash = generate_password_hash(password, method='pbkdf2', salt_length=16)


    # add the user to the data base
    db.execute("INSERT INTO mangers (field_id, username,hash) VALUES (?,?,?)", field_id,username, password_hash)

    # save the session
    session["user_id"] = db.execute("SELECT field_id FROM mangers WHERE username = ?", username)

    return True

# to get the time and format it
def get_time_day():
    now = datetime.now()
    today = date.today()
    order_time = now.strftime("%H:%M:%S")
    order_time = str(today) + " " + str(order_time)
    return order_time


# to be sure that the available times for field is not expair
def check_time_up(time_field, date_field):

    time_now = (datetime.now()).hour
    date_today = str(date.today())

    time_field = (time_field.split(" "))
    addition = 0
    if time_field[1] == "pm":
        addition = 12

    time_field = (time_field[0]).split("-")
    time_field = (int(time_field[0]) + addition)

    if time_field >= 24:
        time_field = 23 
    
    time_field = time(time_field).hour


    if date_today == date_field:
        if time_now >= time_field:
            return False
    return True



def cancel_order_return_state(info, reason):
    try:
        # get all information form the dicti
        order_id = info["id_order"]
        person_name = info["person_name"]
        phone_number = info["phone_number"]
        field_id = info["field_id"] + "(" + info["field_name"] + ")"
        day = info["day"]
        time = info["time"]
        size = info["size"]
        price = info["price"]
        order_time = info["order_time"]

        # try to delete the order
        db.execute("DELETE FROM orders WHERE id_order = ?", order_id)

        # try to add the order iformation to cancel table
        db.execute("INSERT INTO cancel (field_id, day, time, order_time, size, person_name, person_number, reason, price) VALUES (?, ?,?,?,?,?,?,?,?)",field_id , day, time, order_time, size, person_name, phone_number, reason, price)

    except:
       return False, ""

    # seem there is no problem
    return True, info["phone_number"]


## for security and.....
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response



@app.route("/", methods=["GET", "POST"])
def index():

    # clear the session
    # session.clear()

    if request.method == "GET":
        infos = db.execute("SELECT * FROM fields_names")
        return render_template("homePage.html", infos=infos)


    # if post:
    else:
        field_id = request.form.get("field_id")

        ##
        infos = db.execute("SELECT * FROM field WHERE field_id = ?", field_id)
        infos2 = db.execute("SELECT * FROM fields_names WHERE field_id = ?", field_id)

        try:
            # delate the list format
            infos = infos[0]

            # get the field name
            field_name = infos["name"]


            # convert the string to list (sizes)
            sizes = (infos["size"]).split(":")
            # infos_size = []
            # for i in sizes:
            #     infos_size.append(i)


            # get the location of the field
            map = infos2[0]["mapURL"]


        except:
            print("400")
            return apology("ERROR", 400)

        return render_template("field.html", map= map, name=field_name, field_id= field_id, sizes=sizes)



# login for main manger
@app.route("/login", methods=["GET", "POST"])
def login():


    """Log user in"""
    # Forget any user_id
    # session.clear()
    session.pop("manger_id", None)

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 420)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 421)



        # Query database for username
        rows = db.execute("SELECT * FROM director WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 422)

        # Remember which user has logged in
        session["manger_id"] = rows[0]["id"]

        # Redirect to manger
        return redirect("/manger")


    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


# login for side mangers
@app.route("/Login", methods=["GET", "POST"])
def Login_side():

    """Log user in"""
    # Forget any user_id
    session.pop("user_id", None)

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 420)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 421)

        ##my addition
        username = request.form.get("username")

        # Query database for username
        rows = db.execute("SELECT * FROM mangers WHERE username = ?", username)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            print(len(rows))
            # print(check_password_hash(rows[0]["hash"], request.form.get("password")))
            return apology("invalid username and/or password", 422)

        # Remember which user has logged in
        session["user_id"] = rows[0]["field_id"]

        username_ = rows[0]["username"]
        field_id = rows[0]["field_id"]

        # Redirect to side mangers
        return redirect(url_for("fields_mangers", username_ = username_, field_id = field_id))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login_side.html")


@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "GET":

        order_date = request.args.get("date_input")
        order_time = request.args.get("time_input")
        order_size = request.args.get("size_input")
        field_id = request.args.get("field_id")


        # check if the data avaliible in the database
        infos_db = db.execute("SELECT * FROM field WHERE field_id = ?", field_id)
        location_name = db.execute("SELECT location_name FROM fields_names WHERE field_id = ?", field_id)
        print("location")

        try:
            # delate the list format
            infos_db = infos_db[0]
            field_id = infos_db["field_id"]
            field_name = infos_db["name"]
            location_name = location_name[0]["location_name"]
            print("delate format")
        except:
            return apology("ERROR", 670)


        try:
            time_db = (infos_db["time"]).split(":")
            print(time_db)
            sizes_db = (infos_db["size"]).split(":")
            print(sizes_db)
            price_db = (infos_db["price"]).split(":")
            print(price_db)
        except:
            return apology("ERROR", 732)

        # check if the time and size and price are correct
        if order_time not in time_db:
            print("error, 500")
            return apology("the time is not avilable", 500)

        if order_size not in sizes_db:
            print("error, 501")
            return apology("the size is not avilable", 501)

        try:
            # get the price depend on size
            price = 0
            for i in range(len(sizes_db)):
                if order_size == sizes_db[i]:
                    price = price_db[i]
        except:
            return apology("ERROR",435)


        # check if the field and size is available in this (date)
        # complete

        return render_template("order.html",field_id=field_id, name=field_name, location_name= location_name, size=order_size, date=order_date, time=order_time, price=price)


    else:
        name = request.form.get("name")
        fullPhoneNumber = request.form.get("phoneNumber")
        comments = request.form.get("comments")
        field_id = request.form.get("field_id")

        # get the date from the previce page by using hidden input elemnt
        Date = request.form.get("date")
        time = request.form.get("time")
        price = request.form.get("price")
        size =  request.form.get("size")

        # check if name and phone number are provide?
        print(fullPhoneNumber)
        if not name or not fullPhoneNumber:
            return apology("Name And Number are required To Order", 402)

        # check phone number is correct
        if not (is_valid_number(parse(fullPhoneNumber))):
            return apology("the phone number is not correct", 403)


        # check if the id is valid
        infos_by_ID_db = db.execute("SELECT * FROM field WHERE field_id = ?", field_id)
        if len(infos_by_ID_db) == 0:
            print("450")
            return apology("Invalid information", 450)

        # check if the time is a vilable
        infos_ = db.execute("SELECT * FROM orders WHERE field_id = ? AND day =? AND time = ? AND size = ?", field_id, Date, time, size)
        if len(infos_) != 0:
            print("451")
            print(infos_)
            return apology("Invalid information", 451)



        # create id for order
        number_ = randint(999, 9999999)
        letter1 = choice(ascii_letters)
        letter2 = choice(ascii_letters)
        order_id = "#" + str(number_) + letter1 + letter2

        # TO update the orders table in database
        # create variable for save data
        field_id0 = infos_by_ID_db[0]["field_id"]
        field_name = infos_by_ID_db[0]["name"]

        # comblete (ADD date colum for orders tables so we can truck the time)

        # get the time
        order_time = get_time_day()

        # state of the order
        state = "Booked"

        # to save the numebr with out the country
        number = fullPhoneNumber[4:]

        ## add infromation to orders table
        db.execute("INSERT INTO orders (id_order, person_name, phone_number, field_id, field_name, day, time, size, price, comments, order_time, stateTEXT, paid) VALUES (?, ?, ?, ?, ?, ?,?, ?, ?, ?, ?, ?, ?)",
            order_id,
            name,
            number,
            field_id0,
            field_name,
            Date,
            time,
            size,
            price,
            comments,
            order_time,
            state,
            "Yet")


        #send a message to the customer
        text = (f" \n Your order take place in {field_name}, {size} on {Date} at {time}\n price: {price}R.o\n orderID: {order_id}")
        phone = number

        sendMessage(text, phone)

        return render_template("confirmOrder.html", order_id=order_id, name = name, price=price, size=size, date=Date, time=time)


@app.route("/bookedUP")
def booked():
    infos = db.execute("SELECT * FROM orders ORDER BY order_time DESC")
    return render_template("bookedUP.html", infos=infos)



@app.route("/manger", methods=["GET", "POST"])
@login_required
def mang():

    # page with two buttons one for manger orders and another for mange fields
    if request.method == "GET":
        return render_template("manger.html")

    else:
        try:
            id = request.form.get("orderInfo")
            infos = db.execute("SELECT * FROM orders WHERE id = ?", id)
            infos = infos[0]
        except:
            return apology("ERROR..", 405)

        return render_template("checkInfos.html", infos=infos)



# this route for direct the manger to check the booked, canceld and all orders
@app.route("/manger/orders", methods=["GET"])
@login_required
def checkOrders():
    if request.method == "GET":
        return render_template("directMangerForOrders.html")



# this route for check the booked and the cancled orders BY the manger
@app.route("/manger/orders/booked", methods=["GET"])
@login_required
def checkBookedOrders():

    # if the manger select the booked orders buttton
    if request.method == "GET":
        infos = db.execute("SELECT * FROM orders WHERE stateTEXT = ? ORDER BY field_name, day, time DESC", "Booked")
        return render_template("mange_booked_orders.html", infos=infos, from_="manger", field_name = "All Fields")



@app.route("/manger/orders/canceled", methods=["GET", "POST"])
@login_required
def checkCanceledOrders():

    # if the manger select the canceld orders buttton
    if request.method == "GET":
        infos = db.execute("SELECT * FROM cancel ORDER BY field_id, day, time DESC")

        # count the total money and the profit
        total = calculate_money(infos)
        count = len(infos) # count the number of orders
        profit = calculate_profit(total)

        return render_template("mange_canceld_orders.html", infos=infos, from_="manger", field_name = "All Fields", total=total, profit=profit, count=count)


    # check information for a cancel order
    else:
        canceled_id = request.form.get("canceledId")
        infos = db.execute("SELECT * FROM cancel WHERE id = ? ORDER BY field_id, day, time DESC", canceled_id)
        try:
            infos = infos[0]
        except:
            infos = {'id':'NO INFORMATION'}

        return render_template("checkInfosForCanceledOrders.html", infos=infos, from_="manger", field_name = "All Fields")



@app.route("/manger/orders/completed", methods=["GET", "POST"])
@login_required
def checkAllOrders():

    # see all completed orders
    if request.method == "GET":
        infos = db.execute("SELECT * FROM orders WHERE stateTEXT = ? ORDER BY order_time DESC", "Done")

        # count the total money and the profit
        total = calculate_money(infos)
        count = len(infos) # count the number of orders
        profit = calculate_profit(total)

        return render_template("mange_completed_orders.html", infos=infos, from_="manger", field_name = "All Fields", total=total, profit=profit, count=count)

    # check specific order
    else:
        order_id = request.form.get("id_order")
        infos = db.execute("SELECT * FROM orders WHERE id_order = ?", order_id)

        try:
            infos = infos[0]
        except:
            infos = {'id_order':'NO INFO'}

        return render_template("checkInfosForCompletedOrders.html", infos=infos, from_="manger", field_name = "All Fields")


@app.route("/manger/fields", methods=["GET", "POST"])
@login_required
def directManger():
    # fields manger, two butons one for adding field and another for see all fields(same route by post)
    if request.method == "GET":
        infos = db.execute("SELECT * FROM field")
        return render_template("mange_fields.html", infos=infos)



@app.route("/manger/fields/check", methods=["GET", "POST"])
@login_required
def checkFields():

    # check fields for manger, page with all fields and there general infos
    if request.method == "GET":
        infos = db.execute("SELECT * FROM fields_names")
        return render_template("seeFields.html", infos=infos)

    # check specific field by it id
    else:
        field_id = request.form.get("field_id")
        infos = db.execute("SELECT * FROM fields_names WHERE field_id = ?", field_id)
        field_name = infos[0]["field_name"]
        return render_template("checkField.html", infos=infos, field_id = field_id, field_name=field_name)


@app.route("/manger/fields/check/<field_name>", methods=["GET", "POST"])
@login_required
def checkSpecifiField(field_name):

    # if the manger want to check the general information of the field
    if request.method == "GET":
        field_id = request.args.get("field_id")
        infos = db.execute("SELECT * FROM fields_names WHERE field_id = ?", field_id)
        infos_field = db.execute("SELECT * FROM field WHERE field_id = ?", field_id)
        infos_orders_all = db.execute("SELECT * FROM orders WHERE field_id = ? AND stateTEXT = ?", field_id, "Done")
        infos_orders_notPaid = db.execute("SELECT * FROM orders WHERE field_id = ? AND stateTEXT = ? AND paid = ?", field_id, "Done", "Yet")


        try:
            infos = infos[0]
            infos_field = infos_field[0]
        except:
            infos = {'field_id':"NO INFORMATION"}
            infos_field = {'field_id':"NO INFORMATION"}



        # count the TOTAL, money, profit and counts for this field
        totalMoney = calculate_money(infos_orders_all)
        totalCounts = len(infos_orders_all)
        totalProfit =  calculate_profit(totalMoney)


        # count not paid money, profit, counts
        money = calculate_money(infos_orders_notPaid)
        count = len(infos_orders_notPaid) # count the number of orders
        profit = calculate_profit(money)


        return render_template("checkFieldGeneralInfo.html", infos=infos, infos2=infos_field, money=money, profit=profit, count = count, totalProfit=totalProfit ,totalCounts = totalCounts, totalMoney=totalMoney)



    # if the manger want to see
    #  orders for this field
    else:
        ###########
        field_id = request.form.get("field_id")
        infos_field_general = db.execute("SELECT * FROM fields_names WHERE field_id = ?", field_id)
        infos_field = db.execute("SELECT * FROM field WHERE field_id = ?", field_id)
        infos_orders_all = db.execute("SELECT * FROM orders WHERE field_id = ? AND stateTEXT = ?", field_id, "Done")
        infos_orders_notPaid = db.execute("SELECT * FROM orders WHERE field_id = ? AND stateTEXT = ? AND paid = ?", field_id, "Done", "Yet")

        try:
            infos_field_general = infos_field_general[0]
            infos_field = infos_field[0]
        except:
            infos_field_general = {'field_id':"NO INFORMATION"}
            infos_field = {'field_id':"NO INFORMATION"}


        # count the TOTAL, money, profit and counts for this field
        money = calculate_money(infos_orders_all)
        counts = len(infos_orders_all)
        profits =  calculate_profit(money)


        # check the field orders by manger
        return render_template("checkOrdersForField.html", infos = infos_field_general, infos2 = infos_field, money = money, counts = counts, profits= profits) # complete




@app.route("/manger/fields/addField", methods=["POST", "GET"])
@login_required
def addfield():
    if request.method == "POST":

        # create random id for field
        field_id = ("@"+ str(randint(99, 999999)) + choice(ascii_letters) + choice(ascii_letters))

        # get information from the manger
        field_name = request.form.get("fieldName")
        price = request.form.getlist("price")
        location = request.form.get("location")
        imgURL = request.form.get("imgURL")
        mapURL = request.form.get("mapURL")
        field_size = request.form.getlist("size")
        times = request.form.getlist("time")
        manger_name = request.form.get("manager_name")
        manger_PhoneNumber = request.form.get("manager_phone_number")


        ## for login
        manger_username = request.form.get("username")
        manger_password = request.form.get("password")
        manger_password_comfirm = request.form.get("password_confirm")

        # to check and save the manger login information
        if login_info(field_id, manger_username, manger_password, manger_password_comfirm) == False:
            print(423)
            return apology("Error in the username/password/confirmation...", 423)

        # check if the information is valid
        # check if the information is provide
        if (not field_name or not price or not location or not imgURL or not mapURL or not field_size or not times or not manger_name or not manger_PhoneNumber):
            print(406)
            return apology("All data is necessery", 406)

        # check if the name is valid
        infos = db.execute("SELECT * FROM fields_names WHERE field_name = ?", field_name)
        if len(infos) == 1:
            infos = infos[0]
            name_db = infos["field_name"]
            if field_name == name_db:
                return apology("The name is not valid", 407)

        # check if the id is valid
        infos = db.execute("SELECT * FROM fields_names WHERE field_id = ?", field_id)
        if len(infos) == 1:
            infos = infos[0]
            field_id_db = infos["field_id"]
            if field_id == field_id_db:
                print(408)
                return apology("ERROR...Please try agin.", 408)

        # check if price is valid
        for pr in price:
            if int(pr) <= 0 or not (str(pr)).isdigit():
                print(409)
                return apology("ERROR..The price is not valid", 409)

        # check if the phone number is valid
        if len(manger_PhoneNumber) != 8 or not manger_PhoneNumber.isdigit():
            print(410)
            return apology("Phone_number is not valid", 410)


        # every thing seem good
        # save information in the database

        try:
            db.execute(
                "INSERT INTO fields_names (field_id, field_name, location_name, imgURL, mapURL, manger_name, manger_PhoneNumber) VALUES (?,?,?,?,?,?,?)",
                field_id,
                field_name,
                location,
                imgURL,
                mapURL,
                manger_name,
                manger_PhoneNumber,
            )
        except:
            return apology("ERROR", 560)

        # get infromation to confirm the user
        infos = db.execute("SELECT * FROM fields_names WHERE field_id = ?", field_id)

        try:
            infos = infos[0]
        except:
            print(411)
            return apology("ERROR...", 411)



        # format the time && the price && the size (".... : ....")
        # format the time as "6-7 am : 7-8 am : ...."
        time_format = ""
        for Time in times:
            if time_format != "":
                time_format = time_format + ":" + Time
            else:
                time_format = Time

        # fomate the size
        size_format = ""
        for i in field_size:

            if size_format != "":
                size_format = size_format + ":" + i
            else:
                size_format = i

        print("size:",size_format)

        # format the price
        price_format = ""
        for i in price:
            if price_format != "":
                price_format = price_format + ":" + i
            else:
                price_format = i


        try:
            db.execute(
                        "INSERT INTO field (field_id, name, time, size, price) VALUES (?,?,?,?,?)",
                        field_id,
                        field_name,
                        time_format,
                        size_format,
                        price_format)
        except:
            return apology("ERROR", 561)

        return render_template("confirm_adding.html", infos=infos, times=times)

    # open the add field page to give the manger the ability of adding new field
    else:
        infos = db.execute("SELECT * FROM field")
        times = [
            "5-6 am",
            "6-7 am",
            "7-8 am",
            "4-5 pm",
            "5-6 pm",
            "6-7 pm",
            "7-8 pm",
            "8-9 pm",
            "9-10 pm",
            "10-11 pm",
            "11-12 pm",
            "12-1 pm",
        ]
        return render_template("add_field.html", sizes= FIELD_SIZE_TYPE, infos=infos, times=times)



@app.route("/delete_field", methods=["POST", "GET"])
@login_required
def deletefield():

    # confirm deleting the field
    if request.method == "GET":
        field_id = request.args.get("field_id")
        return render_template("confirmDeletingField.html", field_id = field_id) 


    # delete the field
    # check if the information is correct
    else:
        field_id = request.form.get("field_id")

        if not field_id:
            return apology("ERROR", 412)
        check_id = db.execute("SELECT * FROM fields_names WHERE field_id = ?", field_id)

        try:
            check_id = check_id[0]["field_id"]
        except:
            return apology("ERROR", 413)

        if check_id != field_id:
            return apology("ERROR", 414)


        # save all information as csv before delete the data
        # continuse


        # EVERY THING SEEM GOOD
        # try to delete all related data
        try:
            db.execute("DELETE FROM fields_names WHERE field_id = ?", field_id)
            db.execute("DELETE FROM orders WHERE field_id = ?", field_id)
            db.execute("DELETE FROM cancel WHERE field_id = ?", field_id)
            db.execute("DELETE FROM mangers WHERE field_id = ?", field_id)
            db.execute("DELETE FROM field WHERE field_id = ?", field_id)
        except:
            return apology("ERROR in Deleting", 567)

        flash("Deleting the field: Done")
        return redirect("/manger/fields/check")



@app.route("/search")
def search():

    field_id = request.args.get("field_id")
    Date = request.args.get("date")
    size = request.args.get("size")

    times = db.execute("SELECT time FROM field WHERE field_id = ?", field_id)
    booked_times = db.execute("SELECT time FROM orders WHERE field_id = ? AND day = ? AND size = ?", field_id, Date, size)

    if times:
        times = (times[0]["time"]).split(":")


    booked_timesWithFormat = []

    if booked_times != []:
        for booked in booked_times:
            booked_timesWithFormat.append(booked["time"])


    available_times = []
    for time in times:
        if time not in booked_timesWithFormat and check_time_up(time, Date):
            available_times.append(time)


    else:
        times = []

    return jsonify(times= available_times)


@app.route("/searchField")
def searchFieldById():

    # get the info from html and add # because you deleted by javascript
    order_id = "#" + request.args.get("order_id")

    if order_id:

        field_infos = db.execute("SELECT * FROM orders WHERE id_order = ? AND stateTEXT =?", order_id, "Booked")
        if field_infos == []:
            return apology("ERROR.. ", 414)
    else:
        field_infos = []

    try:
        field_infos = field_infos[0]
        print(field_infos)
    except:
        field_infos = []


    return render_template("field_by_id.html", info=field_infos)



@app.route("/cancel", methods=["GET", "POST"])
def cancel():

    if request.method == "POST":
        order_id = request.form.get("order_id")

        if order_id:
            field_infos = db.execute("SELECT * FROM orders WHERE id_order = ?", order_id)
            if field_infos == []:
                return apology("ERROR.. ", 416)

        else:
            return apology("ERROR.. ", 418)

        try:
            field_infos = field_infos[0]
        except:
            return apology("ERROR.. ", 417)

        return render_template("cancel.html", info= field_infos)


    else:
        order_id = request.args.get("order_id")
        reason = request.args.get("reason")

        if order_id:
            field_infos = db.execute("SELECT * FROM orders WHERE id_order = ?",order_id)
            print("inos:",field_infos)
            if field_infos == []:
                return apology("ERROR.. ", 416)

        else:
            return apology("ERROR.. ", 418)

        try:
            field_infos = field_infos[0]
        except:
            return apology("ERROR.. ", 417)


        result, phoneNumber = cancel_order_return_state(field_infos, reason)

        if result == True:

            # continue
            text = (f" \n Your order {order_id} is successful canceled")
            st = sendMessage(text, phoneNumber)
            print("TEXT:", text)
            print("nu,ber: ",phoneNumber)
            print("result:", st )

            return render_template("confirm_cancel.html")

        else:
            return apology("ERROR...", 418)




# this for other mangers with will have control of the orders for specefic field.

@app.route("/fieldsMangers", methods = ["GET","POST"])
@login_required2
def fields_mangers():


    # if session.get("user_id") is None:
    #     # check if the user is one of the mangers
    #     return redirect("/Login")



    # for contrel the orders for specific field
    if request.method == "GET":

        print("username:", session.get("user_id"))

        username_ = request.args.get("username_")

        # get the field id from the url
        # field_id = request.args.get("field_id")
        field_id = session.get("user_id")


        # get the information of a field be the field id
        infos = db.execute("SELECT * FROM fields_names WHERE field_id = ?", field_id)

        try:
            field_name = infos[0]["field_name"]
        except:
            return apology("ERROR.. ", 427)


        # this html will show two bottons one for field infos and other for check orders
        return render_template("sub_mangers.html", field_id = field_id, field_name = field_name)


    # enter to field information
    else:
        print("username:", session.get("user_id"))

        field_id = request.form.get("field_id")
        infos_field_general = db.execute("SELECT * FROM fields_names WHERE field_id = ?", field_id)
        infos_field = db.execute("SELECT * FROM field WHERE field_id = ?", field_id)
        infos_orders_all = db.execute("SELECT * FROM orders WHERE field_id = ? AND stateTEXT = ? ORDER BY day, time", field_id, "Done")
        infos_orders_notPaid = db.execute("SELECT * FROM orders WHERE field_id = ? AND stateTEXT = ? AND paid = ? ORDER BY day, time", field_id, "Done", "Yet")


        try:
            infos_field_general = infos_field_general[0]
            infos_field = infos_field[0]
        except:
            infos_field_general = {'field_id':"NO INFORMATION"}
            infos_field = {'field_id':"NO INFORMATION"}



        # count the TOTAL, money, profit and counts for this field
        money = calculate_money(infos_orders_all)
        counts = len(infos_orders_all)
        profits =  calculate_profit(money)

        ## check field infos by the submanger
        return render_template("fieldInfosSubManger.html", infos = infos_field_general, infos2 = infos_field, money = money, counts = counts, profits= profits)




# this for dirct the submangers to (check orders OR check completed orders)
@app.route("/fieldsMangers/DirectSubMangers", methods = ["GET"])
@login_required2
def DirectSub():

    # if session.get("user_id") is None:
    #     # check if the user is one of the mangers
    #     return redirect("/Login")


    # check orders for specific field with (done, check, report) bottons
    if request.method == "GET":
        field_id = request.args.get("field_id")
        field_name = request.args.get("field_name")
        today = date.today()
        infos = db.execute("SELECT * FROM orders WHERE field_id=? AND stateTEXT = ? AND day= ? ORDER BY time", field_id, "Booked", today)

        return render_template("mange_booked_orders.html", infos=infos, from_="not", field_name = field_name)




# this for give statue for order (Done, cancel , report)
@app.route("/fieldsMangers/DirectSubMangers/orderState", methods = ["GET","POST"])
@login_required2
def orderState():

    # if session.get("user_id") is None and session.get("manger_id") is None:
    #     # check if the user is one of the mangers
    #     return redirect("/Login")

    # if get --> user click DONE
    if request.method == "GET":

        order_id = request.args.get("orderCompleted")
        infos = db.execute("SELECT * FROM orders WHERE id_order = ?", order_id)

        try:
            infos = infos[0]
            order_id = infos["id_order"]
            field_id = infos["field_id"]
            field_name = infos["field_name"]

        except:
            return apology("ERROR..", 424)

        # update the order to be completed
        db.execute("UPDATE orders SET stateTEXT = ? WHERE id_order = ?", "Done", order_id)

        flash("completed")

        # because I have to directions which can reatch to this route, we will check from where it direct
        direct_from = request.args.get("from")
        if direct_from == "manger":
            return redirect("/manger/orders/booked")

        return redirect(url_for("DirectSub", field_id = field_id, field_name = field_name))


    # if post --> user click check
    else:

        id_order = request.form.get("orderInfo")
        infos = db.execute("SELECT * FROM orders WHERE id_order = ?", id_order)

        try:
            infos = infos[0]
        except:
            return apology("Sorry an error happen..", 425)

        return render_template("checkInfos.html", infos = infos)



# this for reset the money and the   and the profit
@app.route("/resetTheMoney", methods = ["POST"])
def resetMoney():
    if request.method == "POST":
        field_id = request.form.get("field_id")
        field_orders = db.execute("SELECT * FROM orders WHERE paid = ? AND field_id = ? AND stateTEXT =?", "Yet", field_id, "Done")

        for order in field_orders:
            db.execute("UPDATE orders SET paid = ? WHERE field_id = ? AND stateTEXT =? AND paid = ?", "Paid", field_id, "Done", "Yet")

    flash("reset done")
    field_name = field_orders[0]["field_name"]
    return redirect(url_for("checkSpecifiField", field_id = field_id, field_name = field_name))





@app.route('/update_orders', methods=['GET'])
def update_orders():
    status = request.args.get('status')
    field_id = request.args.get("field_id")
    period = request.args.get("period")
    startDate = request.args.get("start_date")
    endDate = request.args.get("end_date")
    print("period: ",period)



    # the cancel option does not work because the name of colume in orders table different from cancel table
    if status == "Booked" or status == "Done":
        # Fetch orders from the database based on the status and the period
        if period == "all":
            orders = db.execute("SELECT * FROM orders WHERE stateTEXT = ? AND field_id = ? ORDER BY day, time", status, field_id)

        elif period == "specifiData":
            # use strptime() to create date object
            startDate_object = (datetime.strptime(startDate, "%Y-%m-%d")).date()
            endDate_object = (datetime.strptime(endDate, "%Y-%m-%d")).date()


            if startDate_object == endDate_object:
                orders = db.execute("SELECT * FROM orders WHERE stateTEXT = ? AND field_id = ? AND day = ? ORDER BY day, time", status, field_id, startDate_object)

            else:
                orders = []
                while (startDate_object < endDate_object):
                    infoss = db.execute("SELECT * FROM orders WHERE stateTEXT = ? AND field_id = ? AND day = ? ORDER BY day, time", status, field_id, startDate_object)
                    print("infoss: ",infoss)
                    # to ensure it not empty
                    if len(infoss) > 0:
                        orders.append(infoss[0])
                    startDate_object += timedelta(days=1)

                print("orders:",orders)

        # if period ==  toPay
        else:
            orders = db.execute("SELECT * FROM orders WHERE stateTEXT = ? AND field_id = ? AND paid = ? ORDER BY day, time", status, field_id, "Yet")


    # from cancel
    else:
        field_names = db.execute("SELECT * FROM field WHERE field_id = ?", field_id)
        for i in field_names:
            field_name = i["name"]
        orders = db.execute("SELECT * FROM cancel WHERE field_id = ? ORDER BY day, time", field_id + "("+ field_name + ")")


    # Calculate totals
    total = calculate_money(orders)
    profit = calculate_profit(total)
    netMoney = total - profit
    count = len(orders)

    response = {
        'total': total,
        'profit': profit,
        'netMoney': netMoney,
        'count': count,
        'infos': orders
    }

    return jsonify(response)




@app.route("/contact", methods=["GET"])
def contact():
    if request.method == "GET":
        return render_template("contact.html")




if __name__ == "__main__":
    app.run(debug=False, host = '0.0.0.0')
