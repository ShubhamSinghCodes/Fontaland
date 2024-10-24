from werkzeug._compat import text_type
from werkzeug._compat import PY2
import re
from flask import Flask,send_from_directory,render_template,redirect,session,request,abort
import sqlite3
import os
from fontTools.ttLib import TTFont,TTLibError
from PIL import Image, ImageDraw, ImageFont, ImageChops
import datetime

_filename_ascii_strip_re = re.compile(r'[^A-Za-z0-9_.-]')

def secure_filename(filename):
    if isinstance(filename, text_type):
        from unicodedata import normalize

        filename = normalize("NFKD", filename).encode("ascii", "ignore")
        if not PY2:
            filename = filename.decode("ascii")
    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, " ")
    filename = str(_filename_ascii_strip_re.sub("", "_".join(filename.split()))).strip("._")
    return filename

def makehomepage(search=""):
    connection = sqlite_connect("database.db")

    # Create a cursor object
    cursor = connection.cursor()
    if search=="":
        sql_retrieve_file_query = """SELECT name,downloads,cost FROM fonts ORDER BY downloads DESC """
        cursor.execute(sql_retrieve_file_query)
    else:
        sql_retrieve_file_query = """SELECT name,downloads,cost FROM fonts WHERE name LIKE ? ORDER BY downloads DESC """
        cursor.execute(sql_retrieve_file_query, ("%" + search + "%",))

    # Retrieve results in a tuple
    record = cursor.fetchall()

    def remext(name):
        return "".join(name[0].split(".")[:-1])


    def megarchop(string):
        string = string.lower()
        for test in ("-regular","-oblique","-bold","-oblique","- ","-"):
            string = string.removesuffix(test)
        return string

    for font in record:
        try:
            os.remove(font[0])
        except FileNotFoundError:
            pass
        try:
            os.remove(remext(font) + ".png")
        except FileNotFoundError:
            pass
    fontlist = [[remext(font), "/downloadincrement/" + font[0], font[1], font[2], megarchop(remext(font)), font[0]] for font in record]
    sql_retrieve_file_query = f"""SELECT credits,downloaded,uploaded FROM accountinfo WHERE name = ?"""
    try:
        cursor.execute(sql_retrieve_file_query,(session['username'],))
        dboard = cursor.fetchall()[0]
        usname = session['username']
    except KeyError:
        dboard = [0,0,0]
        usname = "please sign in"
    except IndexError:
        dboard = [0, 0, 0]
        usname = "please sign in"
    connection.commit()
    cursor.close()
    return (fontlist,record,dboard,usname)

def convertToBinaryData(filename):
    # Convert digital data to binary format
    with open(filename, 'rb') as file:
        blobData = file.read()
    return blobData


# Create a function to connect to a database with SQLite
def sqlite_connect(db_name):
    """Connect to a database if exists. Create an instance if otherwise.
    Args:
        db_name: The name of the database to connect
    Returns:
        an sqlite3.connection object
    """
    try:
        # Create a connection
        conn = sqlite3.connect(db_name)
    except sqlite3.Error:
        pass
    finally:
        return conn


def insert_file(file_name, db_name, table_name):
    try:
        # Establish a connection
        connection = sqlite_connect(db_name)

        # Create a cursor object
        cursor = connection.cursor()
        def remext(name):
            return "".join(name.split(".")[:-1])

        sqlite_insert_blob_query = f"""INSERT INTO {table_name} (name, data, img, downloads, owner, cost) VALUES (?, ?, ?, 0, ?, 0)"""
        blobdata = convertToBinaryData(file_name)
        imgdata = convertToBinaryData(remext(file_name.split("/")[-1]) + ".png")
        try:
            data_tuple = (file_name.split("/")[-1], blobdata, imgdata, session["username"])
        except KeyError:
            data_tuple = (file_name.split("/")[-1], blobdata, imgdata, "")

        # Execute the query
        cursor.execute(sqlite_insert_blob_query, data_tuple)
        sql_retrieve_file_query = f"""UPDATE accountinfo SET uploaded = uploaded + 1 WHERE name = ?"""
        try:
            cursor.execute(sql_retrieve_file_query, (session['username'],))
        except KeyError:
            cursor.execute(sql_retrieve_file_query, ("nonex",))
        connection.commit()
        cursor.close()
    except sqlite3.Error:
        pass
    finally:
        if connection:
            connection.close()


def write_to_file(binary_code, file_name):
    # Convert binary to a proper file and store in memory
    with open(file_name, 'wb') as file:
        file.write(binary_code)



