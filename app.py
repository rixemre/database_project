import pymysql
import pymysql.cursors
from flask import Flask, render_template, request, redirect, url_for, g, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# ======================================================
# RUN FLASK APP
# ======================================================
app = Flask(__name__)
app.secret_key = 's3cr3t_y0u_d0nt_kn0w'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ======================================================
# DATABASE CONNECTION SETTINGS
# ======================================================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '578531'
app.config['MYSQL_DB'] = 'bannerlord'
app.config['MYSQL_PORT'] = 3306

# ======================================================
# CONNECTION FUNCTIONS WITH DBAPI2 DRIVER
# ======================================================
def get_db():
    """Opens a new database connection if one hasn't been established yet."""
    if 'db' not in g:
        try:
            g.db = pymysql.connect(
                host=app.config['MYSQL_HOST'],
                user=app.config['MYSQL_USER'],
                password=app.config['MYSQL_PASSWORD'],
                database=app.config['MYSQL_DB'],
                port=app.config['MYSQL_PORT'],
                cursorclass=pymysql.cursors.DictCursor
            )
        except pymysql.Error as err:
            print(f"Database connection error: {err}")
            g.db = None
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# ==========
#(HELPERS)
# ==========
def safe_int(key):
    """Safely retrieves a numeric value from form data, returning None (SQL NULL) if empty."""
    val = request.form.get(key)
    return val if val else None

def fetch_cultures(cursor):
    """Fetches the list of cultures."""
    cursor.execute("SELECT Culture_Type_ID, Culture_Type_Name FROM Culture_Types ORDER BY Culture_Type_Name;")
    return cursor.fetchall()

def fetch_materials(cursor):
    """Fetches unique materials from Armors table for the dropdown."""
    cursor.execute("SELECT DISTINCT Material FROM Armors WHERE Material IS NOT NULL AND Material <> '' ORDER BY Material;")
    return cursor.fetchall()

def fetch_mount_types(cursor):
    """Fetches unique mount types."""
    cursor.execute("SELECT DISTINCT Mount_Type FROM Mounts WHERE Mount_Type IS NOT NULL ORDER BY Mount_Type;")
    return cursor.fetchall()

def fetch_item_types(cursor):
    """Fetches the list of item types."""
    cursor.execute("SELECT Item_Type_ID, Item_Type_Name FROM Item_Types ORDER BY Item_Type_Name;")
    return cursor.fetchall()

def get_item_type_id(cursor, type_name):
    """Retrieves Item_Type_ID based on the type name, with hardcoded fallbacks."""
    cursor.execute("SELECT Item_Type_ID FROM Item_Types WHERE Item_Type_Name = %s", (type_name,))
    result = cursor.fetchone()
    if result:
        return result['Item_Type_ID']
    # Fallbacks based on common database setup
    if type_name == 'Armor': return 3
    if type_name == 'Melee Weapon': return 1 
    if type_name == 'Ranged Weapon': return 2
    if type_name == 'Shield': return 4
    if type_name == 'Mount': return 5
    return None

# ======================================================
# BASIC ADMINISTRATION SYSTEM
# ======================================================
class AdminUser(UserMixin):
    id = "admin"
    username = "Kingdom Admin"

@login_manager.user_loader
def load_user(user_id):
    if user_id == "admin":
        return AdminUser()
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "1234":
            login_user(AdminUser())
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Wrong password or username!")
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

class AdminUser(UserMixin):
    def __init__(self):
        self.id = "admin"
        self.username = "Kingdom Admin"
        self.is_admin = True  # HTML'deki {% if current_user.is_admin %} buraya bakar

# =================================
# 1. MAIN PAGE AND ITEMS DASHBOARD
# =================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/items')
def items_dashboard():
    return render_template('items/dashboard.html')

# ===========
# 2. (All Items)
# ===========
@app.route('/all_items')
def all_items_page():
    """Lists all items with ADVANCED filtering capabilities."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        
        search_name = request.args.get('search_name')
        search_culture = request.args.get('search_culture')
        search_type = request.args.get('search_type')
        
        # Yeni Filtreler
        min_w = request.args.get('min_weight')
        max_w = request.args.get('max_weight')
        is_civilian = request.args.get('is_civilian')
        
        base_query = """
        SELECT
            I.Item_ID, I.Item_Name, I.Weight, I.Civilian,
            C.Culture_Type_Name AS Culture,
            IT.Item_Type_Name AS Item_Type,
            IT.Item_Type_ID  -- Bunu ekledik ki HTML'de kontrol edebilelim
        FROM Items AS I
        JOIN Culture_Types AS C ON I.Culture_ID = C.Culture_Type_ID
        JOIN Item_Types AS IT ON I.Item_Type_ID = IT.Item_Type_ID
        """
        
        where_clauses = []
        params = []
        
        if search_name:
            where_clauses.append("I.Item_Name LIKE %s")
            params.append(f"%{search_name}%")
            
        if search_culture:
            where_clauses.append("I.Culture_ID = %s")
            params.append(search_culture)
            
        if search_type:
            where_clauses.append("I.Item_Type_ID = %s")
            params.append(search_type)

        # Yeni Filtre Mantıkları
        if min_w:
            where_clauses.append("I.Weight >= %s")
            params.append(min_w)
            
        if max_w:
            where_clauses.append("I.Weight <= %s")
            params.append(max_w)
            
        if is_civilian and is_civilian != "":
            where_clauses.append("I.Civilian = %s")
            params.append(is_civilian)
            
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)
            
        base_query += " ORDER BY I.Item_Name;"
        
        cursor.execute(base_query, tuple(params))
        all_items = cursor.fetchall()
        
        cultures = fetch_cultures(cursor)
        item_types = fetch_item_types(cursor)
        
        return render_template('items/all_items.html', 
                               all_items=all_items, 
                               cultures=cultures, 
                               item_types=item_types)
        
    except pymysql.Error as err:
        return f"Query error (READ - All Items): {err}", 500
    finally:
        if cursor: cursor.close()

# ================
# 3. (ARMORS)(CRUD)
# ================
@app.route('/armors')
def armors_page():
    db = get_db()
    cursor = db.cursor()

    search_name = request.args.get('search_name')
    search_culture = request.args.get('search_culture')
    search_material = request.args.get('search_material')
    is_civilian = request.args.get('is_civilian')
    
    min_w = request.args.get('min_weight'); max_w = request.args.get('max_weight')
    min_body = request.args.get('min_body'); max_body = request.args.get('max_body')
    min_head = request.args.get('min_head'); max_head = request.args.get('max_head')
    min_leg = request.args.get('min_leg'); max_leg = request.args.get('max_leg')
    min_arm = request.args.get('min_arm'); max_arm = request.args.get('max_arm')
    min_tot = request.args.get('min_total'); max_tot = request.args.get('max_total')

    base_query = """
    SELECT I.Item_ID, I.Item_Name, I.Weight, I.Civilian,
           C.Culture_Type_Name AS Culture, IT.Item_Type_Name AS Item_Type,
           A.Body_Armor_Rating, A.Leg_Armor_Rating, A.Head_Armor_Rating, A.Arm_Armor_Rating,
           A.Armor_Rating, A.Total_Armor_Rating, A.Material
    FROM Items AS I
    JOIN Armors AS A ON I.Item_ID = A.Item_ID
    JOIN Culture_Types AS C ON I.Culture_ID = C.Culture_Type_ID
    JOIN Item_Types AS IT ON I.Item_Type_ID = IT.Item_Type_ID
    """
    
    where = []
    params = []
    
    if search_name: where.append("I.Item_Name LIKE %s"); params.append(f"%{search_name}%")
    if search_culture: where.append("I.Culture_ID = %s"); params.append(search_culture)
    if search_material: where.append("A.Material = %s"); params.append(search_material)
    if is_civilian: where.append("I.Civilian = %s"); params.append(is_civilian)

    # Numeric Filters
    if min_w: where.append("I.Weight >= %s"); params.append(min_w)
    if max_w: where.append("I.Weight <= %s"); params.append(max_w)
    
    if min_body: where.append("A.Body_Armor_Rating >= %s"); params.append(min_body)
    if max_body: where.append("A.Body_Armor_Rating <= %s"); params.append(max_body)
    
    if min_head: where.append("A.Head_Armor_Rating >= %s"); params.append(min_head)
    if max_head: where.append("A.Head_Armor_Rating <= %s"); params.append(max_head)
    
    if min_leg: where.append("A.Leg_Armor_Rating >= %s"); params.append(min_leg)
    if max_leg: where.append("A.Leg_Armor_Rating <= %s"); params.append(max_leg)
    
    if min_arm: where.append("A.Arm_Armor_Rating >= %s"); params.append(min_arm)
    if max_arm: where.append("A.Arm_Armor_Rating <= %s"); params.append(max_arm)

    if min_tot: where.append("A.Total_Armor_Rating >= %s"); params.append(min_tot)
    if max_tot: where.append("A.Total_Armor_Rating <= %s"); params.append(max_tot)

    if where: base_query += " WHERE " + " AND ".join(where)
    base_query += " ORDER BY I.Item_Name;"
    
    cursor.execute(base_query, tuple(params))
    armors = cursor.fetchall()
    cultures = fetch_cultures(cursor)
    materials = fetch_materials(cursor)
    cursor.close()
    return render_template('items/armors.html', armors=armors, cultures=cultures, materials=materials)

@app.route('/add_armor', methods=['POST'])
@login_required
def add_armor():
    """Adds a new armor item (Items + Armors)."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        
        item_name = request.form['item_name']
        weight = request.form['weight']
        culture_id = request.form['culture_id']
        civilian = 'Yes' if 'civilian' in request.form else 'No'
        item_type_id = get_item_type_id(cursor, 'Armor')
        
        sql_items = "INSERT INTO Items (Item_Type_ID, Culture_ID, Item_Name, Weight, Civilian) VALUES (%s, %s, %s, %s, %s);"
        val_items = (item_type_id, culture_id, item_name, weight, civilian)
        cursor.execute(sql_items, val_items)
        
        new_item_id = cursor.lastrowid
        
        body_armor = request.form['body_armor']
        leg_armor = request.form['leg_armor']
        head_armor = request.form['head_armor']
        arm_armor = request.form['arm_armor']
        armor_rating = request.form['armor_rating']
        total_armor_rating = request.form['total_armor_rating']
        material = request.form['material']
        merchandise = request.form['merchandise']

        sql_armors = """
        INSERT INTO Armors (Item_ID, Leg_Armor_Rating, Body_Armor_Rating, Arm_Armor_Rating, 
                          Head_Armor_Rating, Armor_Rating, Total_Armor_Rating, Material, Merchandise)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        val_armors = (new_item_id, leg_armor, body_armor, arm_armor, 
                      head_armor, armor_rating, total_armor_rating, material, merchandise)
        cursor.execute(sql_armors, val_armors)
        
        db.commit()
        
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (CREATE - Armor): {err}", 500
    finally:
        if cursor: cursor.close()
            
    return redirect(url_for('armors_page'))

@app.route('/update_page/<int:item_id>')
@login_required
def update_page(item_id):
    """Renders the update form for an armor item."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor() 
        query = "SELECT I.*, A.* FROM Items AS I JOIN Armors AS A ON I.Item_ID = A.Item_ID WHERE I.Item_ID = %s;"
        cursor.execute(query, (item_id,))
        armor = cursor.fetchone()
        
        if armor is None: return "Armor not found", 404
            
        cultures = fetch_cultures(cursor)
            
        return render_template('items/update_armor.html', armor=armor, cultures=cultures, item_id=item_id)
        
    except pymysql.Error as err:
        return f"Query error (UPDATE PAGE - Armor): {err}", 500
    finally:
        if cursor: cursor.close()

@app.route('/update_armor/<int:item_id>', methods=['POST'])
@login_required
def update_armor(item_id):
    """Updates an existing armor item."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        

        item_name = request.form['item_name']
        weight = request.form['weight']
        culture_id = request.form['culture_id']
        civilian = 'Yes' if 'civilian' in request.form else 'No'

        body_armor = request.form['body_armor']
        leg_armor = request.form['leg_armor']
        head_armor = request.form['head_armor']
        arm_armor = request.form['arm_armor']
        material = request.form['material']
        
        sql_items = "UPDATE Items SET Item_Name = %s, Weight = %s, Culture_ID = %s, Civilian = %s WHERE Item_ID = %s;"
        val_items = (item_name, weight, culture_id, civilian, item_id)
        cursor.execute(sql_items, val_items)
        

        sql_armors = """
        UPDATE Armors 
        SET Body_Armor_Rating = %s, Leg_Armor_Rating = %s, Head_Armor_Rating = %s, 
            Arm_Armor_Rating = %s, Material = %s
        WHERE Item_ID = %s;
        """
        val_armors = (body_armor, leg_armor, head_armor, arm_armor, material, item_id)
        cursor.execute(sql_armors, val_armors)
        
        db.commit()
        
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (UPDATE - Armor): {err}", 500
    finally:
        if cursor: cursor.close()
            
    return redirect(url_for('armors_page'))
    
@app.route('/delete_armor/<int:item_id>', methods=['POST'])
@login_required
def delete_armor(item_id):
    """Deletes an armor item."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM Armors WHERE Item_ID = %s;", (item_id,))
        cursor.execute("DELETE FROM Items WHERE Item_ID = %s;", (item_id,))
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (DELETE - Armor): {err}", 500
    finally:
        if cursor: cursor.close()
            
    return redirect(url_for('armors_page'))

