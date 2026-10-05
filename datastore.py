#okay so like what the fuck i need to crate a datastore with funcitons because thats what the controller will then call?
import sqlite3, datetime
class Datastore:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.cursor = self.connection.cursor()

        self.cursor.executescript(
                    """
                    CREATE INDEX IF NOT EXISTS idx_loaned_game_active
                        ON games_loaned(game_id) WHERE return_date IS NULL;
                    CREATE INDEX IF NOT EXISTS idx_loaned_loan ON games_loaned(loan_id);
                    CREATE INDEX IF NOT EXISTS idx_loans_mem ON loans(mem_id);
                    CREATE INDEX IF NOT EXISTS idx_games_cat ON games(Cat_id);
                    CREATE INDEX IF NOT EXISTS idx_members_email ON members(email);
                    CREATE INDEX IF NOT EXISTS idx_fees_mem_year ON fees(mem_id, year);
                    """
                )
        self.cursor.execute("PRAGMA journal_mode = WAL")
        self.cursor.execute("PRAGMA synchronous = NORMAL")

    def get_catalogue(self):
        #[(game_id:int, name:str, category:str, min_players:int, max_players:int, min_age:int, status:str, on_hold:bool)]
        """
        `status` is `"Now"` if the game is currently available, or
        `f"Loaned on {date}"` if it is currently on loan.
        """
        self.cursor.execute(
            #the collumn is min_playes for some reason
            """
            SELECT games.game_id, games.name, categories.name, min_playes, max_players, min_age, hold, loans.loan_date
            FROM games
            LEFT JOIN games_loaned ON games.game_id = games_loaned.game_id
                                  AND games_loaned.return_date IS NULL
            LEFT JOIN loans ON games_loaned.loan_id = loans.loan_id
            LEFT JOIN categories ON games.Cat_id = categories.cat_id
            """
        )
        results = self.cursor.fetchall()
        actual_results = []
        for result in results:
            status = f"Loaned on {result[7]}" if result[7] is not None else "Now"
            actual_results.append((*result[:6], status, result[6] is not None))
        return actual_results

    def get_game_name(self, name):
        #oke we do the % thingy
        self.cursor.execute(
            """
            SELECT games.game_id, games.name, categories.name, min_playes, max_players, min_age, hold, loans.loan_date
            FROM games
            LEFT JOIN games_loaned ON games.game_id = games_loaned.game_id
                                  AND games_loaned.return_date IS NULL
            LEFT JOIN loans ON games_loaned.loan_id = loans.loan_id
            LEFT JOIN categories ON games.Cat_id = categories.cat_id
            WHERE games.name LIKE :name
            """,
            {
                'name': f"%{name}%"
            }
        )
        results = self.cursor.fetchall()
        actual_results = []
        for result in results:
            status = f"Loaned on {result[7]}" if result[7] is not None else "Now"
            actual_results.append((*result[:6], status, result[6] is not None))
        return actual_results

    def get_games_players(self, num_players):
        self.cursor.execute(
            """
            SELECT games.game_id, games.name, categories.name, min_playes, max_players, min_age, hold, loans.loan_date
            FROM games
            LEFT JOIN games_loaned ON games.game_id = games_loaned.game_id
                                  AND games_loaned.return_date IS NULL
            LEFT JOIN loans ON games_loaned.loan_id = loans.loan_id
            LEFT JOIN categories ON games.Cat_id = categories.cat_id
            WHERE min_playes <= :players AND max_players >= :players
            """,
            {
                'players': num_players
            }
        )
        results = self.cursor.fetchall()
        actual_results = []
        for result in results:
            status = f"Loaned on {result[7]}" if result[7] is not None else "Now"
            actual_results.append((*result[:6], status, result[6] is not None))
        return actual_results

    def get_games_age(self, age):
        self.cursor.execute(
            """
            SELECT games.game_id, games.name, categories.name, min_playes, max_players, min_age, hold, loans.loan_date
            FROM games
            LEFT JOIN games_loaned ON games.game_id = games_loaned.game_id
                                  AND games_loaned.return_date IS NULL
            LEFT JOIN loans ON games_loaned.loan_id = loans.loan_id
            LEFT JOIN categories ON games.Cat_id = categories.cat_id
            WHERE min_age <= :age
            """,
            {
                'age': age
            }
        )
        results = self.cursor.fetchall()
        actual_results = []
        for result in results:
            status = f"Loaned on {result[7]}" if result[7] is not None else "Now"
            actual_results.append((*result[:6], status, result[6] is not None))
        return actual_results

    def get_games_available(self):
        self.cursor.execute(
            """
            SELECT games.game_id, games.name, categories.name, min_playes, max_players, min_age, hold
            FROM games
            LEFT JOIN games_loaned ON games.game_id = games_loaned.game_id
                                  AND games_loaned.return_date IS NULL
            LEFT JOIN categories ON games.Cat_id = categories.cat_id
            WHERE games_loaned.loan_id IS NULL
            """
        )
        results = self.cursor.fetchall()
        actual_results = []
        for result in results:
            actual_results.append((*result[:6], "Now", result[6] is not None))
        return actual_results

    def get_games_on_hold(self):
        self.cursor.execute(
            """
            SELECT games.game_id, games.name, categories.name, min_playes, max_players, min_age, hold, loans.loan_date
            FROM games
            LEFT JOIN games_loaned ON games.game_id = games_loaned.game_id
                                  AND games_loaned.return_date IS NULL
            LEFT JOIN loans ON games_loaned.loan_id = loans.loan_id
            LEFT JOIN categories ON games.Cat_id = categories.cat_id
            WHERE hold IS NOT NULL
            """
        )
        results = self.cursor.fetchall()
        actual_results = []
        for result in results:
            status = f"Loaned on {result[7]}" if result[7] is not None else "Now"
            actual_results.append((*result[:6], status, result[6] is not None))
        return actual_results

    def get_members(self):
        self.cursor.execute(
            """
            SELECT mem_id, first_name, last_name
            FROM members
            WHERE active = 1
            """
        )
        results = self.cursor.fetchall()
        actual_results = []
        for result in results:
            actual_results.append((result[0], f"{result[1]} {result[2]}"))
        return actual_results

    def get_all_members(self):
            self.cursor.execute(
                """
                SELECT mem_id, first_name, last_name, active, admin
                FROM members
                """
            )
            results = self.cursor.fetchall()
            actual_results = []
            for result in results:
                actual_results.append((result[0], f"{result[1]} {result[2]}",result[3:]))
            return actual_results

    #okeeeeeeee logining um what do we do check docs
    def get_member_by_email(self, email):
        #(mem_id:int, first_name:str, last_name:str, email:str, password:str, phone:str, active:int, admin:int) | None
        self.cursor.execute(
            """
            SELECT *
            FROM members
            WHERE email = :member_email
            """,
            {
                "member_email": email
            }
        )
        results = self.cursor.fetchone()
        return results

    def get_games(self):
        self.cursor.execute(
            """
            SELECT game_id, name
            FROM games
            """
        )
        return self.cursor.fetchall()
    
    def get_games_on_loan(self):
        self.cursor.execute(
            """
            SELECT name, loans.loan_id, members.first_name, members.last_name
            FROM games
            INNER JOIN games_loaned ON games.Game_id = games_loaned.game_id
            INNER JOIN loans ON games_loaned.loan_id = loans.loan_id
            INNER JOIN members ON loans.mem_id = members.mem_id
            WHERE games_loaned.return_date IS NULL
            """
        )
        results = self.cursor.fetchall()
        actual_results = []
        for result in results:
            actual_results.append((*result[:2], f"{result[2]} {result[3]}"))
        return actual_results

    def get_categories(self):
        self.cursor.execute(
            """
            SELECT *
            FROM categories
            """
        )
        return self.cursor.fetchall()

    def get_members_games(self, mem_id):
        self.cursor.execute(
            """
            SELECT games.game_id, games.name
            FROM games
            JOIN games_loaned ON games.game_id = games_loaned.game_id
            JOIN loans ON games_loaned.loan_id = loans.loan_id
            WHERE loans.mem_id = :mem_id AND games_loaned.return_date IS NULL
            """,
            {
                "mem_id":mem_id
            }
        )
        return self.cursor.fetchall()

    def get_fees(self, mem_id):
        self.cursor.execute(
            """
            SELECT year, paid
            FROM fees
            WHERE mem_id = :mem_id
            """,
            {
                "mem_id":mem_id
            }
        )
        results = self.cursor.fetchall()
        actual_results = []
        for result in results:
            actual_results.append((result[0], result[1]==1))
        return actual_results
    
    def get_latest_loan_id(self):
        self.cursor.execute(
            """
            SELECT MAX(loan_id)
            FROM loans
            """
        )
        return self.cursor.fetchone()[0]

    def get_mem_held_games(self):
        self.cursor.execute(
            """
            SELECT game_id, hold
            FROM games
            WHERE hold IS NOT NULL
            """
        )
        return self.cursor.fetchall()

    def add_annual_fees(self, year, amt):
        self.cursor.execute(
            """
            INSERT INTO fees
            SELECT :year, mem_id, :amt, 0 FROM members WHERE active = 1
            """,
            {"year": year, "amt": amt},
        )
        self.connection.commit()

    def add_loan(self, mem_id):
        self.cursor.execute(
            """
            INSERT INTO loans (mem_id, loan_date)
            VALUES (:mem_id, :date)
            """,
            {
                "mem_id": mem_id,
                "date":self.date_today()
            }
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def add_game_to_loan(self, loan_id, game_id):
        self.cursor.execute(
            """
            INSERT INTO games_loaned (loan_id, game_id)
            VALUES (:loan_id, :game_id)
            """,
            {
                "loan_id":loan_id,
                "game_id":game_id
            }
        )
        self.connection.commit()

    def add_members(self, first_name, last_name, email, password, phone, admin):
        self.cursor.execute(
            """
            INSERT INTO members (first_name, last_name, email, password, phone, active, admin)
            VALUES (:first_name, :last_name, :email, :password, :phone, 1, :admin)
            """,
            {
                "first_name":first_name,
                "last_name":last_name,
                "email":email,
                "password":password,
                "phone":phone,
                "admin":admin
            }
        )
        self.connection.commit()

    def add_game(self, name, cat_id, min_players, max_players, min_age, owner):
        self.cursor.execute(
            """
            INSERT INTO games(name, cat_id, min_playes, max_players, min_age, owner)
            VALUES (:name, :cat_id, :min_players, :max_players, :min_age, :owner)
            """,
            {
                "name":name,
                "cat_id":cat_id,
                "min_players":min_players,
                "max_players":max_players,
                "min_age":min_age,
                "owner":owner
            }
        )
        self.connection.commit()

    def update_hold(self, mem_id, game_id):
        self.cursor.execute(
            """
            SELECT hold
            FROM games
            WHERE game_id = :game_id
            """,
            {
                "game_id":game_id
            }
        )
        if self.cursor.fetchone()[0] == mem_id:
            mem_id = None
        self.cursor.execute(
            """
            UPDATE games
            SET hold = :mem_id
            WHERE game_id = :game_id
            """,
            {
                "mem_id":mem_id,
                "game_id":game_id
            }
        )
        self.connection.commit()

    def update_loan(self, game_id):
        self.cursor.execute(
            """
            UPDATE games_loaned
            SET return_date = :date
            WHERE game_id = :game_id AND return_date IS NULL
            """,
            {
                "date":self.date_today(),
                "game_id":game_id
            }
        )
        self.connection.commit()

    def update_member_status(self, mem_id):
        self.cursor.execute(
            """
            SELECT active
            FROM members
            WHERE mem_id = :mem_id
            """,
            {
                "mem_id":mem_id
            }
        )
        active = self.cursor.fetchone()[0]
        self.cursor.execute(
            """
            UPDATE members
            SET active = :active
            WHERE mem_id = :mem_id
            """,
            {
                "active":(active-1)**2,
                "mem_id":mem_id
            }
        )
        self.connection.commit()

    def update_fees(self, year, mem_id):
        self.cursor.execute(
            """
            UPDATE fees
            SET paid = 1
            WHERE year = :year AND mem_id = :mem_id
            """,
            {
                "year":year,
                "mem_id":mem_id
            }
        )
        self.connection.commit()

    def update_password(self, mem_id, password):
        self.cursor.execute(
            """
            UPDATE members
            SET password = :password
            WHERE mem_id = :mem_id
            """,
            {
                "password":password,
                "mem_id":mem_id
            }
        )
        self.connection.commit()

    def delete_game(self, game_id):
        #heh execute, delete
        self.cursor.execute(
            """
            DELETE FROM games
            WHERE game_id = :game_id
            """,
            {
                "game_id":game_id
            }
        )
        self.connection.commit()

    def date_today(self):
        return datetime.date.today().strftime("%Y-%m-%d")
    
    def close(self):
        self.cursor.execute("PRAGMA optimize")
        self.connection.close()

# db = Datastore("TableTopGamers.db")
# db.add_annual_fees(2120,5)