app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "/home/fontaland/"
app.secret_key = "dsdngvddmv xm,dfjcnxlbddgnfbfngm,hnmd,b.ngfhndnfmbnvmckfgnxdfnsemaefmsmed,adgns,enklsdgjsgjkdskfndfjgkjdbncf,gnx,dgndfjndffffffffffffdjkkkkkkkkkfvnnnnnnnnfmds,zzzzzzbnfjd,ajsdvzjgnvmcvkdksx,ckdkckcksk,dkckxkskskcxlsla,ssd,dkxkaldlxlzladlxllsalsldllsllsdlldslalsllxlaldlxsaksmfkvjsdmvjdjs"


@app.route("/")
def homepage():
    fontlist,record,dboard,usname=makehomepage()
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    return render_template("homepage.html",
                           the_row_titles=("Font name","Download links"),
                           fonts=fontlist,
                           height=180.200 + len(fontlist)*23,
                           loginout=islogged,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname)


@app.route("/upload",methods=["POST"])
def addfile():
    def remext(name):
        return "".join(name.split(".")[:-1])
    file = request.files['font']
    fontlist,record,dboard,usname=makehomepage()
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    try:
        f = TTFont(file)
        f.flavor = None
        f.save(remext(secure_filename(font['name'].getDebugName(4))) + ".ttf")
    except FileNotFoundError:
            return render_template("redirecttohome.html",
                               the_row_titles=("Font name", "Download links"),
                               text="No font file selected :(",
                               fonts=fontlist,
                               height=180.200 + len(fontlist) * 23,
                               loginout=islogged,
                               credits=points,
                               up=up,
                               down=down,
                               username=usname)
    except TTLibError:
        return render_template("redirecttohome.html",
                               the_row_titles=("Font name", "Download links"),
                               text="Not a font file :(",
                               fonts=fontlist,
                               height=180.200 + len(fontlist) * 23,
                               loginout=islogged,
                               credits=points,
                               up=up,
                               down=down,
                               username=usname)
    connection = sqlite_connect("database.db")
    cursor = connection.cursor()
    sql_retrieve_file_query = f"""SELECT name FROM fonts WHERE name = ?"""
    cursor.execute(sql_retrieve_file_query, (font['name'].getDebugName(4),))
    result = cursor.fetchall()
    if len(result) == 1:
        return render_template("redirecttohome.html",
                               the_row_titles=("Font name", "Download links"),
                               text="Font already exists :(",
                               fonts=fontlist,
                               height=180.200 + len(fontlist) * 23,
                               loginout=islogged,
                               credits=points,
                               up=up,
                               down=down,
                               username=usname)
    try:
        font = ImageFont.truetype(remext(secure_filename(font['name'].getDebugName(4))) + ".ttf", 224, encoding='utf-8')
    except OSError:
        os.remove(".ttf")
        return render_template("redirecttohome.html",
                               the_row_titles=("Font name", "Download links"),
                               text="No font file selected :(",
                               fonts=fontlist,
                               height=180.200 + len(fontlist) * 23,
                               loginout=islogged,
                               credits=points,
                               up=up,
                               down=down,
                               username=usname)
    temp = 0
    for ch in remext(secure_filename(font['name'].getDebugName(4))):
        temp += font.getsize(ch)[0]
    W, H = (temp, 224)
    image = Image.new("RGB", (W, H), "black")
    draw = ImageDraw.Draw(image)
    offset_w, offset_h = font.getoffset(remext(secure_filename(font['name'].getDebugName(4))))
    w, h = draw.textsize(remext(secure_filename(font['name'].getDebugName(4))), font=font)
    pos = ((W - w - offset_w) / 2, (H - h - offset_h) / 2)
    draw.text(pos, remext(secure_filename(font['name'].getDebugName(4))), "white", font=font)
    createtemp = open(remext(secure_filename(font['name'].getDebugName(4))) + ".png","w")
    createtemp.close()
    image = ImageChops.invert(image)
    image.save(remext(secure_filename(font['name'].getDebugName(4))) + ".png")
    insert_file(remext(secure_filename(font['name'].getDebugName(4))) + ".ttf", "database.db", "fonts")
    sql_retrieve_file_query = f"""UPDATE accountinfo SET credits = credits + 15 WHERE name = ?"""
    try:
        cursor.execute(sql_retrieve_file_query, (session['username'],))
    except KeyError:
        cursor.execute(sql_retrieve_file_query, ("nonex",))
    connection.commit()
    connection.close()
    return render_template("redirecttohome.html",
                           the_row_titles=("Font name", "Download links"),
                           text="Font uploaded!",
                           fonts=fontlist,
                           height=180.200 + len(fontlist)*23,
                           loginout=islogged,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname)