# =======================
# 4. (MELEE_WEAPONS)(CRUD)
# =======================
@app.route('/melee_weapons')
def melee_weapons_page():
    db = get_db()
    cursor = db.cursor()
    
    search_name = request.args.get('search_name')
    search_culture = request.args.get('search_culture')
    is_civilian = request.args.get('is_civilian')
    
    # Ranges
    min_w = request.args.get('min_weight'); max_w = request.args.get('max_weight')
    min_tier = request.args.get('min_tier'); max_tier = request.args.get('max_tier')
    min_swing_d = request.args.get('min_swing_d'); max_swing_d = request.args.get('max_swing_d')
    min_swing_s = request.args.get('min_swing_s'); max_swing_s = request.args.get('max_swing_s')
    min_thrust_d = request.args.get('min_thrust_d'); max_thrust_d = request.args.get('max_thrust_d')
    min_thrust_s = request.args.get('min_thrust_s'); max_thrust_s = request.args.get('max_thrust_s')
    min_len = request.args.get('min_len'); max_len = request.args.get('max_len')
    min_hnd = request.args.get('min_hnd'); max_hnd = request.args.get('max_hnd')

    base_query = """
    SELECT I.Item_ID, I.Item_Name, I.Weight, I.Civilian,
           C.Culture_Type_Name AS Culture, IT.Item_Type_Name AS Item_Type,
           MW.Tier, MW.Length, MW.Handling, MW.Swing_Speed, MW.Swing_Damage, MW.Thrust_Speed, MW.Thrust_Damage
    FROM Items AS I
    JOIN Melee_Weapons AS MW ON I.Item_ID = MW.Item_ID
    JOIN Culture_Types AS C ON I.Culture_ID = C.Culture_Type_ID
    JOIN Item_Types AS IT ON I.Item_Type_ID = IT.Item_Type_ID
    """
    
    where = []
    params = []
    
    if search_name: where.append("I.Item_Name LIKE %s"); params.append(f"%{search_name}%")
    if search_culture: where.append("I.Culture_ID = %s"); params.append(search_culture)
    if is_civilian: where.append("I.Civilian = %s"); params.append(is_civilian)

    if min_w: where.append("I.Weight >= %s"); params.append(min_w)
    if max_w: where.append("I.Weight <= %s"); params.append(max_w)

    if min_tier: where.append("MW.Tier >= %s"); params.append(min_tier)
    if max_tier: where.append("MW.Tier <= %s"); params.append(max_tier)
    
    if min_swing_d: where.append("MW.Swing_Damage >= %s"); params.append(min_swing_d)
    if max_swing_d: where.append("MW.Swing_Damage <= %s"); params.append(max_swing_d)
    
    if min_swing_s: where.append("MW.Swing_Speed >= %s"); params.append(min_swing_s)
    if max_swing_s: where.append("MW.Swing_Speed <= %s"); params.append(max_swing_s)

    if min_thrust_d: where.append("MW.Thrust_Damage >= %s"); params.append(min_thrust_d)
    if max_thrust_d: where.append("MW.Thrust_Damage <= %s"); params.append(max_thrust_d)
    
    if min_thrust_s: where.append("MW.Thrust_Speed >= %s"); params.append(min_thrust_s)
    if max_thrust_s: where.append("MW.Thrust_Speed <= %s"); params.append(max_thrust_s)
    
    if min_len: where.append("MW.Length >= %s"); params.append(min_len)
    if max_len: where.append("MW.Length <= %s"); params.append(max_len)
    
    if min_hnd: where.append("MW.Handling >= %s"); params.append(min_hnd)
    if max_hnd: where.append("MW.Handling <= %s"); params.append(max_hnd)

    if where: base_query += " WHERE " + " AND ".join(where)
    base_query += " ORDER BY I.Item_Name;"
    
    cursor.execute(base_query, tuple(params))
    melee_weapons = cursor.fetchall()
    cultures = fetch_cultures(cursor)
    cursor.close()
    return render_template('items/melee_weapons.html', melee_weapons=melee_weapons, cultures=cultures)
        
@app.route('/add_melee_weapon', methods=['POST'])
@login_required
def add_melee_weapon():
    """Adds a new melee weapon (Items + Melee_Weapons)."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        

        item_name = request.form['item_name']
        weight = request.form['weight']
        culture_id = request.form['culture_id']
        civilian = 'Yes' if 'civilian' in request.form else 'No'
        item_type_id = get_item_type_id(cursor, 'Melee Weapon')
        
        sql_items = "INSERT INTO Items (Item_Type_ID, Culture_ID, Item_Name, Weight, Civilian) VALUES (%s, %s, %s, %s, %s);"
        val_items = (item_type_id, culture_id, item_name, weight, civilian)
        cursor.execute(sql_items, val_items)
        new_item_id = cursor.lastrowid
        
        val_melee = (new_item_id, safe_int('Tier'), safe_int('Swing_Speed'), safe_int('Swing_Damage'),
                     safe_int('Thrust_Speed'), safe_int('Thrust_Damage'), safe_int('Length'), safe_int('Handling'))
        
        sql_melee = """
        INSERT INTO Melee_Weapons (Item_ID, Tier, Swing_Speed, Swing_Damage, Thrust_Speed, Thrust_Damage, Length, Handling)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        cursor.execute(sql_melee, val_melee)
        db.commit()
        
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (CREATE - Melee): {err}", 500
    finally:
        if cursor: cursor.close()
        
    return redirect(url_for('melee_weapons_page'))

@app.route('/update_page_melee/<int:item_id>')
@login_required
def update_page_melee(item_id):
    """Renders the update form for a melee weapon."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        query = "SELECT I.*, MW.* FROM Items AS I JOIN Melee_Weapons AS MW ON I.Item_ID = MW.Item_ID WHERE I.Item_ID = %s;"
        cursor.execute(query, (item_id,))
        weapon = cursor.fetchone()
        
        if weapon is None: return "Weapon not found", 404
        
        cultures = fetch_cultures(cursor)
        return render_template('items/update_melee_weapons.html', weapon=weapon, cultures=cultures, item_id=item_id)
    except pymysql.Error as err:
        return f"Query error (UPDATE PAGE - Melee): {err}", 500
    finally:
        if cursor: cursor.close()

@app.route('/update_melee_weapon/<int:item_id>', methods=['POST'])
@login_required
def update_melee_weapon(item_id):
    """Updates an existing melee weapon."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        
        item_name = request.form['item_name']
        weight = request.form['weight']
        culture_id = request.form['culture_id']
        civilian = 'Yes' if 'civilian' in request.form else 'No'
        sql_items = "UPDATE Items SET Item_Name = %s, Weight = %s, Culture_ID = %s, Civilian = %s WHERE Item_ID = %s;"
        val_items = (item_name, weight, culture_id, civilian, item_id)
        cursor.execute(sql_items, val_items)
        
        val_melee = (safe_int('Tier'), safe_int('Swing_Speed'), safe_int('Swing_Damage'),
                     safe_int('Thrust_Speed'), safe_int('Thrust_Damage'), safe_int('Length'), 
                     safe_int('Handling'), item_id)
        
        sql_melee = """
        UPDATE Melee_Weapons 
        SET Tier = %s, Swing_Speed = %s, Swing_Damage = %s, Thrust_Speed = %s, 
            Thrust_Damage = %s, Length = %s, Handling = %s
        WHERE Item_ID = %s;
        """
        cursor.execute(sql_melee, val_melee)
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (UPDATE - Melee): {err}", 500
    finally:
        if cursor: cursor.close()
    return redirect(url_for('melee_weapons_page'))

@app.route('/delete_melee_weapon/<int:item_id>', methods=['POST'])
@login_required
def delete_melee_weapon(item_id):
    """Deletes a melee weapon."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM Melee_Weapons WHERE Item_ID = %s;", (item_id,))
        cursor.execute("DELETE FROM Items WHERE Item_ID = %s;", (item_id,))
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (DELETE - Melee): {err}", 500
    finally:
        if cursor: cursor.close()
    return redirect(url_for('melee_weapons_page'))

# ========================
# 5. (RANGED_WEAPONS)(CRUD)
# ========================
@app.route('/ranged_weapons')
def ranged_weapons_page():
    db = get_db()
    cursor = db.cursor()
    
    search_name = request.args.get('search_name')
    search_culture = request.args.get('search_culture')
    
    min_w = request.args.get('min_weight'); max_w = request.args.get('max_weight')
    min_tier = request.args.get('min_tier'); max_tier = request.args.get('max_tier')
    min_dmg = request.args.get('min_dmg'); max_dmg = request.args.get('max_dmg')
    min_acc = request.args.get('min_acc'); max_acc = request.args.get('max_acc')
    min_mspd = request.args.get('min_mspd'); max_mspd = request.args.get('max_mspd')
    min_dspd = request.args.get('min_dspd'); max_dspd = request.args.get('max_dspd')
    min_rspd = request.args.get('min_rspd'); max_rspd = request.args.get('max_rspd')
    min_skill = request.args.get('min_skill'); max_skill = request.args.get('max_skill')
    
    base_query = """
    SELECT I.Item_ID, I.Item_Name, I.Weight, I.Civilian,
           C.Culture_Type_Name AS Culture, IT.Item_Type_Name AS Item_Type,
           RW.Tier, RW.Damage, RW.Accuracy, RW.Missile_Speed, RW.Skill, RW.Draw_Speed, RW.Reload_Speed, RW.Usable_on_Horseback
    FROM Items AS I
    JOIN Ranged_Weapons AS RW ON I.Item_ID = RW.Item_ID
    JOIN Culture_Types AS C ON I.Culture_ID = C.Culture_Type_ID
    JOIN Item_Types AS IT ON I.Item_Type_ID = IT.Item_Type_ID
    """
    
    where = []
    params = []
    
    if search_name: where.append("I.Item_Name LIKE %s"); params.append(f"%{search_name}%")
    if search_culture: where.append("I.Culture_ID = %s"); params.append(search_culture)
    
    if min_w: where.append("I.Weight >= %s"); params.append(min_w)
    if max_w: where.append("I.Weight <= %s"); params.append(max_w)

    if min_tier: where.append("RW.Tier >= %s"); params.append(min_tier)
    if max_tier: where.append("RW.Tier <= %s"); params.append(max_tier)
    
    if min_dmg: where.append("RW.Damage >= %s"); params.append(min_dmg)
    if max_dmg: where.append("RW.Damage <= %s"); params.append(max_dmg)

    if min_acc: where.append("RW.Accuracy >= %s"); params.append(min_acc)
    if max_acc: where.append("RW.Accuracy <= %s"); params.append(max_acc)
    
    if min_mspd: where.append("RW.Missile_Speed >= %s"); params.append(min_mspd)
    if max_mspd: where.append("RW.Missile_Speed <= %s"); params.append(max_mspd)

    if min_dspd: where.append("RW.Draw_Speed >= %s"); params.append(min_dspd)
    if max_dspd: where.append("RW.Draw_Speed <= %s"); params.append(max_dspd)

    if min_rspd: where.append("RW.Reload_Speed >= %s"); params.append(min_rspd)
    if max_rspd: where.append("RW.Reload_Speed <= %s"); params.append(max_rspd)

    if min_skill: where.append("RW.Skill >= %s"); params.append(min_skill)
    if max_skill: where.append("RW.Skill <= %s"); params.append(max_skill)

    if where: base_query += " WHERE " + " AND ".join(where)
    base_query += " ORDER BY I.Item_Name;"
    
    cursor.execute(base_query, tuple(params))
    ranged_weapons = cursor.fetchall()
    cultures = fetch_cultures(cursor)
    cursor.close()
    return render_template('items/ranged_weapons.html', ranged_weapons=ranged_weapons, cultures=cultures)

@app.route('/add_ranged_weapon', methods=['POST'])
@login_required
def add_ranged_weapon():
    """Adds a new ranged weapon (Items + Ranged_Weapons)."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        

        item_name = request.form['item_name']
        weight = request.form['weight']
        culture_id = request.form['culture_id']
        civilian = 'Yes' if 'civilian' in request.form else 'No'
        item_type_id = get_item_type_id(cursor, 'Ranged Weapon')


        sql_items = "INSERT INTO Items (Item_Type_ID, Culture_ID, Item_Name, Weight, Civilian) VALUES (%s, %s, %s, %s, %s);"
        val_items = (item_type_id, culture_id, item_name, weight, civilian)
        cursor.execute(sql_items, val_items)
        new_item_id = cursor.lastrowid
        

        usable_horse = 'Yes' if 'Usable_on_Horseback' in request.form else 'No'
        reload_horse = 'Yes' if 'Reload_on_Horseback' in request.form else 'No'
        
        val_ranged = (new_item_id, safe_int('Tier'), safe_int('Skill'), safe_int('Draw_Speed'),
                      safe_int('Damage'), safe_int('Accuracy'), safe_int('Missile_Speed'),
                      usable_horse, reload_horse, safe_int('Reload_Speed'))
        
        sql_ranged = """
        INSERT INTO Ranged_Weapons (Item_ID, Tier, Skill, Draw_Speed, Damage, Accuracy, 
                                  Missile_Speed, Usable_on_Horseback, Reload_on_Horseback, Reload_Speed)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        cursor.execute(sql_ranged, val_ranged)
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (CREATE - Ranged): {err}", 500
    finally:
        if cursor: cursor.close()
    return redirect(url_for('ranged_weapons_page'))

@app.route('/update_page_ranged/<int:item_id>')
@login_required
def update_page_ranged(item_id):
    """Renders the update form for a ranged weapon."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        query = "SELECT I.*, RW.* FROM Items AS I JOIN Ranged_Weapons AS RW ON I.Item_ID = RW.Item_ID WHERE I.Item_ID = %s;"
        cursor.execute(query, (item_id,))
        weapon = cursor.fetchone()
        if weapon is None: return "Weapon not found", 404
        cultures = fetch_cultures(cursor)
        return render_template('items/update_ranged_weapons.html', weapon=weapon, cultures=cultures, item_id=item_id)
    except pymysql.Error as err:
        return f"Query error (UPDATE PAGE - Ranged): {err}", 500
    finally:
        if cursor: cursor.close()

@app.route('/update_ranged_weapon/<int:item_id>', methods=['POST'])
@login_required
def update_ranged_weapon(item_id):
    """Updates an existing ranged weapon."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        
        # Items tablosunu güncelle
        item_name = request.form['item_name']
        weight = request.form['weight']
        culture_id = request.form['culture_id']
        civilian = 'Yes' if 'civilian' in request.form else 'No'
        sql_items = "UPDATE Items SET Item_Name = %s, Weight = %s, Culture_ID = %s, Civilian = %s WHERE Item_ID = %s;"
        val_items = (item_name, weight, culture_id, civilian, item_id)
        cursor.execute(sql_items, val_items)
        
        # Ranged_Weapons tablosunu güncelle
        usable_horse = 'Yes' if 'Usable_on_Horseback' in request.form else 'No'
        reload_horse = 'Yes' if 'Reload_on_Horseback' in request.form else 'No'
        
        tier = safe_int('Tier')
        skill = safe_int('Skill')
        draw_speed = safe_int('Draw_Speed')
        damage = safe_int('Damage')
        accuracy = safe_int('Accuracy')
        missile_speed = safe_int('Missile_Speed')
        reload_speed = safe_int('Reload_Speed')
        
        val_ranged = (tier, skill, draw_speed, damage, accuracy, missile_speed,
                      usable_horse, reload_horse, reload_speed, item_id)
        
        sql_ranged = """
        UPDATE Ranged_Weapons 
        SET Tier = %s, Skill = %s, Draw_Speed = %s, Damage = %s, Accuracy = %s, 
            Missile_Speed = %s, Usable_on_Horseback = %s, Reload_on_Horseback = %s, Reload_Speed = %s
        WHERE Item_ID = %s;
        """
        cursor.execute(sql_ranged, val_ranged)
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (UPDATE - Ranged): {err}", 500
    finally:
        if cursor: cursor.close()
    return redirect(url_for('ranged_weapons_page'))

@app.route('/delete_ranged_weapon/<int:item_id>', methods=['POST'])
@login_required
def delete_ranged_weapon(item_id):
    """Deletes a ranged weapon."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM Ranged_Weapons WHERE Item_ID = %s;", (item_id,))
        cursor.execute("DELETE FROM Items WHERE Item_ID = %s;", (item_id,))
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (DELETE - Ranged): {err}", 500
    finally:
        if cursor: cursor.close()
    return redirect(url_for('ranged_weapons_page'))