@app.route("/download/<filename>")
def downloadfile(filename):
    conn = sqlite_connect("database.db")
    cur = conn.cursor()
    sql_retrieve_file_query = f"""SELECT data FROM fonts WHERE name = ?"""
    cur.execute(sql_retrieve_file_query,(filename,))
    rec = cur.fetchall()
    write_to_file(rec[0][0],filename)
    return send_from_directory(directory=app.config["UPLOAD_FOLDER"], path=app.config["UPLOAD_FOLDER"], filename=filename, as_attachment=True)

@app.route("/downloadincrement/<filename>")
def downloadincrfile(filename):
    connection = sqlite_connect("database.db")
    cursor = connection.cursor()
    sql_retrieve_file_query = """SELECT owner,cost FROM fonts WHERE name = ?"""
    cursor.execute(sql_retrieve_file_query, (filename,))
    owner, cost = cursor.fetchall()[0]
    sql_retrieve_file_query = """SELECT credits FROM accountinfo WHERE name = ?"""
    try:
        cursor.execute(sql_retrieve_file_query, (session['username'],))
        credits = cursor.fetchall()
        print(credits)
        credits = credits[0]
    except (KeyError,IndexError):
        if cost == 0:
            connection.commit()
            connection.close()
            fontlist, record, dboard, usname = makehomepage()
            points = dboard[0]
            down = dboard[1]
            up = dboard[2]
            try:
                islogged = "logout" if session["loggedin"] else "login"
            except KeyError:
                islogged = "login"
            return render_template("redirectdownload.html",
                                   text="please wait,it will download after exactly two second(only!).After that, you can click the back button.",
                                   url=filename,
                                   fonts=fontlist,
                                   loginout=islogged,
                                   height=180.200 + len(fontlist) * 23,
                                   credits=points,
                                   up=up,
                                   down=down,
                                   username=usname,
                                   the_row_titles=("Font name", "Download links"))
        else:
            connection.commit()
            connection.close()
            fontlist, record, dboard, usname = makehomepage()
            points = dboard[0]
            down = dboard[1]
            up = dboard[2]
            try:
                islogged = "logout" if session["loggedin"] else "login"
            except KeyError:
                islogged = "login"
            return render_template("redirecttohome.html",
                                   text="Please sign in.",
                                   url=filename,
                                   fonts=fontlist,
                                   loginout=islogged,
                                   height=180.200 + len(fontlist) * 23,
                                   credits=points,
                                   up=up,
                                   down=down,
                                   username=usname,
                                   the_row_titles=("Font name", "Download links"))
    credits = credits[0]
    if cost > credits:
        connection.commit()
        connection.close()
        fontlist, record, dboard, usname = makehomepage()
        points = dboard[0]
        down = dboard[1]
        up = dboard[2]
        try:
            islogged = "logout" if session["loggedin"] else "login"
        except KeyError:
            islogged = "login"
        return render_template("redirecttohome.html",
                               text="Not enough credits.",
                               url=filename,
                               fonts=fontlist,
                               loginout=islogged,
                               height=180.200 + len(fontlist) * 23,
                               credits=points,
                               up=up,
                               down=down,
                               username=usname,
                               the_row_titles=("Font name", "Download links"))
    sql_retrieve_file_query = f"""UPDATE fonts SET downloads = downloads + 1 WHERE name = ?"""
    cursor.execute(sql_retrieve_file_query, (filename,))
    sql_retrieve_file_query = f"""UPDATE accountinfo SET downloaded = downloaded + 1 WHERE name = ?"""
    try:
        cursor.execute(sql_retrieve_file_query, (session['username'],))
    except KeyError:
        cursor.execute(sql_retrieve_file_query, ("nonex",))
    sql_retrieve_file_query = f"""UPDATE accountinfo SET credits = credits + 5 WHERE name = ?"""
    cursor.execute(sql_retrieve_file_query, (owner,))
    sql_retrieve_file_query = f"""UPDATE accountinfo SET credits = credits - ? WHERE name = ?"""
    try:
        cursor.execute(sql_retrieve_file_query, (cost, session['username'],))
    except KeyError:
        pass

    connection.commit()
    connection.close()
    fontlist,record,dboard,usname=makehomepage()
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    return render_template("redirectdownload.html",
                           text="please wait,it will download after exactly two second(only!).After that, you can click the back button.",
                           url=filename,
                           fonts=fontlist,
                           loginout=islogged,
                           height=180.200 + len(fontlist)*23,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname,
                           the_row_titles=("Font name","Download links"))

@app.route("/downloadincrement/static/hf.css")
@app.route("/monetize/<ignore>/static/hf.css")
def correctcss(ignore=None):
    return redirect("/static/hf.css")

@app.route("/login")
def login():
    fontlist, record, dboard, usname = makehomepage()
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    return render_template("login.html",
                           loginout=islogged,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname)

@app.route("/create")
def create():
    fontlist,record,dboard,usname=makehomepage()
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    return render_template("create.html",
                           loginout=islogged,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname)

@app.route("/dologin",methods=["POST"])
def dologin():
    name=request.form["usname"]
    pswd = request.form["psswd"]
    connection = sqlite_connect("database.db")
    cursor = connection.cursor()
    sql_retrieve_file_query = f"""SELECT name,password FROM accountinfo WHERE name = ?"""
    cursor.execute(sql_retrieve_file_query, (name,))
    result = cursor.fetchall()
    try:
        result = result[0]
    except IndexError:
        connection.commit()
        connection.close()
        fontlist,record,dboard,usname=makehomepage()
        points = dboard[0]
        down = dboard[1]
        up = dboard[2]
        try:
            islogged = "logout" if session["loggedin"] else "login"
        except KeyError:
            islogged = "login"
        return render_template("redirecttologin.html",
                               text="No such account",
                               loginout=islogged,
                               height=180.200 + len(fontlist)*23,
                               credits=points,
                               up=up,
                               down=down,
                               username=usname)
    if result[1] != pswd:
        connection.commit()
        connection.close()
        fontlist,record,dboard,usname=makehomepage()
        points = dboard[0]
        down = dboard[1]
        up = dboard[2]
        try:
            islogged = "logout" if session["loggedin"] else "login"
        except KeyError:
            islogged = "login"
        return render_template("redirecttologin.html",
                               text="Wrong password",
                               loginout=islogged,
                               height=180.200 + len(fontlist)*23,
                               credits=points,
                               up=up,
                               down=down,
                               username=usname)
    connection.commit()
    connection.close()
    session['loggedin'] = True
    session['username'] = name
    fontlist,record,dboard,usname=makehomepage()
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    return render_template("redirecttohome.html",
                           fonts=fontlist,
                           text="You have logged in!",
                           loginout=islogged,
                           height=180.200 + len(fontlist)*23,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname)

@app.route("/docreate",methods=["POST"])
def docreate():
    name=request.form["usname"]
    pswd = request.form["psswd"]
    confirmpswd = request.form["conpsswd"]
    connection = sqlite_connect("database.db")
    cursor = connection.cursor()
    sql_retrieve_file_query = f"""SELECT name FROM accountinfo WHERE name = ?"""
    cursor.execute(sql_retrieve_file_query, (name,))
    result = cursor.fetchall()
    if len(result) == 1:
        connection.commit()
        connection.close()
        fontlist,record,dboard,usname=makehomepage()
        points = dboard[0]
        down = dboard[1]
        up = dboard[2]
        try:
            islogged = "logout" if session["loggedin"] else "login"
        except KeyError:
            islogged = "login"
        return render_template("redirecttocreate.html",
                               text="Username already taken",
                               loginout=islogged,
                               height=180.200 + len(fontlist)*23,
                               credits=points,
                               up=up,
                               down=down,
                               username=usname)
    if confirmpswd != pswd:
        connection.commit()
        connection.close()
        fontlist,record,dboard,usname=makehomepage()
        points = dboard[0]
        down = dboard[1]
        up = dboard[2]
        try:
            islogged = "logout" if session["loggedin"] else "login"
        except KeyError:
            islogged = "login"
        return render_template("redirecttocreate.html",
                               text="passwords don't match",
                               loginout=islogged,
                               height=180.200 + len(fontlist)*23,
                               credits=points,
                               up=up,
                               down=down,
                               username=usname)
    sql_retrieve_file_query = """INSERT INTO accountinfo (name, password, credits, downloaded, uploaded) VALUES (?, ?, 50, 0, 0)"""
    cursor.execute(sql_retrieve_file_query,(name,pswd))
    connection.commit()
    connection.close()
    session['loggedin'] = True
    fontlist,record,dboard,usname=makehomepage()
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    return render_template("redirecttologin.html",
                           text="You have made an account! Now you can login with the username and password.",
                           loginout=islogged,
                           height=180.200 + len(fontlist)*23,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname)