# =================
# 6. (SHIELDS)(CRUD)
# =================
@app.route('/shields')
def shields_page():
    db = get_db()
    cursor = db.cursor()
    
    search_name = request.args.get('search_name')
    search_culture = request.args.get('search_culture')
    
    min_w = request.args.get('min_weight'); max_w = request.args.get('max_weight')
    min_hp = request.args.get('min_hp'); max_hp = request.args.get('max_hp')
    min_spd = request.args.get('min_speed'); max_spd = request.args.get('max_speed')
    min_size = request.args.get('min_size'); max_size = request.args.get('max_size')
    min_res = request.args.get('min_res'); max_res = request.args.get('max_res')
    
    base_query = """
    SELECT I.Item_ID, I.Item_Name, I.Weight, I.Civilian,
           C.Culture_Type_Name AS Culture, IT.Item_Type_Name AS Item_Type,
           S.Durability, S.Resistance, S.Size, S.Speed, S.Base_Value
    FROM Items AS I
    JOIN Shields AS S ON I.Item_ID = S.Item_ID
    JOIN Culture_Types AS C ON I.Culture_ID = C.Culture_Type_ID
    JOIN Item_Types AS IT ON I.Item_Type_ID = IT.Item_Type_ID
    """
    
    where = []
    params = []
    
    if search_name: where.append("I.Item_Name LIKE %s"); params.append(f"%{search_name}%")
    if search_culture: where.append("I.Culture_ID = %s"); params.append(search_culture)
    
    if min_w: where.append("I.Weight >= %s"); params.append(min_w)
    if max_w: where.append("I.Weight <= %s"); params.append(max_w)

    if min_hp: where.append("S.Durability >= %s"); params.append(min_hp)
    if max_hp: where.append("S.Durability <= %s"); params.append(max_hp)

    if min_spd: where.append("S.Speed >= %s"); params.append(min_spd)
    if max_spd: where.append("S.Speed <= %s"); params.append(max_spd)

    if min_size: where.append("S.Size >= %s"); params.append(min_size)
    if max_size: where.append("S.Size <= %s"); params.append(max_size)

    if min_res: where.append("S.Resistance >= %s"); params.append(min_res)
    if max_res: where.append("S.Resistance <= %s"); params.append(max_res)

    if where: base_query += " WHERE " + " AND ".join(where)
    base_query += " ORDER BY I.Item_Name;"
    
    cursor.execute(base_query, tuple(params))
    shields = cursor.fetchall()
    cultures = fetch_cultures(cursor)
    cursor.close()
    return render_template('items/shields.html', shields=shields, cultures=cultures)

@app.route('/add_shield', methods=['POST'])
@login_required
def add_shield():
    """Adds a new shield item."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        
        item_name = request.form['item_name']
        weight = request.form['weight']
        culture_id = request.form['culture_id']
        civilian = 'Yes' if 'civilian' in request.form else 'No'
        item_type_id = get_item_type_id(cursor, 'Shield')

        sql_items = "INSERT INTO Items (Item_Type_ID, Culture_ID, Item_Name, Weight, Civilian) VALUES (%s, %s, %s, %s, %s);"
        val_items = (item_type_id, culture_id, item_name, weight, civilian)
        cursor.execute(sql_items, val_items)
        new_item_id = cursor.lastrowid
        

        val_shield = (new_item_id, request.form['Durability'], request.form['Resistance'],
                      request.form['Size'], request.form['Speed'], request.form['BaseValue'])
        
        sql_shield = """
        INSERT INTO Shields (Item_ID, Durability, Resistance, Size, Speed, BaseValue)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        cursor.execute(sql_shield, val_shield)
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (CREATE - Shield): {err}", 500
    finally:
        if cursor: cursor.close()
    return redirect(url_for('shields_page'))

@app.route('/update_page_shield/<int:item_id>')
@login_required
def update_page_shield(item_id):
    """Renders the update form for a shield item."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        query = "SELECT I.*, S.* FROM Items AS I JOIN Shields AS S ON I.Item_ID = S.Item_ID WHERE I.Item_ID = %s;"
        cursor.execute(query, (item_id,))
        shield = cursor.fetchone()
        if shield is None: return "Shield not found", 404
        cultures = fetch_cultures(cursor)
        return render_template('items/update_shield.html', shield=shield, cultures=cultures, item_id=item_id)
    except pymysql.Error as err:
        return f"Query error (UPDATE PAGE - Shield): {err}", 500
    finally:
        if cursor: cursor.close()

@app.route('/update_shield/<int:item_id>', methods=['POST'])
@login_required
def update_shield(item_id):
    """Updates an existing shield item."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        
        item_name = request.form['item_name']
        weight = request.form['weight']
        culture_id = request.form['culture_id']
        civilian = 'Yes' if 'civilian' in request.form else 'No'
        sql_items = "UPDATE Items SET Item_Name = %s, Weight = %s, Culture_ID = %s, Civilian = %s WHERE Item_ID = %s;"
        val_items = (item_name, weight, culture_id, civilian, item_id)
        cursor.execute(sql_items, val_items)
        
        # Shields tablosunu güncelle
        val_shield = (request.form['Durability'], request.form['Resistance'], request.form['Size'], 
                      request.form['Speed'], request.form['BaseValue'], item_id)
        
        sql_shield = """
        UPDATE Shields 
        SET Durability = %s, Resistance = %s, Size = %s, Speed = %s, BaseValue = %s
        WHERE Item_ID = %s;
        """
        cursor.execute(sql_shield, val_shield)
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (UPDATE - Shield): {err}", 500
    finally:
        if cursor: cursor.close()
    return redirect(url_for('shields_page'))

@app.route('/delete_shield/<int:item_id>', methods=['POST'])
@login_required
def delete_shield(item_id):
    """Deletes a shield item."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM Shields WHERE Item_ID = %s;", (item_id,))
        cursor.execute("DELETE FROM Items WHERE Item_ID = %s;", (item_id,))
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (DELETE - Shield): {err}", 500
    finally:
        if cursor: cursor.close()
    return redirect(url_for('shields_page'))

# ================
# 7. (MOUNTS)(CRUD)
# ================
@app.route('/mounts')
def mounts_page():
    """Lists mounts with ADVANCED search/filtering (No Type)."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()

        search_name = request.args.get('search_name')
        search_culture = request.args.get('search_culture')
        
        min_w = request.args.get('min_weight'); max_w = request.args.get('max_weight')
        min_tier = request.args.get('min_tier'); max_tier = request.args.get('max_tier')
        min_hp = request.args.get('min_hp'); max_hp = request.args.get('max_hp')
        min_speed = request.args.get('min_speed'); max_speed = request.args.get('max_speed')
        min_charge = request.args.get('min_charge'); max_charge = request.args.get('max_charge')
        min_man = request.args.get('min_man'); max_man = request.args.get('max_man')
        min_ride = request.args.get('min_ride'); max_ride = request.args.get('max_ride')

        # Mount_Type SELECT listesinden çıkarıldı
        base_query = """
        SELECT I.Item_ID, I.Item_Name, I.Weight, I.Civilian,
               C.Culture_Type_Name AS Culture, IT.Item_Type_Name AS Item_Type,
               M.Riding, M.Tier, M.Charge, M.Speed, M.Maneuver, M.HP
        FROM Items AS I
        JOIN Mounts AS M ON I.Item_ID = M.Item_ID
        JOIN Culture_Types AS C ON I.Culture_ID = C.Culture_Type_ID
        JOIN Item_Types AS IT ON I.Item_Type_ID = IT.Item_Type_ID
        """
        
        where = []
        params = []
        
        if search_name: where.append("I.Item_Name LIKE %s"); params.append(f"%{search_name}%")
        if search_culture: where.append("I.Culture_ID = %s"); params.append(search_culture)
        
        if min_w: where.append("I.Weight >= %s"); params.append(min_w)
        if max_w: where.append("I.Weight <= %s"); params.append(max_w)
        
        if min_tier: where.append("M.Tier >= %s"); params.append(min_tier)
        if max_tier: where.append("M.Tier <= %s"); params.append(max_tier)
        
        if min_hp: where.append("M.HP >= %s"); params.append(min_hp)
        if max_hp: where.append("M.HP <= %s"); params.append(max_hp)

        if min_speed: where.append("M.Speed >= %s"); params.append(min_speed)
        if max_speed: where.append("M.Speed <= %s"); params.append(max_speed)

        if min_charge: where.append("M.Charge >= %s"); params.append(min_charge)
        if max_charge: where.append("M.Charge <= %s"); params.append(max_charge)

        if min_man: where.append("M.Maneuver >= %s"); params.append(min_man)
        if max_man: where.append("M.Maneuver <= %s"); params.append(max_man)
        
        if min_ride: where.append("M.Riding >= %s"); params.append(min_ride)
        if max_ride: where.append("M.Riding <= %s"); params.append(max_ride)

        if where: base_query += " WHERE " + " AND ".join(where)
        base_query += " ORDER BY I.Item_Name;"
        
        cursor.execute(base_query, tuple(params))
        mounts = cursor.fetchall()
        cultures = fetch_cultures(cursor)
        

        return render_template('items/mounts.html', mounts=mounts, cultures=cultures)
    except pymysql.Error as err:
        return f"Query error (READ - Mounts): {err}", 500
    finally:
        if cursor: cursor.close()

@app.route('/add_mount', methods=['POST'])
@login_required
def add_mount():
    """Adds a new mount item (No Type)."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        

        item_name = request.form['item_name']
        weight = request.form['weight']
        culture_id = request.form['culture_id']
        civilian = 'Yes' if 'civilian' in request.form else 'No'
        item_type_id = get_item_type_id(cursor, 'Mount')

        sql_items = "INSERT INTO Items (Item_Type_ID, Culture_ID, Item_Name, Weight, Civilian) VALUES (%s, %s, %s, %s, %s);"
        val_items = (item_type_id, culture_id, item_name, weight, civilian)
        cursor.execute(sql_items, val_items)
        new_item_id = cursor.lastrowid
        
        # Mounts tablosu (Mount_Type çıkarıldı)
        val_mount = (new_item_id, request.form['Riding'], request.form['Tier'], request.form['Charge'],
                     request.form['Speed'], request.form['Maneuver'], request.form['HP'])
        
        sql_mount = """
        INSERT INTO Mounts (Item_ID, Riding, Tier, Charge, Speed, Maneuver, HP)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        cursor.execute(sql_mount, val_mount)
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (CREATE - Mount): {err}", 500
    finally:
        if cursor: cursor.close()
    return redirect(url_for('mounts_page'))

@app.route('/update_page_mount/<int:item_id>')
@login_required
def update_page_mount(item_id):
    """Renders the update form for a mount item."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        query = "SELECT I.*, M.* FROM Items AS I JOIN Mounts AS M ON I.Item_ID = M.Item_ID WHERE I.Item_ID = %s;"
        cursor.execute(query, (item_id,))
        mount = cursor.fetchone()
        if mount is None: return "Mount not found", 404
        cultures = fetch_cultures(cursor)
        return render_template('items/update_mount.html', mount=mount, cultures=cultures, item_id=item_id)
    except pymysql.Error as err:
        return f"Query error (UPDATE PAGE - Mount): {err}", 500
    finally:
        if cursor: cursor.close()

@app.route('/update_mount/<int:item_id>', methods=['POST'])
@login_required
def update_mount(item_id):
    """Updates an existing mount item (No Type)."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        
        # Items tablosunu güncelle
        item_name = request.form['item_name']
        weight = request.form['weight']
        culture_id = request.form['culture_id']
        civilian = 'Yes' if 'civilian' in request.form else 'No'
        sql_items = "UPDATE Items SET Item_Name = %s, Weight = %s, Culture_ID = %s, Civilian = %s WHERE Item_ID = %s;"
        val_items = (item_name, weight, culture_id, civilian, item_id)
        cursor.execute(sql_items, val_items)
        
        val_mount = (request.form['Riding'], request.form['Tier'], request.form['Charge'],
                     request.form['Speed'], request.form['Maneuver'], request.form['HP'], 
                     item_id)
        sql_mount = """
        UPDATE Mounts 
        SET Riding = %s, Tier = %s, Charge = %s, Speed = %s, 
            Maneuver = %s, HP = %s
        WHERE Item_ID = %s;
        """
        cursor.execute(sql_mount, val_mount)
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (UPDATE - Mount): {err}", 500
    finally:
        if cursor: cursor.close()
    return redirect(url_for('mounts_page'))