@app.route("/logout")
def logout():
    session['loggedin'] = False
    session['username'] = ""
    fontlist,record,dboard,usname=makehomepage()
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    return render_template("redirecttohome.html",
                           fonts=fontlist,
                           text="You have logged out!",
                           height=180.200 + len(fontlist)*23,
                           loginout=islogged,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname,
                           the_row_titles=("Font name","Download links"))

@app.route("/search",methods=["POST"])
def dosearch():
    fontlist, record, dboard, usname = makehomepage(request.form["search"])
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    return render_template("homepage.html",
                           fonts=fontlist,
                           height=180.200 + len(fontlist) * 23,
                           loginout=islogged,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname,
                           the_row_titles=("Font name","Download links"))


@app.route("/monetize/<fontname>/")
def money(fontname):
    connection = sqlite_connect("database.db")
    cursor = connection.cursor()
    update_query = """UPDATE fonts SET cost = cost + 5 WHERE name LIKE ?"""
    cursor.execute(update_query,(str(fontname),))
    connection.commit()
    connection.close()
    fontlist, record, dboard, usname = makehomepage()
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    return render_template("redirecttohome.html",
                           fonts=fontlist,
                           text = "done",
                           height=180.200 + len(fontlist) * 23,
                           loginout=islogged,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname,
                           the_row_titles=("Font name", "Download links"))



@app.route("/team")
def homepageteam():
    fontlist,record,dboard,usname=makehomepage()
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    try:
        if session["username"] != "FontaLandTeam":
            abort(404)
    except KeyError:
        abort(404)
    for filename in record:
        try:
            os.remove(filename[0])
        except FileNotFoundError:
            pass
    return render_template("homepageTeam.html",
                           the_row_titles=("Font name","Download links"),
                           fonts=fontlist,
                           height=180.200 + len(fontlist)*23,
                           loginout=islogged,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname)


@app.route("/preview/<fname>")
def prev(fname):
    def remext(name):
        return "".join(name.split(".")[:-1])
    conn = sqlite_connect("database.db")
    cur = conn.cursor()
    sql_retrieve_file_query = f"""SELECT img FROM fonts WHERE name = ?"""
    cur.execute(sql_retrieve_file_query,(remext(fname) + ".ttf",))
    rec = cur.fetchall()
    write_to_file(rec[0][0],fname)
    return send_from_directory(directory=app.config["UPLOAD_FOLDER"], path=app.config["UPLOAD_FOLDER"], filename=fname,)

@app.route("/how2/<fname>")
def how2(fname):
    return send_from_directory(directory="/home/fontaland/mysite/FontalandHelpFrames/", path="/home/fontaland/mysite/FontalandHelpFrames/", filename=fname,)

@app.route("/HowToUseSite")
def hhwtosite():
    return render_template("FontalandHelpFrames.html")

@app.errorhandler(404)
def handle404(e):
    fontlist,record,dboard,usname=makehomepage()
    points = dboard[0]
    down = dboard[1]
    up = dboard[2]
    try:
        islogged = "logout" if session["loggedin"] else "login"
    except KeyError:
        islogged = "login"
    return render_template("redirecttohome.html",
                           text="404.Thats an error.( The page does not exist. If you entered the URL manually please check your spelling and try again.)",
                           the_row_titles=("Font name","Download links"),
                           fonts=fontlist,
                           height=180.200 + len(fontlist)*23,
                           loginout=islogged,
                           credits=points,
                           up=up,
                           down=down,
                           username=usname)

@app.route("/miscellaneous/<lol>")
@app.route("/misc/<lol>")
@app.route("/easter")
def joke(lol=None):
    return render_template("rickroll.html",page=lol)


#Table creation code
try:
    connection = sqlite_connect("database.db")
    cursor = connection.cursor()
    sql_retrieve_file_query = "CREATE TABLE fonts (name TEXT NOT NULL, data BLOB NOT NULL, img BLOB NOT NULL, downloads INT NOT NULL, owner TEXT NOT NULL, cost INT NOT NULL);"
    cursor.execute(sql_retrieve_file_query)
    sql_retrieve_file_query = "CREATE TABLE accountinfo (name TEXT NOT NULL, password TEXT NOT NULL, credits INT NOT NULL, downloaded INT NOT NULL, uploaded INT NOT NULL);"
    cursor.execute(sql_retrieve_file_query)
except:
    pass

if __name__ == "__main__":
    app.run(debug=True)