@app.route('/delete_mount/<int:item_id>', methods=['POST'])
@login_required
def delete_mount(item_id):
    """Deletes a mount item."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM Mounts WHERE Item_ID = %s;", (item_id,))
        cursor.execute("DELETE FROM Items WHERE Item_ID = %s;", (item_id,))
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (DELETE - Mount): {err}", 500
    finally:
        if cursor: cursor.close()
    return redirect(url_for('mounts_page'))

# =================
# 8. ITEM DETAILS
# =================

@app.route('/item_details/<int:item_id>')
def item_details_page(item_id):
    db = get_db()
    if db is None: 
        return "Database connection error.", 500
    
    try:
        with db.cursor(pymysql.cursors.DictCursor) as cursor:
            query = """
            SELECT
                I.Item_ID, I.Item_Name, I.Weight, I.Civilian,
                C.Culture_Type_Name AS Culture,
                IT.Item_Type_Name AS Item_Type,
                -- Armor bilgileri
                A.Body_Armor_Rating, A.Leg_Armor_Rating, A.Head_Armor_Rating, 
                A.Arm_Armor_Rating, A.Armor_Rating, A.Total_Armor_Rating, 
                A.Material, A.Merchandise AS Armor_Merchandise,
                -- Melee weapon bilgileri
                MW.Tier AS Melee_Tier, MW.Swing_Speed, MW.Swing_Damage, 
                MW.Thrust_Speed, MW.Thrust_Damage, MW.Length, MW.Handling, 
                MW.Merchandise AS Melee_Merchandise,
                -- Ranged weapon bilgileri
                RW.Tier AS Ranged_Tier, RW.Skill, RW.Damage AS Ranged_Damage, 
                RW.Accuracy, RW.Missile_Speed, RW.Draw_Speed, 
                RW.Reload_on_Horseback, RW.Usable_on_Horseback, RW.Reload_Speed,
                -- Shield bilgileri
                S.Durability, S.Resistance, S.Size, 
                S.Speed AS Shield_Speed, S.Base_Value AS Shield_BaseValue,
                S.Merchandise AS Shield_Merchandise,
                -- Mount bilgileri
                M.Riding, M.Tier AS Mount_Tier, M.Charge, 
                M.Speed AS Mount_Speed, M.Maneuver, M.HP, 
                M.Mount_Type, M.Weight_Bonus
            FROM Items AS I
            LEFT JOIN Culture_Types AS C ON I.Culture_ID = C.Culture_Type_ID
            LEFT JOIN Item_Types AS IT ON I.Item_Type_ID = IT.Item_Type_ID
            LEFT JOIN Armors AS A ON I.Item_ID = A.Item_ID
            LEFT JOIN Melee_Weapons AS MW ON I.Item_ID = MW.Item_ID
            LEFT JOIN Ranged_Weapons AS RW ON I.Item_ID = RW.Item_ID
            LEFT JOIN Shields AS S ON I.Item_ID = S.Item_ID
            LEFT JOIN Mounts AS M ON I.Item_ID = M.Item_ID
            WHERE I.Item_ID = %s;
            """
            cursor.execute(query, (item_id,))
            item = cursor.fetchone()
            
            if item is None:
                return "Item not found", 404
                
            return render_template('items/item_details.html', item=item)
            
    except pymysql.Error as err:
        return f"Query error: {err}", 500
    
    
@app.route('/complex_queries_page')
def complex_queries_page():
    # HATAYI ÇÖZEN KISIM: g nesnesinden bağlantıyı alıyoruz
    db = get_db()
    if db is None:
        return "Veritabanı bağlantısı kurulamadı.", 500
        
    db_cursor = db.cursor() # DictCursor zaten get_db içinde tanımlı olduğu için burada belirtmeye gerek yok

    # 1. TEMEL VERİLER (Sayfanın altındaki tablo ve filtreler için)
    db_cursor.execute("SELECT * FROM Items")
    all_items = db_cursor.fetchall()
    
    db_cursor.execute("SELECT * FROM Culture_Types")
    cultures = db_cursor.fetchall()
    
    db_cursor.execute("SELECT * FROM Item_Types")
    item_types = db_cursor.fetchall()

    # ---------------------------------------------------------
    # ANALYTICS 1: Efficiency Index (Damage / Weight) Analysis
    # ---------------------------------------------------------
    # Query 1: Melee Weapon Efficiency Analysis
    query_1 = """
    WITH Melee_Damage_Analysis AS ( 
        SELECT 
            I.Item_Name, 
            CT.Culture_Type_Name, 
            MW.Tier, 
            I.Weight, 
            (COALESCE(MW.Swing_Damage, 0) + COALESCE(MW.Thrust_Damage, 0)) AS Total_Damage, 
            (COALESCE(MW.Swing_Damage, 0) + COALESCE(MW.Thrust_Damage, 0)) / NULLIF(I.Weight, 0) AS Efficiency_Index 
        FROM Melee_Weapons AS MW 
        INNER JOIN Items AS I ON MW.Item_ID = I.Item_ID 
        INNER JOIN Culture_Types AS CT ON I.Culture_ID = CT.Culture_Type_ID 
        WHERE I.Weight > 0.1 
    ) 
    SELECT 
        Item_Name, 
        Culture_Type_Name, 
        Tier, 
        Total_Damage, 
        Weight, 
        ROUND(Efficiency_Index, 2) AS Efficiency_Index_Rounded, 
        -- PARTITION BY sayesinde her kültür kendi içinde 1'den başlar
        RANK() OVER (PARTITION BY Culture_Type_Name ORDER BY Efficiency_Index DESC) AS Culture_Rank 
    FROM Melee_Damage_Analysis 
    WHERE Efficiency_Index > 50.0 
    ORDER BY Culture_Type_Name, Culture_Rank; -- Önce kültüre, sonra ranka göre sıralar
    """ 
    
    
    
    db_cursor.execute(query_1)
    efficiency_data = db_cursor.fetchall()

    # ---------------------------------------------------------
    # ANALYTICS 2: Top-Tier Comparison
    # ---------------------------------------------------------
    query_2 = """
    (
        SELECT 'Armor' AS Item_Category, I.Item_Name AS Item_Detail,  
               A.Total_Armor_Rating AS Metric_Value, I.Weight, CT.Culture_Type_Name
        FROM Armors AS A
        INNER JOIN Items AS I ON A.Item_ID = I.Item_ID
        INNER JOIN Culture_Types AS CT ON I.Culture_ID = CT.Culture_Type_ID
        WHERE A.Total_Armor_Rating > 40
        ORDER BY A.Total_Armor_Rating DESC LIMIT 5 
    )
    UNION ALL
    (
        SELECT 'Melee Weapon' AS Item_Category, I.Item_Name AS Item_Detail,  
               (COALESCE(MW.Swing_Damage, 0) + COALESCE(MW.Thrust_Damage, 0)) AS Metric_Value, 
               I.Weight, CT.Culture_Type_Name
        FROM Melee_Weapons AS MW
        INNER JOIN Items AS I ON MW.Item_ID = I.Item_ID
        INNER JOIN Culture_Types AS CT ON I.Culture_ID = CT.Culture_Type_ID
        WHERE (COALESCE(MW.Swing_Damage, 0) + COALESCE(MW.Thrust_Damage, 0)) > 100
        ORDER BY Metric_Value DESC LIMIT 5 
    )
    ORDER BY Culture_Type_Name, Item_Category, Metric_Value DESC;
    """
    db_cursor.execute(query_2)
    top_tier_comparison = db_cursor.fetchall()

    # ---------------------------------------------------------
    # ANALYTICS 3: Weight Balance Analysis
    # ---------------------------------------------------------
    query_3 = """
        WITH High_Tier_Item_Weight AS (
            SELECT A.Item_ID, 'Armor' AS Item_Category, I.Culture_ID 
            FROM Armors AS A
            INNER JOIN Items AS I ON A.Item_ID = I.Item_ID
            WHERE A.Total_Armor_Rating >= 40
            UNION ALL
            SELECT MW.Item_ID, 'Melee Weapon' AS Item_Category, I.Culture_ID 
            FROM Melee_Weapons AS MW
            INNER JOIN Items AS I ON MW.Item_ID = I.Item_ID
            WHERE MW.Tier >= 4
        )
        SELECT
            CT.Culture_Type_Name,
            -- İSİMLERİ HTML İLE UYUMLU HALE GETİRİYORUZ:
            COALESCE(AVG(CASE WHEN HTIW.Item_Category = 'Armor' THEN I.Weight END), 0) AS Avg_High_Tier_Armor_Weight,
            COALESCE(AVG(CASE WHEN HTIW.Item_Category = 'Melee Weapon' THEN I.Weight END), 0) AS Avg_High_Tier_Melee_Weight,
            COALESCE(AVG(CASE WHEN HTIW.Item_Category = 'Armor' THEN I.Weight END), 0) - 
            COALESCE(AVG(CASE WHEN HTIW.Item_Category = 'Melee Weapon' THEN I.Weight END), 0) AS Weight_Delta_Defense_Vs_Offense
        FROM Culture_Types AS CT
        LEFT JOIN Items AS I ON CT.Culture_Type_ID = I.Culture_ID
        LEFT JOIN High_Tier_Item_Weight AS HTIW ON I.Item_ID = HTIW.Item_ID
        GROUP BY CT.Culture_Type_Name
        HAVING COUNT(HTIW.Item_ID) >= 1
        ORDER BY Weight_Delta_Defense_Vs_Offense DESC;
        """
    db_cursor.execute(query_3)
    weight_balance = db_cursor.fetchall()

    # Cursor'ı kapatıyoruz (Bağlantıyı @app.teardown_appcontext zaten kapatacak)
    db_cursor.close()

    return render_template('items/complex_queries_page.html', 
                           melee_efficiency=efficiency_data,      # Maps to {% for weapon in melee_efficiency %}
                           cross_category=top_tier_comparison,   # Maps to {% for item in cross_category %}
                           weight_balance=weight_balance)

# =============
# 9. LORDS MODULE 
# =============
@app.route("/lords")
def lords_page():
    """Lists lords with filtering including Culture."""
    db = get_db()
    if db is None: return "Database connection error.", 500

    cursor = None
    try:
        cursor = db.cursor()

        # Filtre Parametreleri
        search_name = request.args.get("search_name", "").strip()
        search_culture = request.args.get("search_culture") # YENİ
        gender     = request.args.get("gender")
        min_age    = request.args.get("min_age", type=int)
        max_age    = request.args.get("max_age", type=int)
        min_level  = request.args.get("min_level", type=int)
        max_level  = request.args.get("max_level", type=int)
        has_wiki   = request.args.get("has_wiki")
       
        base_query = """
            SELECT 
                L.lord_id, 
                L.name, 
                L.gender, 
                L.age, 
                L.traits, 
                L.source_url,
                L.level,
                C.Culture_Type_Name AS CultureName
            FROM lords L
            LEFT JOIN Culture_Types C ON L.culture_id = C.Culture_Type_ID
        """
        where_clauses = []
        params = []

        if search_name:
            where_clauses.append("L.name LIKE %s")
            params.append(f"%{search_name}%")

        if search_culture: # YENİ FİLTRE MANTIĞI
            where_clauses.append("L.culture_id = %s")
            params.append(search_culture)

        if gender:
            where_clauses.append("L.gender = %s")
            params.append(gender)

        if min_age is not None:
            where_clauses.append("L.age >= %s")
            params.append(min_age)

        if max_age is not None:
            where_clauses.append("L.age <= %s")
            params.append(max_age)
        
        if min_level is not None:
            where_clauses.append("L.level >= %s")
            params.append(min_level)

        if max_level is not None:
            where_clauses.append("L.level <= %s")
            params.append(max_level)

        if has_wiki == "1":
            where_clauses.append("L.source_url IS NOT NULL AND L.source_url <> ''")

        query = base_query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY L.name ASC;"

        cursor.execute(query, tuple(params))
        lords = cursor.fetchall()
        
       
        cultures = fetch_cultures(cursor)

        return render_template("lords/dashboard.html", lords=lords, cultures=cultures)

    except pymysql.Error as err:
        return f"Query error (READ - Lords): {err}", 500
    finally:
        if cursor: cursor.close()

@app.route("/lords/complex-stats")
def lords_complex_stats():
    """
    The complex query has been updated: It now also retrieves settlement and village names.
    """
    db = get_db()
    if db is None:
        return "Database connection error.", 500

    cursor = None
    try:
        cursor = db.cursor()

        sql = """
        SELECT
            l.lord_id,
            l.name,
            l.culture_id,

            COALESCE(sk.total_skill_points, 0) AS total_skill_points,
            COALESCE(sk.avg_skill_value, 0)    AS avg_skill_value,

            COUNT(DISTINCT s.settlement_id)    AS num_settlements,
            GROUP_CONCAT(DISTINCT s.name SEPARATOR ', ') AS settlement_names,

            COUNT(DISTINCT v.village_id)       AS num_villages,
            GROUP_CONCAT(DISTINCT v.name SEPARATOR ', ') AS village_names,

            COALESCE(AVG(s.prosperity), 0)     AS avg_settlement_prosperity

        FROM lords AS l

        LEFT JOIN (
            SELECT
                lord_id,
                SUM(value) AS total_skill_points,
                AVG(value) AS avg_skill_value
            FROM lord_skills
            GROUP BY lord_id
        ) AS sk
            ON sk.lord_id = l.lord_id

        LEFT JOIN settlements AS s
            ON s.lord_id = l.ext_id

        LEFT JOIN villages AS v
            ON v.settlement_id = s.settlement_id

        GROUP BY
            l.lord_id,
            l.name,
            l.culture_id,
            sk.total_skill_points,
            sk.avg_skill_value

        HAVING
            COUNT(DISTINCT s.settlement_id) >= 1

        ORDER BY
            total_skill_points DESC,
            num_settlements DESC,
            num_villages DESC;
        """


        cursor.execute(sql)
        rows = cursor.fetchall()
        return render_template("lords/complex_stats.html", rows=rows)

    except pymysql.Error as err:
        return f"Query error (Lords complex stats): {err}", 500
    finally:
        if cursor:
            cursor.close()

@app.route("/lords/domain-stats")
def lords_domain_stats():
    """
    Complex Query #2:
    - 4+ tablo: lords, settlements, villages, lord_skills
    - Nested subquery (global avg prosperity)
    - LEFT JOIN + GROUP BY + HAVING

    Each row: Lord + associated settlement + number of villages + skill power + prosperity/loyalty/security.
    Only settlements with prosperity ABOVE the global average are listed.
    """
    db = get_db()
    if db is None:
        return "Database connection error.", 500

    cursor = None
    try:
        cursor = db.cursor()
        sql = """
            SELECT
                l.lord_id,
                l.name               AS lord_name,
                l.culture_id,
                s.settlement_id,
                s.name               AS settlement_name,
                s.type               AS settlement_type,

                COUNT(DISTINCT v.village_id)              AS num_villages,
                COALESCE(AVG(v.hearth), 0)                AS avg_village_hearth,

                s.prosperity                              AS settlement_prosperity,

                COALESCE(sk.total_skill_points, 0)        AS total_skill_points

            FROM settlements AS s
            JOIN lords AS l
                ON s.lord_id = l.ext_id

            LEFT JOIN villages AS v
                ON v.settlement_id = s.settlement_id

            LEFT JOIN (
                SELECT
                    lord_id,
                    SUM(value) AS total_skill_points
                FROM lord_skills
                GROUP BY lord_id
            ) AS sk
                ON sk.lord_id = l.lord_id

            GROUP BY
                l.lord_id,
                l.name,
                l.culture_id,
                s.settlement_id,
                s.name,
                s.type,
                s.prosperity,
                sk.total_skill_points

            HAVING
                s.prosperity >= (
                    SELECT AVG(prosperity) FROM settlements
                )

            ORDER BY
                settlement_prosperity DESC,
                total_skill_points    DESC;
            """
        cursor.execute(sql)
        rows = cursor.fetchall()
        return render_template("lords/domain_stats.html", rows=rows)
    except pymysql.Error as err:
        return f"Query error (Lords domain stats): {err}", 500
    finally:
        if cursor:
            cursor.close()

@app.route("/lords/new", methods=["GET", "POST"])
@login_required
def create_lord():
    """Create (INSERT) a new lord."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        if request.method == "GET":
            
            cultures = fetch_cultures(cursor)
            return render_template("lords/new.html", cultures=cultures)

        # POST: read form fields
        name = request.form.get("name")
        gender = request.form.get("gender") or None
        age = request.form.get("age") or None
        level = request.form.get("level") or None
        culture_id = request.form.get("culture_id") or None 

        if not name:
            return "Name is required.", 400

        cursor.execute(
            """
            INSERT INTO lords (name, gender, age, level, culture_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (name, gender, age, level, culture_id),
        )
        db.commit()
        
    except pymysql.Error as err:
        if db: db.rollback()
        return f"Query error (CREATE - Lords): {err}", 500
    finally:
        if cursor: cursor.close()

    return redirect(url_for("lords_page"))

@app.route("/lords/<int:lord_id>/edit", methods=["GET", "POST"])
@login_required
def edit_lord(lord_id):
    """Update (UPDATE) an existing lord."""
    db = get_db()
    if db is None: return "Database connection error.", 500

    cursor = None
    try:
        cursor = db.cursor()

        if request.method == "GET":
            cursor.execute(
                "SELECT lord_id, name, gender, age, level, culture_id FROM lords WHERE lord_id = %s",
                (lord_id,)
            )
            lord = cursor.fetchone()
            if not lord:
                return "Lord not found.", 404
             
            return render_template("lords/update.html", lord=lord) # ,

        # POST: update record
        name = request.form.get("name")
        gender = request.form.get("gender") or None
        age = request.form.get("age") or None
        level = request.form.get("level") or None
        culture_id = request.form.get("culture_id") or None

        if not name:
            return "Name is required.", 400

        cursor.execute(
            """
            UPDATE lords
               SET name = %s,
                   gender = %s,
                   age = %s,
                   level = %s,
                   culture_id = %s
             WHERE lord_id = %s
            """,
            (name, gender, age, level, culture_id, lord_id),
        )
        db.commit()
    except pymysql.Error as err:
        if db: db.rollback()
        return f"Query error (UPDATE - Lords): {err}", 500
    finally:
        if cursor: cursor.close()

    return redirect(url_for("lords_page"))

@app.route("/lords/<int:lord_id>/delete", methods=["POST"])
@login_required
def delete_lord(lord_id):
    """Delete (DELETE) a lord."""
    db = get_db()
    if db is None: return "Database connection error.", 500

    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM lords WHERE lord_id = %s", (lord_id,))
        db.commit()
    except pymysql.Error as err:
        if db: db.rollback()
        return f"Query error (DELETE - Lords): {err}", 500
    finally:
        if cursor: cursor.close()

    return redirect(url_for("lords_page"))

# ======================================================
# 10. LORD API ENDPOINTS
# ======================================================
@app.get("/api/lords")
def api_list_lords():
    q = request.args.get("q")
    trait = request.args.get("trait")
    min_level = request.args.get("min_level", type=int)
    page = max(request.args.get("page", default=1, type=int), 1)
    per_page = 20

    db = get_db()
    if db is None: return jsonify({"error": "db connection error"}), 500

    where_clauses = []
    params = []

    if q:
        where_clauses.append("l.name LIKE %s")
        params.append(f"%{q}%")

    if min_level is not None:
        where_clauses.append("l.level >= %s")
        params.append(min_level)

    join_trait = False
    if trait:
        join_trait = True
        where_clauses.append("t.trait LIKE %s")
        params.append(f"%{trait}%")

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    if join_trait:
        count_sql = f"""
            SELECT COUNT(DISTINCT l.lord_id) AS total
            FROM lords l
            JOIN lord_traits t ON l.lord_id = t.lord_id
            {where_sql}
        """
        data_sql = f"""
            SELECT DISTINCT l.ext_id, l.name, l.gender, l.age, l.level, l.source_url
            FROM lords l
            JOIN lord_traits t ON l.lord_id = t.lord_id
            {where_sql}
            ORDER BY l.name
            LIMIT %s OFFSET %s
        """
    else:
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM lords l
            {where_sql}
        """
        data_sql = f"""
            SELECT l.ext_id, l.name, l.gender, l.age, l.level, l.source_url
            FROM lords l
            {where_sql}
            ORDER BY l.name
            LIMIT %s OFFSET %s
        """

    params_for_data = params + [per_page, (page - 1) * per_page]
    
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute(count_sql, tuple(params))
        total_row = cursor.fetchone()
        total = total_row["total"] if total_row else 0

        cursor.execute(data_sql, tuple(params_for_data))
        rows = cursor.fetchall()
        
        return jsonify({
            "page": page,
            "per_page": per_page,
            "total": total,
            "results": rows,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        if cursor: cursor.close()

@app.get("/api/lords/<ext_id>")
def api_lord_detail(ext_id):
    db = get_db()
    if db is None: return jsonify({"error": "db connection error"}), 500

    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT lord_id, ext_id, name, gender, age, level, source_url
            FROM lords
            WHERE ext_id = %s
            """,
            (ext_id,),
        )
        lord = cursor.fetchone()
        if not lord:
            return jsonify({"error": "not found"}), 404

        lord_id = lord["lord_id"]

        cursor.execute(
            "SELECT trait FROM lord_traits WHERE lord_id = %s ORDER BY trait",
            (lord_id,)
        )
        traits = [row["trait"] for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT ls.skill_id, s.name AS skill_name, ls.value
            FROM lord_skills ls
            JOIN skills s ON s.skill_id = ls.skill_id
            WHERE ls.lord_id = %s
            ORDER BY s.name
            """,
            (lord_id,),
        )
        skills = cursor.fetchall()

        data = {
            "ext_id": lord["ext_id"],
            "name": lord["name"],
            "gender": lord["gender"],
            "age": lord["age"],
            "level": lord["level"],
            "traits": traits,
            "skills": skills,
            "source_url": lord["source_url"],
        }
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        if cursor: cursor.close()

@app.get("/api/stats/traits")
def api_stats_traits():
    """The most common traits (top 10)."""
    db = get_db()
    if db is None: return jsonify({"error": "db connection error"}), 500

    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT trait, COUNT(*) AS count
            FROM lord_traits
            GROUP BY trait
            ORDER BY count DESC
            LIMIT 10
            """
        )
        rows = cursor.fetchall()
        return jsonify(rows)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        if cursor: cursor.close()

# ======================================================
# 10. SETTLEMENTS & VILLAGES & ANALYTICS
# ======================================================

@app.route('/settlements')
def settlements_page():
    """Lists settlements with filters."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        
        # Filtreler
        search_name = request.args.get('search_name')
        search_type = request.args.get('search_type')
        search_faction = request.args.get('search_faction')
        min_pros = request.args.get('min_prosperity')
        max_pros = request.args.get('max_prosperity')
        
        # 2. Ana Sorgu (Düzeltilmiş ve Temizlenmiş)
        base_query = """
        SELECT 
            S.settlement_id, S.name, S.type, S.prosperity, S.description,
            F.name AS FactionName,              -- Faction İsmi (Doğru)
            L.name AS LordName,                 -- Lord İsmi (Doğru)
            C.Culture_Type_Name AS CultureName  -- Culture İsmi (Doğru)
        FROM settlements S
        LEFT JOIN factions F ON S.faction_id = F.faction_id        -- Factions tablosuna faction_id ile bağlanır
        LEFT JOIN lords L ON S.lord_id = L.ext_id                  -- Lords tablosuna ext_id ile bağlanır
        LEFT JOIN Culture_Types C ON S.culture_id = C.Culture_Type_ID -- Culture tablosuna bağlanır
        """
        
        where_clauses = []
        params = []
        
        if search_name:
            where_clauses.append("S.name LIKE %s")
            params.append(f"%{search_name}%")
        if search_type:
            where_clauses.append("S.type = %s")
            params.append(search_type)
        if search_faction:
            where_clauses.append("S.faction_id = %s")
            params.append(search_faction)
        if min_pros:
            where_clauses.append("S.prosperity >= %s")
            params.append(min_pros)
        if max_pros:
            where_clauses.append("S.prosperity <= %s")
            params.append(max_pros)
            
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)
            
        base_query += " ORDER BY S.name ASC;"
        
        cursor.execute(base_query, tuple(params))
        settlements = cursor.fetchall()
        
        # Dropdown verileri
        cultures = fetch_cultures(cursor)
        try:
            cursor.execute("SELECT faction_id, name FROM factions ORDER BY name")
            factions = cursor.fetchall()
            cursor.execute("SELECT ext_id AS lord_id, name FROM lords ORDER BY name")
            lords = cursor.fetchall()
        except: 
            factions = []
            lords = []
        
        return render_template('settlements/dashboard.html', 
                               settlements=settlements, 
                               cultures=cultures,
                               factions=factions,
                               lords=lords)
    except pymysql.Error as err:
        return f"Query error: {err}", 500
    finally:
        if cursor: cursor.close()

@app.route('/settlement_detail/<string:settlement_id>')
def settlement_detail(settlement_id):
    """Details of a settlement + List of its villages."""
    db = get_db()
    if db is None: return "Database connection error.", 500
    cursor = None
    try:
        cursor = db.cursor()
        
        # 1. Settlement Verisini Çek
        query_sett = """
            SELECT S.*, F.name as FactionName, L.name as LordName, 
                   L.ext_id as RealLordID, C.Culture_Type_Name as CultureName 
            FROM settlements S
            LEFT JOIN factions F ON S.faction_id = F.faction_id
            LEFT JOIN lords L ON S.lord_id = L.ext_id 
            LEFT JOIN Culture_Types C ON S.culture_id = C.Culture_Type_ID
            WHERE S.settlement_id = %s
        """
        cursor.execute(query_sett, (settlement_id,))
        settlement = cursor.fetchone()
        
        if not settlement: return "Settlement not found", 404
        
        # 2. Köy Verilerini Çek
        query_villages = """
            SELECT V.*, C.Culture_Type_Name as CultureName 
            FROM villages V
            LEFT JOIN Culture_Types C ON V.culture_id = C.Culture_Type_ID
            WHERE V.settlement_id = %s
            ORDER BY V.name
        """
        cursor.execute(query_villages, (settlement_id,))
        villages = cursor.fetchall()
        
        # 3. Dropdown İçin Kültürleri Çek
        cultures = fetch_cultures(cursor)

        # --- YENİ EKLENEN RESİM MANTIĞI (Buraya Dikkat) ---
        # Varsayılan yolun da klasör içinde olduğunu belirtiyoruz:
        image_filename = "img/settlements/default.jpg" 
        
        if settlement and settlement.get('CultureName') and settlement.get('type'):
            # Örnek Çıktı: img/settlements/empire_town.jpg
            cult_part = settlement['CultureName'].lower().replace(' ', '_')
            type_part = settlement['type'].lower()
            image_filename = f"img/settlements/{cult_part}_{type_part}.jpg"
        # --------------------------------------------------

        return render_template('settlements/detail.html', 
                               settlement=settlement, 
                               villages=villages, 
                               cultures=cultures,
                               image_filename=image_filename) # <-- HTML'e gönderiyoruz

    except pymysql.Error as err:
        return f"Query error: {err}", 500
    finally:
        if cursor: cursor.close()

@app.route('/add_settlement', methods=['POST'])
@login_required
def add_settlement():
    db = get_db(); cursor = db.cursor()
    try:
        s_id = request.form['settlement_id']
        name = request.form['name']
        s_type = request.form['type']
        pros = request.form['prosperity'] or 0
        desc = request.form['description']
        faction_id = request.form.get('faction_id') or None
        lord_id = request.form.get('lord_id') or None
        culture_id = request.form.get('culture_id') or None
        
        query = "INSERT INTO settlements (settlement_id, name, type, prosperity, description, faction_id, lord_id, culture_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (s_id, name, s_type, pros, desc, faction_id, lord_id, culture_id))
        db.commit()
        flash(f"{name} established!", "success")
    except Exception as e: db.rollback(); flash(f"Error: {e}", "danger")
    finally: cursor.close()
    return redirect(url_for('settlements_page'))

@app.route('/update_page_settlement/<string:settlement_id>')
@login_required
def update_page_settlement(settlement_id):
    db = get_db(); cursor = db.cursor()
    cursor.execute("SELECT * FROM settlements WHERE settlement_id = %s", (settlement_id,))
    settlement = cursor.fetchone()
    if not settlement: return "Not found", 404
    
    cultures = fetch_cultures(cursor)
    try:
        cursor.execute("SELECT faction_id, name FROM factions ORDER BY name"); factions = cursor.fetchall()
        cursor.execute("SELECT ext_id AS lord_id, name FROM lords ORDER BY name"); lords = cursor.fetchall()
    except: factions = []; lords = []
    cursor.close()
    return render_template('settlements/update.html', settlement=settlement, cultures=cultures, factions=factions, lords=lords)

@app.route('/update_settlement/<string:settlement_id>', methods=['POST'])
@login_required
def update_settlement(settlement_id):
    db = get_db(); cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM settlements WHERE settlement_id=%s", (settlement_id,))
        current = cursor.fetchone()
        
        name = request.form.get('name', current['name'])
        s_type = request.form.get('type', current['type'])
        pros = request.form.get('prosperity', current['prosperity'])
        desc = request.form.get('description', current['description'])
        faction_id = request.form.get('faction_id') or current['faction_id']
        lord_id = request.form.get('lord_id') or current['lord_id']
        culture_id = request.form.get('culture_id') or current['culture_id']
        
        sql = "UPDATE settlements SET name=%s, type=%s, prosperity=%s, description=%s, faction_id=%s, lord_id=%s, culture_id=%s WHERE settlement_id=%s"
        cursor.execute(sql, (name, s_type, pros, desc, faction_id, lord_id, culture_id, settlement_id))
        db.commit()
        flash("Settlement updated.", "success")
    except Exception as e: db.rollback(); flash(str(e), "danger")
    finally: cursor.close()
    return redirect(url_for('settlements_page'))

@app.route('/delete_settlement/<string:settlement_id>', methods=['POST'])
@login_required
def delete_settlement(settlement_id):
    db = get_db(); cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM settlements WHERE settlement_id = %s", (settlement_id,))
        db.commit()
        flash("Settlement deleted.", "warning")
    except: db.rollback()
    finally: cursor.close()
    return redirect(url_for('settlements_page'))

# --- VILLAGE FEATURES (NEW) ---

@app.route('/village/<string:vid>')
def village_detail(vid):
    """Detailed view for a village."""
    db = get_db(); cursor = db.cursor()
    sql = """
        SELECT v.*, s.name as settlement_name, c.Culture_Type_Name as culture_name 
        FROM villages v
        LEFT JOIN settlements s ON v.settlement_id = s.settlement_id
        LEFT JOIN Culture_Types c ON v.culture_id = c.Culture_Type_ID
        WHERE v.village_id = %s
    """
    cursor.execute(sql, (vid,))
    vill = cursor.fetchone()
    cursor.close()
    if not vill: return "Village Not Found", 404
    return render_template('settlements/village.html', village=vill)

@app.route('/edit_village/<string:vid>', methods=['GET', 'POST'])
@login_required
def edit_village(vid):
    db = get_db(); cursor = db.cursor()
    if request.method == 'POST':
        try:
            name = request.form['name']
            res = request.form['primary_resource']
            hearth = request.form['hearth']
            desc = request.form.get('description', '')  # Yeni eklenen kısım
            
            sql = "UPDATE villages SET name=%s, primary_resource=%s, hearth=%s, description=%s WHERE village_id=%s"
            cursor.execute(sql, (name, res, hearth, desc, vid))
            db.commit()
            flash("Village updated!", "success")
            return redirect(url_for('village_detail', vid=vid))
        except Exception as e: db.rollback(); flash(str(e), "danger")
    
    cursor.execute("SELECT * FROM villages WHERE village_id=%s", (vid,))
    data = cursor.fetchone()
    cursor.close()
    return render_template('settlements/edit_village.html', village=data)
# --- app.py içindeki add_village fonksiyonunu bununla değiştir ---

@app.route('/add_village', methods=['POST'])
@login_required
def add_village():
    """Adds a village directly from the settlement detail page."""
    db = get_db(); cursor = db.cursor()
    try:
        # Formdan gelen veriler
        v_id = request.form['village_id']
        name = request.form['name']
        s_id = request.form['settlement_id'] # Hangi şehirden geldiysek ona dönmek için
        res = request.form['primary_resource']
        hearth = request.form['hearth']
        desc = request.form.get('description', '') 
        cult = request.form.get('culture_id') or None
        
        sql = "INSERT INTO villages (village_id, name, settlement_id, primary_resource, hearth, description, culture_id) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (v_id, name, s_id, res, hearth, desc, cult))
        db.commit()
        flash(f"Village '{name}' added successfully.", "success")
    except Exception as e: 
        db.rollback()
        flash(f"Error adding village: {e}", "danger")
    finally: 
        cursor.close()
    
    # İşlem bitince geldiğimiz detay sayfasına geri dönüyoruz
    return redirect(url_for('settlement_detail', settlement_id=s_id))

@app.route('/delete_village/<string:village_id>', methods=['POST'])
@login_required
def delete_village(village_id):
    db = get_db(); cursor = db.cursor()
    cursor.execute("SELECT settlement_id FROM villages WHERE village_id=%s", (village_id,))
    row = cursor.fetchone()
    sid = row['settlement_id'] if row else None
    
    cursor.execute("DELETE FROM villages WHERE village_id=%s", (village_id,))
    db.commit()
    cursor.close()
    
    if sid: return redirect(url_for('settlement_detail', settlement_id=sid))
    return redirect(url_for('settlements_page'))
# --- ANALYTICS DASHBOARD (COMPLEX QUERIES) ---
@app.route('/dashboard')
def dashboard():
    """Executes complex SQL queries for Settlement Analytics."""
    db = get_db(); cursor = db.cursor()
    
    # 1. Economic Power (Karmaşık Sorgu 1)
    # Settlement Prosperity + Toplam Köy Hearth Değeri
    cursor.execute("""
        SELECT s.name, s.type, s.prosperity, 
               COUNT(v.village_id) as village_count,
               COALESCE(SUM(v.hearth), 0) as total_village_hearth,
               (s.prosperity + COALESCE(SUM(v.hearth), 0)) as total_power
        FROM settlements s
        LEFT JOIN villages v ON s.settlement_id = v.settlement_id
        GROUP BY s.settlement_id
        ORDER BY total_power DESC
        LIMIT 10
    """)
    stats_power = cursor.fetchall()

    # 2. Battania Hardwood (Karmaşık Sorgu 2)
    # 3 Tablo Join: Villages -> Settlements -> Culture_Types
    cursor.execute("""
        SELECT v.name as village_name, s.name as bound_settlement, v.hearth
        FROM villages v
        JOIN settlements s ON v.settlement_id = s.settlement_id
        JOIN Culture_Types c ON s.culture_id = c.Culture_Type_ID
        WHERE c.Culture_Type_Name LIKE '%Battania%' 
          AND v.primary_resource LIKE '%Hardwood%'
        ORDER BY v.hearth DESC
    """)
    stats_battania = cursor.fetchall()

    # 3. Grain Production (Karmaşık Sorgu 3)
    # Gruplama ve Aggregate Fonksiyonlar
    cursor.execute("""
        SELECT c.Culture_Type_Name as culture_name,
               COUNT(v.village_id) as total_grain_villages,
               COALESCE(SUM(v.hearth), 0) as total_production_capacity
        FROM villages v
        JOIN settlements s ON v.settlement_id = s.settlement_id
        JOIN Culture_Types c ON s.culture_id = c.Culture_Type_ID
        WHERE v.primary_resource LIKE '%Grain%'
        GROUP BY c.Culture_Type_Name
        ORDER BY total_production_capacity DESC
    """)
    stats_grain = cursor.fetchall()
    
    # 4 Tabloyu Birleştiriyoruz: Factions -> Clans -> Lords (Leader) -> Settlements
    # Klan Liderinin sahip olduğu mülklerin toplam refahını hesaplar.
    cursor.execute("""
        SELECT 
            C.name AS ClanName,
            F.name AS FactionName,
            L.name AS LeaderName,
            COUNT(S.settlement_id) AS FiefCount,
            COALESCE(SUM(S.prosperity), 0) AS TotalWealth
        FROM clans C
        JOIN factions F ON C.faction_id = F.faction_id   -- Klanın Krallığı
        JOIN lords L ON C.leader_id = L.ext_id           -- Klanın Lideri
        LEFT JOIN settlements S ON S.lord_id = L.ext_id  -- Liderin Şehirleri
        GROUP BY C.clan_id, C.name, F.name, L.name
        ORDER BY TotalWealth DESC
        LIMIT 5
    """)
    stats_clans = cursor.fetchall()
    cursor.close()
    

    return render_template('settlements/complex.html', 
                           stats_power=stats_power, 
                           stats_battania=stats_battania, 
                           stats_grain=stats_grain,
                           stats_clans=stats_clans)

# ======================================================
# 11. TROOPS MODULES (COMPLETE CRUD)
# ======================================================

def fetch_troop_skills(cursor, troop_id):
    """Fetches all skill values for a specific troop from Troop_Skills table."""
    cursor.execute("""
        SELECT troop_id, one_handed, two_handed, polearm, bow, crossbow, throwing,
               riding, athletics, tactics, scouting, roguery, charm, leadership,
               trade, steward, medicine, engineering
        FROM Troop_Skills
        WHERE troop_id = %s
    """, (troop_id,))
    return cursor.fetchone()


@app.route('/update_troop_skills/<int:troop_id>', methods=['POST'])
@login_required
def update_troop_skills(troop_id):
    """Update all skills for a troop (CREATE or UPDATE)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        # Extract all skill values from form
        skills_dict = {
            'one_handed': request.form.get('one_handed', 0),
            'two_handed': request.form.get('two_handed', 0),
            'polearm': request.form.get('polearm', 0),
            'bow': request.form.get('bow', 0),
            'crossbow': request.form.get('crossbow', 0),
            'throwing': request.form.get('throwing', 0),
            'riding': request.form.get('riding', 0),
            'athletics': request.form.get('athletics', 0),
            'tactics': request.form.get('tactics', 0),
            'scouting': request.form.get('scouting', 0),
            'roguery': request.form.get('roguery', 0),
            'charm': request.form.get('charm', 0),
            'leadership': request.form.get('leadership', 0),
            'trade': request.form.get('trade', 0),
            'steward': request.form.get('steward', 0),
            'medicine': request.form.get('medicine', 0),
            'engineering': request.form.get('engineering', 0),
        }
        
        # Check if skills record exists
        cursor.execute("SELECT troop_id FROM Troop_Skills WHERE troop_id = %s", (troop_id,))
        exists = cursor.fetchone()
        
        if exists:
            # UPDATE existing
            cursor.execute("""
                UPDATE Troop_Skills 
                SET one_handed = %s, two_handed = %s, polearm = %s, bow = %s,
                    crossbow = %s, throwing = %s, riding = %s, athletics = %s,
                    tactics = %s, scouting = %s, roguery = %s, charm = %s,
                    leadership = %s, trade = %s, steward = %s, medicine = %s,
                    engineering = %s
                WHERE troop_id = %s
            """, (
                skills_dict['one_handed'], skills_dict['two_handed'], skills_dict['polearm'],
                skills_dict['bow'], skills_dict['crossbow'], skills_dict['throwing'],
                skills_dict['riding'], skills_dict['athletics'], skills_dict['tactics'],
                skills_dict['scouting'], skills_dict['roguery'], skills_dict['charm'],
                skills_dict['leadership'], skills_dict['trade'], skills_dict['steward'],
                skills_dict['medicine'], skills_dict['engineering'],
                troop_id
            ))
        else:
            # INSERT new
            cursor.execute("""
                INSERT INTO Troop_Skills 
                (troop_id, one_handed, two_handed, polearm, bow, crossbow, throwing,
                 riding, athletics, tactics, scouting, roguery, charm, leadership,
                 trade, steward, medicine, engineering)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                troop_id,
                skills_dict['one_handed'], skills_dict['two_handed'], skills_dict['polearm'],
                skills_dict['bow'], skills_dict['crossbow'], skills_dict['throwing'],
                skills_dict['riding'], skills_dict['athletics'], skills_dict['tactics'],
                skills_dict['scouting'], skills_dict['roguery'], skills_dict['charm'],
                skills_dict['leadership'], skills_dict['trade'], skills_dict['steward'],
                skills_dict['medicine'], skills_dict['engineering']
            ))
        
        db.commit()
        
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (UPDATE - Troop Skills): {err}", 500
    finally:
        if cursor:
            cursor.close()
    
    return redirect(url_for('troop_detail', troop_id=troop_id))



@app.route('/troops')
def troops_page():
    """List all troops with filtering (READ)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        # Get filter parameters
        culture_filter = request.args.get('culture', '')
        tier_filter = request.args.get('tier', '')
        mounted_filter = request.args.get('mounted', '')
        search_name = request.args.get('search_name', '').strip()
        
        # Build query
        query = """
            SELECT t.*, c.Culture_Type_Name as culture_name
            FROM Troops t
            LEFT JOIN Culture_Types c ON t.Culture_Type_ID = c.Culture_Type_ID
            WHERE 1=1
        """
        params = []
        
        if search_name:
            query += " AND t.name LIKE %s"
            params.append(f"%{search_name}%")
        
        if culture_filter:
            query += " AND c.Culture_Type_Name = %s"
            params.append(culture_filter)
        
        if tier_filter:
            query += " AND t.tier = %s"
            params.append(tier_filter)
        
        if mounted_filter:
            query += " AND t.is_mounted = %s"
            params.append(1 if mounted_filter == 'yes' else 0)
        
        query += " ORDER BY c.Culture_Type_Name, t.tier, t.name"
        
        cursor.execute(query, tuple(params))
        troops_list = cursor.fetchall()
        
        # Get all cultures for filter dropdown
        cursor.execute("SELECT Culture_Type_ID, Culture_Type_Name FROM Culture_Types ORDER BY Culture_Type_Name")
        cultures = cursor.fetchall()
        
        return render_template('troops/dashboard.html', 
                             troops=troops_list,
                             cultures=cultures,
                             current_culture=culture_filter,
                             current_tier=tier_filter,
                             current_mounted=mounted_filter,
                             search_name=search_name)
    except pymysql.Error as err:
        return f"Query error (READ - Troops): {err}", 500
    finally:
        if cursor:
            cursor.close()


@app.route('/troop/<int:troop_id>')
def troop_detail(troop_id):
    """Detailed view of a single troop (READ)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        # Get troop info
        cursor.execute("""
            SELECT t.*, c.Culture_Type_Name as culture_name
            FROM Troops t
            LEFT JOIN Culture_Types c ON t.Culture_Type_ID = c.Culture_Type_ID
            WHERE t.troop_id = %s
        """, (troop_id,))
        
        troop = cursor.fetchone()
        
        if not troop:
            return "Troop not found", 404
        
        # Get troop skills
        skills = fetch_troop_skills(cursor, troop_id)
        
        # Get upgrade paths (what this troop can upgrade to)
        cursor.execute("""
            SELECT t.*, up.xp_cost
            FROM Troop_Upgrade_Paths up
            JOIN Troops t ON up.upgraded_troop_id = t.troop_id
            WHERE up.base_troop_id = %s
        """, (troop_id,))
        upgrades = cursor.fetchall()
        
        # Get prerequisites (what troops upgrade to this one)
        cursor.execute("""
            SELECT t.*, up.xp_cost
            FROM Troop_Upgrade_Paths up
            JOIN Troops t ON up.base_troop_id = t.troop_id
            WHERE up.upgraded_troop_id = %s
        """, (troop_id,))
        prerequisites = cursor.fetchall()
        
        # Get equipment for this troop
        cursor.execute("""
            SELECT tej.slot, i.Item_Name as item_name, i.Item_ID as item_id
            FROM Troop_Equipment_Junction tej
            JOIN Items i ON tej.item_id = i.Item_ID
            WHERE tej.troop_id = %s
            ORDER BY tej.slot
        """, (troop_id,))
        equipment_raw = cursor.fetchall()
        
        # Group equipment by slot
        equipment_by_slot = {}
        for item in equipment_raw:
            slot = item['slot']
            if slot not in equipment_by_slot:
                equipment_by_slot[slot] = []
            equipment_by_slot[slot].append(item)
        
        return render_template('troops/detail.html',
                             troop=troop,
                             skills=skills,
                             upgrades=upgrades,
                             prerequisites=prerequisites,
                             equipment=equipment_by_slot)
    except pymysql.Error as err:
        return f"Query error (READ - Troop Detail): {err}", 500
    finally:
        if cursor:
            cursor.close()


@app.route('/add_troop', methods=['POST'])
@login_required
def add_troop():
    """Add a new troop (CREATE)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        name = request.form['name']
        culture_id = request.form.get('Culture_Type_ID') or None
        tier = request.form.get('tier', 1)
        wage = request.form.get('wage', 0)
        is_mounted = 1 if 'is_mounted' in request.form else 0
        
        cursor.execute("""
            INSERT INTO Troops (name, culture_id, tier, wage, is_mounted)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, culture_id, tier, wage, is_mounted))
        
        db.commit()
        
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (CREATE - Troop): {err}", 500
    finally:
        if cursor:
            cursor.close()
    
    return redirect(url_for('troops_page'))


@app.route('/update_page_troop/<int:troop_id>')
@login_required
def update_page_troop(troop_id):
    """Display the update form for a troop (UPDATE - GET)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        # Get troop data
        cursor.execute("""
            SELECT t.*, c.Culture_Type_Name as culture_name
            FROM Troops t
            LEFT JOIN Culture_Types c ON t.Culture_Type_ID = c.Culture_Type_ID
            WHERE t.troop_id = %s
        """, (troop_id,))
        troop = cursor.fetchone()
        
        if not troop:
            return "Troop not found", 404
        
        # Get all cultures for dropdown
        cursor.execute("SELECT Culture_Type_ID, Culture_Type_Name FROM Culture_Types ORDER BY Culture_Type_Name")
        cultures = cursor.fetchall()
        
        return render_template('troops/update.html', troop=troop, cultures=cultures)
        
    except pymysql.Error as err:
        return f"Query error (READ - Update Page): {err}", 500
    finally:
        if cursor:
            cursor.close()


@app.route('/update_troop/<int:troop_id>', methods=['POST'])
@login_required
def update_troop(troop_id):
    """Update an existing troop (UPDATE - POST)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        name = request.form['name']
        culture_id = request.form.get('Culture_Type_ID') or None
        tier = request.form.get('tier', 1)
        wage = request.form.get('wage', 0)
        is_mounted = 1 if 'is_mounted' in request.form else 0
        
        cursor.execute("""
            UPDATE Troops 
            SET name = %s, 
                culture_id = %s, 
                tier = %s, 
                wage = %s, 
                is_mounted = %s
            WHERE troop_id = %s
        """, (name, culture_id, tier, wage, is_mounted, troop_id))
        
        db.commit()
        
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (UPDATE - Troop): {err}", 500
    finally:
        if cursor:
            cursor.close()
    
    return redirect(url_for('troop_detail', troop_id=troop_id))


@app.route('/delete_troop/<int:troop_id>', methods=['POST'])
@login_required
def delete_troop(troop_id):
    """Delete a troop (DELETE)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM Troops WHERE troop_id = %s", (troop_id,))
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (DELETE - Troop): {err}", 500
    finally:
        if cursor:
            cursor.close()
    
    return redirect(url_for('troops_page'))


# =========================
# 12. TROOP EQUIPMENT CRUD
# =========================

@app.route('/add_troop_equipment/<int:troop_id>', methods=['POST'])
@login_required
def add_troop_equipment(troop_id):
    """Add equipment to a troop (CREATE)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        item_id = request.form['item_id']
        slot = request.form['slot']
        
        cursor.execute("""
            INSERT INTO Troop_Equipment_Junction (troop_id, item_id, slot)
            VALUES (%s, %s, %s)
        """, (troop_id, item_id, slot))
        
        db.commit()
        
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (CREATE - Troop Equipment): {err}", 500
    finally:
        if cursor:
            cursor.close()
    
    return redirect(url_for('troop_detail', troop_id=troop_id))


@app.route('/update_troop_equipment/<int:troop_id>/<int:old_item_id>/<old_slot>', methods=['POST'])
@login_required
def update_troop_equipment(troop_id, old_item_id, old_slot):
    """Update equipment for a troop (UPDATE)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        new_item_id = request.form['item_id']
        new_slot = request.form['slot']
        
        # Delete old entry and insert new one (composite key constraint)
        cursor.execute("""
            DELETE FROM Troop_Equipment_Junction 
            WHERE troop_id = %s AND item_id = %s AND slot = %s
        """, (troop_id, old_item_id, old_slot))
        
        cursor.execute("""
            INSERT INTO Troop_Equipment_Junction (troop_id, item_id, slot)
            VALUES (%s, %s, %s)
        """, (troop_id, new_item_id, new_slot))
        
        db.commit()
        
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (UPDATE - Troop Equipment): {err}", 500
    finally:
        if cursor:
            cursor.close()
    
    return redirect(url_for('troop_detail', troop_id=troop_id))


@app.route('/delete_troop_equipment/<int:troop_id>/<int:item_id>/<slot>', methods=['POST'])
@login_required
def delete_troop_equipment(troop_id, item_id, slot):
    """Remove equipment from a troop (DELETE)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("""
            DELETE FROM Troop_Equipment_Junction 
            WHERE troop_id = %s AND item_id = %s AND slot = %s
        """, (troop_id, item_id, slot))
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (DELETE - Troop Equipment): {err}", 500
    finally:
        if cursor:
            cursor.close()
    
    return redirect(url_for('troop_detail', troop_id=troop_id))


# ================================
# 12. TROOP UPGRADE PATHS CRUD
# ================================

@app.route('/add_upgrade_path/<int:base_troop_id>', methods=['POST'])
@login_required
def add_upgrade_path(base_troop_id):
    """Add an upgrade path (CREATE)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        upgraded_troop_id = request.form['upgraded_troop_id']
        xp_cost = request.form.get('xp_cost', 0)
        
        cursor.execute("""
            INSERT INTO Troop_Upgrade_Paths (base_troop_id, upgraded_troop_id, xp_cost)
            VALUES (%s, %s, %s)
        """, (base_troop_id, upgraded_troop_id, xp_cost))
        
        db.commit()
        
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (CREATE - Upgrade Path): {err}", 500
    finally:
        if cursor:
            cursor.close()
    
    return redirect(url_for('troop_detail', troop_id=base_troop_id))


@app.route('/update_upgrade_path/<int:base_troop_id>/<int:old_upgraded_id>', methods=['POST'])
@login_required
def update_upgrade_path(base_troop_id, old_upgraded_id):
    """Update an upgrade path (UPDATE)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        new_upgraded_id = request.form['upgraded_troop_id']
        xp_cost = request.form.get('xp_cost', 0)
        
        # Delete old entry and insert new one (composite key constraint)
        cursor.execute("""
            DELETE FROM Troop_Upgrade_Paths 
            WHERE base_troop_id = %s AND upgraded_troop_id = %s
        """, (base_troop_id, old_upgraded_id))
        
        cursor.execute("""
            INSERT INTO Troop_Upgrade_Paths (base_troop_id, upgraded_troop_id, xp_cost)
            VALUES (%s, %s, %s)
        """, (base_troop_id, new_upgraded_id, xp_cost))
        
        db.commit()
        
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (UPDATE - Upgrade Path): {err}", 500
    finally:
        if cursor:
            cursor.close()
    
    return redirect(url_for('troop_detail', troop_id=base_troop_id))



@app.route('/delete_upgrade_path/<int:base_troop_id>/<int:upgraded_troop_id>', methods=['POST'])
@login_required
def delete_upgrade_path(base_troop_id, upgraded_troop_id):
    """Remove an upgrade path (DELETE)."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("""
            DELETE FROM Troop_Upgrade_Paths 
            WHERE base_troop_id = %s AND upgraded_troop_id = %s
        """, (base_troop_id, upgraded_troop_id))
        db.commit()
    except pymysql.Error as err:
        db.rollback()
        return f"Query error (DELETE - Upgrade Path): {err}", 500
    finally:
        if cursor:
            cursor.close()
    
    return redirect(url_for('troop_detail', troop_id=base_troop_id))


# ================================================================
# 12.5 TROOPS MODULE - ADVANCED ANALYTICS (FOR COMPLEX QUERIES)
# ================================================================

@app.route('/troops/analytics')
def troops_analytics():
    """Advanced analytics page for troops with two complex queries."""
    db = get_db()
    if db is None:
        return "Database connection error.", 500
    
    cursor = None
    try:
        cursor = db.cursor()
        
        # ====================================================================
        # QUERY 1: Troop Upgrade Path Efficiency Analysis (FIXED)
        # ====================================================================
        query1 = """
        SELECT 
            t_base.troop_id AS troop_id,
            c.Culture_Type_Name AS culture,
            t_base.name AS base_troop,
            t_base.tier AS starting_tier,
            t_base.wage AS starting_wage,
            COUNT(DISTINCT tup.upgraded_troop_id) AS upgrade_paths_available,
            AVG(t_upgraded.tier) AS avg_upgrade_tier,
            SUM(tup.xp_cost) AS total_xp_required,
            AVG(t_upgraded.wage - t_base.wage) AS avg_wage_increase,
            
            -- FIXED: Count base troop equipment
            (SELECT COUNT(DISTINCT tej1.item_id)
             FROM Troop_Equipment_Junction tej1
             WHERE tej1.troop_id = t_base.troop_id) AS current_equipment_count,
            
            -- FIXED: Calculate actual armor improvement
            (SELECT AVG(
                    COALESCE((SELECT AVG(a_up.Total_Armor_Rating) 
                              FROM Troop_Equipment_Junction tej_up
                              JOIN Armors a_up ON tej_up.item_id = a_up.Item_ID
                              WHERE tej_up.troop_id = tup2.upgraded_troop_id 
                              AND tej_up.slot = 'armors'), 0) -
                    COALESCE((SELECT AVG(a_base.Total_Armor_Rating)
                              FROM Troop_Equipment_Junction tej_base
                              JOIN Armors a_base ON tej_base.item_id = a_base.Item_ID
                              WHERE tej_base.troop_id = t_base.troop_id
                              AND tej_base.slot = 'armors'), 0)
                )
             FROM Troop_Upgrade_Paths tup2
             WHERE tup2.base_troop_id = t_base.troop_id) AS avg_armor_improvement,
            
            ROUND(
                AVG(t_upgraded.tier - t_base.tier) / NULLIF(AVG(tup.xp_cost), 0) * 1000, 
                2
            ) AS upgrade_efficiency_score
        FROM Troops t_base
        INNER JOIN Culture_Types c ON t_base.Culture_Type_ID = c.Culture_Type_ID
        LEFT JOIN Troop_Upgrade_Paths tup ON t_base.troop_id = tup.base_troop_id
        LEFT JOIN Troops t_upgraded ON tup.upgraded_troop_id = t_upgraded.troop_id
        WHERE tup.upgraded_troop_id IS NOT NULL
        GROUP BY 
            t_base.troop_id,
            c.Culture_Type_Name,
            t_base.name,
            t_base.tier,
            t_base.wage
        HAVING upgrade_paths_available > 0
        ORDER BY upgrade_efficiency_score DESC, avg_upgrade_tier DESC
        """
        
        cursor.execute(query1)
        query1_results = cursor.fetchall()
        
        # ====================================================================
        # QUERY 2: Equipment Loadout Quality Comparison
        # ====================================================================
        query2 = """
        SELECT 
            c.Culture_Type_Name,
            t.tier,
            CASE WHEN t.is_mounted = 1 THEN 'Cavalry' ELSE 'Infantry' END AS unit_type,
            COUNT(DISTINCT t.troop_id) AS unit_count,
            COUNT(DISTINCT CASE WHEN tup.base_troop_id IS NOT NULL THEN t.troop_id END) AS units_with_prerequisites,
            COUNT(DISTINCT CASE WHEN tup.upgraded_troop_id IS NOT NULL THEN t.troop_id END) AS units_with_upgrades,
            COALESCE(AVG(tup.xp_cost), 0) AS avg_upgrade_xp_cost,
            COALESCE(AVG(a.Total_Armor_Rating), 0) AS avg_total_armor,
            COALESCE(AVG(GREATEST(COALESCE(mw.Swing_Damage, 0), COALESCE(mw.Thrust_Damage, 0))), 0) AS avg_melee_damage,
            COALESCE(AVG(m.Charge), 0) AS avg_mount_charge,
            (SELECT COUNT(DISTINCT f.faction_id) FROM factions f WHERE f.culture_id = c.Culture_Type_ID) AS supporting_factions,
            ROUND(
                (t.tier * 100 + 
                 COALESCE(AVG(a.Total_Armor_Rating), 0) + 
                 COALESCE(AVG(GREATEST(COALESCE(mw.Swing_Damage, 0), COALESCE(mw.Thrust_Damage, 0))), 0) * 2 +
                 COALESCE(AVG(m.Charge), 0) * 0.5) 
                 / NULLIF(AVG(t.wage), 0),
                2
            ) AS cost_effectiveness_ratio,
            ROUND(
                (t.tier * 15) +
                (COALESCE(AVG(a.Total_Armor_Rating), 0) * 0.3) +
                (COALESCE(AVG(a.Body_Armor_Rating), 0) * 0.2) +
                (COALESCE(AVG(GREATEST(COALESCE(mw.Swing_Damage, 0), COALESCE(mw.Thrust_Damage, 0))), 0) * 0.8) +
                (COALESCE(AVG(rw.Damage), 0) * 0.4) +
                (COALESCE(AVG(m.Charge), 0) * 0.5) +
                (COALESCE(AVG(m.Speed), 0) * 0.3) +
                (COUNT(DISTINCT t.troop_id) * 8) +
                (COALESCE((SELECT COUNT(DISTINCT f.faction_id) FROM factions f WHERE f.culture_id = c.Culture_Type_ID), 0) * 3),
                2
            ) AS strategic_value_score
        FROM Troops t
        INNER JOIN Culture_Types c ON t.Culture_Type_ID = c.Culture_Type_ID
        LEFT JOIN Troop_Equipment_Junction tej ON t.troop_id = tej.troop_id
        LEFT JOIN Items i ON tej.item_id = i.Item_ID
        LEFT JOIN Armors a ON tej.item_id = a.Item_ID AND tej.slot = 'armors'
        LEFT JOIN Melee_Weapons mw ON tej.item_id = mw.Item_ID AND tej.slot = 'melee_weapons'
        LEFT JOIN Ranged_Weapons rw ON tej.item_id = rw.Item_ID AND tej.slot = 'ranged_weapons'
        LEFT JOIN Shields s ON tej.item_id = s.Item_ID AND tej.slot = 'shields'
        LEFT JOIN Mounts m ON tej.item_id = m.Item_ID AND tej.slot = 'horses'
        LEFT JOIN Troop_Upgrade_Paths tup ON t.troop_id = tup.base_troop_id OR t.troop_id = tup.upgraded_troop_id
        WHERE t.tier >= 1
        GROUP BY 
            c.Culture_Type_ID,
            c.Culture_Type_Name,
            t.tier,
            t.is_mounted
        ORDER BY 
            strategic_value_score DESC,
            cost_effectiveness_ratio DESC
        """
        
        cursor.execute(query2)
        query2_results = cursor.fetchall()
        
        return render_template('troops/analytics.html',
                             query1_results=query1_results,
                             query2_results=query2_results,)
        
    except pymysql.Error as err:
        return f"Query error: {err}", 500
    finally:
        if cursor:
            cursor.close()

@app.route('/troop/<int:troop_id>/loadout')
def troop_loadout(troop_id):
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM Troops WHERE troop_id = %s", (troop_id,))
    troop = cursor.fetchone()
    
    if not troop:
        return "Troop not found", 404
    
    cursor.execute("""
        SELECT tej.slot, i.Item_Name, i.Item_ID
        FROM Troop_Equipment_Junction tej
        JOIN Items i ON tej.item_id = i.Item_ID
        WHERE tej.troop_id = %s
        ORDER BY tej.slot
    """, (troop_id,))
    equipment_raw = cursor.fetchall()
    
    equipment = {}
    for item in equipment_raw:
        slot = item['slot']
        if slot not in equipment:
            equipment[slot] = []
        equipment[slot].append(item)
    
    cursor.execute("SELECT Items.Item_ID, Items.Item_Name FROM Items JOIN Melee_Weapons ON Items.Item_ID = Melee_Weapons.Item_ID ORDER BY Items.Item_Name")
    melee_weapons = cursor.fetchall()
    
    cursor.execute("SELECT Items.Item_ID, Items.Item_Name FROM Items JOIN Ranged_Weapons ON Items.Item_ID = Ranged_Weapons.Item_ID ORDER BY Items.Item_Name")
    ranged_weapons = cursor.fetchall()
    
    cursor.execute("SELECT Items.Item_ID, Items.Item_Name FROM Items JOIN Armors ON Items.Item_ID = Armors.Item_ID ORDER BY Items.Item_Name")
    armors = cursor.fetchall()
    
    cursor.execute("SELECT Items.Item_ID, Items.Item_Name FROM Items JOIN Shields ON Items.Item_ID = Shields.Item_ID ORDER BY Items.Item_Name")
    shields = cursor.fetchall()
    
    cursor.execute("SELECT Items.Item_ID, Items.Item_Name FROM Items JOIN Mounts ON Items.Item_ID = Mounts.Item_ID ORDER BY Items.Item_Name")
    mounts = cursor.fetchall()
    
    cursor.close()
    
    return render_template('troops/loadout.html',
                         troop=troop,
                         equipment=equipment,
                         melee_weapons=melee_weapons,
                         ranged_weapons=ranged_weapons,
                         armors=armors,
                         shields=shields,
                         mounts=mounts)




# ======================================================
# 13. FACTIONS MODULE - CRUD
# ======================================================

def fetch_clans(cursor):
    """Fetches list of clans for dropdowns (Helper)."""
    try:
        cursor.execute("SELECT clan_id, name FROM clans ORDER BY name")
        return cursor.fetchall()
    except:
        return []

@app.route('/factions')
def factions_page():
    """Tüm krallıkları filtreleme seçenekleriyle listeler."""
    db = get_db()
    cursor = db.cursor()
    try:
        search_name = request.args.get('search_name', '')
        search_culture = request.args.get('search_culture', '')

        # JOIN Sorgusu: DBML'deki 'leader_id -> lords.ext_id' ilişkisine göre güncellendi
        query = """
            SELECT 
                F.faction_id, F.name, F.description, F.banner_key,
                C.Culture_Type_Name AS CultureName,
                L.name AS LeaderName,
                CL.name AS ClanName
            FROM factions F
            LEFT JOIN Culture_Types C ON F.culture_id = C.Culture_Type_ID
            LEFT JOIN lords L ON F.leader_id = L.ext_id
            LEFT JOIN clans CL ON F.ruling_clan_id = CL.clan_id
            WHERE F.name LIKE %s
        """
        params = [f"%{search_name}%"]

        if search_culture:
            query += " AND F.culture_id = %s"
            params.append(search_culture)

        query += " ORDER BY F.name ASC"
        cursor.execute(query, params)
        factions = cursor.fetchall()

        # Formlar için dropdown verileri
        cursor.execute("SELECT Culture_Type_ID, Culture_Type_Name FROM Culture_Types")
        cultures = cursor.fetchall()
        
        cursor.execute("SELECT ext_id, name FROM lords ORDER BY name")
        lords = cursor.fetchall()
        
        cursor.execute("SELECT clan_id, name FROM clans ORDER BY name")
        clans = cursor.fetchall()

        return render_template('factions/dashboard.html', 
                               factions=factions, cultures=cultures, 
                               lords=lords, clans=clans)
    finally:
        cursor.close()

@app.route('/add_faction', methods=['POST'])
def add_faction():
    """Yeni bir krallık oluşturur."""
    db = get_db()
    cursor = db.cursor()
    try:
        # Formdan gelen veriler
        f_id = request.form['faction_id']
        name = request.form['name']
        desc = request.form['description']
        banner = request.form['banner_key']
        culture = request.form.get('culture_id')
        leader = request.form.get('leader_id') or None
        clan = request.form.get('ruling_clan_id') or None

        sql = """INSERT INTO factions (faction_id, name, description, banner_key, 
                                     culture_id, leader_id, ruling_clan_id)
                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, (f_id, name, desc, banner, culture, leader, clan))
        db.commit()
        flash("Krallık başarıyla kuruldu!")
    except Exception as e:
        db.rollback()
        flash(f"Hata: {str(e)}")
    return redirect(url_for('factions_page'))

@app.route('/update_faction/<string:faction_id>', methods=['GET','POST']) #get is also added 
def update_faction(faction_id):
    """Mevcut krallık verilerini günceller."""
    db = get_db()
    cursor = db.cursor()
    #for get part 
    if request.method == 'GET':
        
        cursor.execute("SELECT * FROM factions WHERE faction_id = %s", (faction_id,))
        faction = cursor.fetchone()

        if not faction:
            flash("Faction not found.", "warning")
            return redirect(url_for('factions_page'))

        
        cursor.execute("SELECT Culture_Type_ID, Culture_Type_Name FROM Culture_Types ORDER BY Culture_Type_Name")
        cultures = cursor.fetchall()

        cursor.execute("SELECT ext_id, name FROM lords ORDER BY name")
        lords = cursor.fetchall()

        cursor.execute("SELECT clan_id, name FROM clans ORDER BY name")
        clans = cursor.fetchall()

        
        return render_template('factions/update.html', 
                               faction=faction, 
                               cultures=cultures, 
                               lords=lords, 
                               clans=clans) 
    try:
        sql = """UPDATE factions 
                 SET name=%s, description=%s, banner_key=%s, 
                     culture_id=%s, leader_id=%s, ruling_clan_id=%s
                 WHERE faction_id=%s"""
        cursor.execute(sql, (
            request.form['name'], request.form['description'],
            request.form['banner_key'], request.form['culture_id'],
            request.form.get('leader_id') or None,
            request.form.get('ruling_clan_id') or None,
            faction_id
        ))
        db.commit()
        flash("Krallık güncellendi.")
    except Exception as e:
        db.rollback()
        flash(f"Hata: {e}")
    return redirect(url_for('factions_page'))

@app.route('/delete_faction/<string:faction_id>', methods=['POST'])
def delete_faction(faction_id):
    """Krallığı siler (Foreign Key ON DELETE SET NULL kuralına dayanır)."""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM factions WHERE faction_id = %s", (faction_id,))
        db.commit()
        flash("Krallık tarihe karıştı.")
    except Exception as e:
        db.rollback()
        flash(f"Silme hatası: {e}")
    return redirect(url_for('factions_page'))

@app.route('/faction_stats')
def faction_stats():
    conn = get_db() 
    import pymysql.cursors 
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    #  COMPLEX QUERY 1: ELITE KINGDOMS RANKING 
    query_power = """
        SELECT 
            f.name AS faction_name, 
            l.name AS leader_name,
            ct.Culture_Type_Name AS culture,
            COUNT(c.clan_id) AS total_clans,
            ROUND(AVG(c.tier), 1) AS avg_clan_tier
        FROM factions f
        LEFT JOIN clans c ON f.faction_id = c.faction_id
        LEFT JOIN lords l ON f.leader_id = l.ext_id
        LEFT JOIN Culture_Types ct ON f.culture_id = ct.Culture_Type_ID
        GROUP BY f.faction_id, f.name, l.name, ct.Culture_Type_Name
        HAVING total_clans > 0 
        ORDER BY avg_clan_tier DESC;
    """
    
    #  COMPLEX QUERY 2: CULTURAL DISTRIBUTION 
    query_culture = """
        SELECT 
            ct.Culture_Type_Name, 
            COUNT(f.faction_id) as count
        FROM factions f
        JOIN Culture_Types ct ON f.culture_id = ct.Culture_Type_ID
        GROUP BY ct.Culture_Type_Name
    """

    cursor.execute(query_power)
    leaderboard = cursor.fetchall()
    
    cursor.execute(query_culture)
    culture_stats = cursor.fetchall()
    
    return render_template('factions/faction_stats.html', leaderboard=leaderboard, culture_stats=culture_stats)



# ======================================================
# CLANS  (CRUD + COMPLEX QUERIES)
# ======================================================


@app.route('/clans')
def clans_page():
    
    db = get_db()
    cursor = db.cursor()
    
    search_q = request.args.get('q', '')
    filter_tier = request.args.get('tier', '')
    filter_faction = request.args.get('faction_id', '')

    
    query = """
        SELECT 
            c.clan_id, 
            c.name, 
            c.tier, 
            c.banner_key,
            f.name AS faction_name,
            l.name AS leader_name
        FROM clans c
        LEFT JOIN factions f ON c.faction_id = f.faction_id
        LEFT JOIN lords l ON c.leader_id = l.ext_id
        WHERE c.name LIKE %s
    """
    params = [f"%{search_q}%"]

    # Dynamic Filter
    if filter_tier:
        query += " AND c.tier = %s"
        params.append(filter_tier)
    
    if filter_faction:
        query += " AND c.faction_id = %s"
        params.append(filter_faction)

    query += " ORDER BY c.tier DESC, c.name ASC"
    
    cursor.execute(query, tuple(params))
    clans = cursor.fetchall()

    # Dropdown verileri
    cursor.execute("SELECT faction_id, name FROM factions ORDER BY name")
    factions_list = cursor.fetchall()

    return render_template('clans/dashboard.html', clans=clans, factions=factions_list)

@app.route('/clans/stats')
def clan_stats():
    """CLANS ANALYTICS"""
    db = get_db()
    import pymysql.cursors
    cursor = db.cursor(pymysql.cursors.DictCursor)

    # COMPLEX QUERY 1: CLAN OVERVIEW
    
    query_wealth = """
        SELECT 
            c.name AS clan_name,
            f.name AS faction_name,
            COUNT(s.settlement_id) AS fief_count,
            COALESCE(SUM(s.prosperity), 0) AS total_wealth
        FROM clans c
        LEFT JOIN factions f ON c.faction_id = f.faction_id
        LEFT JOIN lords l ON c.leader_id = l.ext_id
        LEFT JOIN settlements s ON s.lord_id = l.ext_id
        GROUP BY c.clan_id, c.name, f.name
        ORDER BY total_wealth DESC
        LIMIT 10
    """

    # COMPLEX QUERY 2: ELITE CLANS (Tier Deviation)
    query_elite = """
        SELECT 
            c.name AS clan_name,
            c.tier,
            f.name AS faction_name,
            faction_stats.avg_tier AS faction_avg
        FROM clans c
        JOIN factions f ON c.faction_id = f.faction_id
        JOIN (
            SELECT faction_id, AVG(tier) as avg_tier 
            FROM clans 
            GROUP BY faction_id
        ) AS faction_stats ON c.faction_id = faction_stats.faction_id
        WHERE c.tier > faction_stats.avg_tier
        ORDER BY (c.tier - faction_stats.avg_tier) DESC;
    """

    cursor.execute(query_wealth)
    wealth_stats = cursor.fetchall()

    cursor.execute(query_elite)
    elite_stats = cursor.fetchall()

    return render_template('clans/stats.html', wealth_stats=wealth_stats, elite_stats=elite_stats)

# --- CREATE, UPDATE, DELETE (Standart CRUD) ---

@app.route('/clans/new', methods=['GET', 'POST'])
def add_clan():
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        try:
            sql = "INSERT INTO clans (clan_id, name, tier, faction_id, leader_id) VALUES (%s, %s, %s, %s, %s)"
            # Not: clan_id formdan geliyor, auto-increment değilse bu doğru.
            cursor.execute(sql, (
                request.form['clan_id'], 
                request.form['name'], 
                request.form['tier'], 
                request.form.get('faction_id') or None, 
                request.form.get('leader_id') or None
            ))
            db.commit()
            flash("New clan established!", "success")
            return redirect(url_for('clans_page'))
        except Exception as e:
            db.rollback()
            flash(f"Error: {e}", "danger")

   
    cursor.execute("SELECT faction_id, name FROM factions ORDER BY name")
    factions = cursor.fetchall()
    
    cursor.execute("SELECT ext_id, name FROM lords ORDER BY name")
    lords = cursor.fetchall()
    
    return render_template('clans/new.html', factions=factions, lords=lords)

@app.route('/clans/delete/<string:clan_id>', methods=['POST'])
def delete_clan(clan_id):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM clans WHERE clan_id=%s", (clan_id,))
        db.commit()
        flash("Clan disbanded.", "warning")
    except Exception as e:
        db.rollback()
        flash(f"Error: {e}", "danger")
    return redirect(url_for('clans_page'))

@app.route('/clans/update/<string:clan_id>', methods=['GET', 'POST'])
def update_clan(clan_id):
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        try:
            sql = """
                UPDATE clans 
                SET name=%s, tier=%s, faction_id=%s, leader_id=%s, banner_key=%s
                WHERE clan_id=%s
            """
            cursor.execute(sql, (
                request.form['name'], 
                request.form['tier'], 
                request.form.get('faction_id') or None, 
                request.form.get('leader_id') or None, 
                request.form['banner_key'], 
                clan_id
            ))
            db.commit()
            flash(f"Clan updated successfully!", "success")
            return redirect(url_for('clans_page'))
        except Exception as e:
            db.rollback()
            flash(f"Update error: {e}", "danger")

    
    cursor.execute("SELECT * FROM clans WHERE clan_id = %s", (clan_id,))
    clan = cursor.fetchone()

    if not clan:
        flash("Clan not found.", "warning")
        return redirect(url_for('clans_page'))

    cursor.execute("SELECT faction_id, name FROM factions ORDER BY name")
    factions = cursor.fetchall()
    
    cursor.execute("SELECT ext_id, name FROM lords ORDER BY name")
    lords = cursor.fetchall()

    return render_template('clans/update.html', clan=clan, factions=factions, lords=lords)
    
# added for view
@app.route('/factions/view/<string:faction_id>')
def faction_detail(faction_id):
    
    db = get_db()
    cursor = db.cursor()
    
   
    cursor.execute("""
        SELECT F.*, C.Culture_Type_Name, L.name as LeaderName 
        FROM factions F
        LEFT JOIN Culture_Types C ON F.culture_id = C.Culture_Type_ID
        LEFT JOIN lords L ON F.leader_id = L.ext_id
        WHERE F.faction_id = %s
    """, (faction_id,))
    faction = cursor.fetchone()

    if not faction:
        return "Faction not found", 404

    
    cursor.execute("""
        SELECT * FROM clans WHERE faction_id = %s ORDER BY tier DESC
    """, (faction_id,))
    clans = cursor.fetchall()

    
    cursor.execute("""
        SELECT * FROM settlements WHERE faction_id = %s ORDER BY prosperity DESC
    """, (faction_id,))
    settlements = cursor.fetchall()

    return render_template('factions/detail.html', faction=faction, clans=clans, settlements=settlements)

# ========================
# Run App
# ========================
if __name__ == '__main__':
    app.run(debug=True)