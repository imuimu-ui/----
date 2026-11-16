
import os
import sqlite3
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta

# ==========================================
# WORLD ECONOMY - ALL IN ONE BOT
# ==========================================

TOKEN = os.getenv("DISCORD_TOKEN")
DB_FILE = "world_economy.db"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

db = sqlite3.connect(DB_FILE)
db.row_factory = sqlite3.Row
cursor = db.cursor()

# ==========================================
# DATABASE
# ==========================================

cursor.executescript("""
CREATE TABLE IF NOT EXISTS news (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT, content TEXT, category TEXT,
 author TEXT, status TEXT, created TEXT
);

CREATE TABLE IF NOT EXISTS bounties (
 player TEXT PRIMARY KEY,
 amount INTEGER, reason TEXT, updated TEXT
);

CREATE TABLE IF NOT EXISTS yonkou (
 name TEXT PRIMARY KEY,
 crew TEXT, bounty INTEGER
);

CREATE TABLE IF NOT EXISTS marine (
 name TEXT PRIMARY KEY,
 rank TEXT, division TEXT
);

CREATE TABLE IF NOT EXISTS government (
 name TEXT PRIMARY KEY,
 position TEXT
);

CREATE TABLE IF NOT EXISTS pirates (
 name TEXT PRIMARY KEY,
 crew TEXT, role TEXT
);

CREATE TABLE IF NOT EXISTS companies (
 name TEXT PRIMARY KEY,
 owner TEXT, description TEXT
);

CREATE TABLE IF NOT EXISTS islands (
 name TEXT PRIMARY KEY,
 ruler TEXT, region TEXT
);

CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT, description TEXT,
 status TEXT, created TEXT
);

CREATE TABLE IF NOT EXISTS fruits (
 name TEXT PRIMARY KEY,
 fruit_type TEXT, ability TEXT,
 owner TEXT
);

CREATE TABLE IF NOT EXISTS warnings (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER, moderator TEXT,
 reason TEXT, created TEXT
);

CREATE TABLE IF NOT EXISTS economy (
 user_id INTEGER PRIMARY KEY,
 balance INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS xp (
 user_id INTEGER PRIMARY KEY,
 points INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS logs (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 action TEXT, actor TEXT,
 target TEXT, details TEXT,
 created TEXT
);
""")
db.commit()


def execute(sql, params=()):
    cursor.execute(sql, params)
    db.commit()
    return cursor


def log_action(action, actor, target, details=""):
    execute(
        "INSERT INTO logs(action,actor,target,details,created) VALUES(?,?,?,?,?)",
        (action, actor, target, details, datetime.now().isoformat())
    )


def embed(title, description, color=discord.Color.gold()):
    result = discord.Embed(
        title=f"『📰』{title}",
        description=description,
        color=color,
        timestamp=datetime.now()
    )
    result.set_footer(text="WORLD ECONOMY • THE NEWS THAT SHAKES THE WORLD")
    return result


def is_admin(interaction):
    return interaction.user.guild_permissions.administrator


def is_mod(interaction):
    permissions = interaction.user.guild_permissions
    return permissions.administrator or permissions.manage_messages


async def deny(interaction):
    await interaction.response.send_message(
        "⛔ You do not have permission to use this command.",
        ephemeral=True
    )


async def admin_required(interaction):
    if not is_admin(interaction):
        await deny(interaction)
        return False
    return True


async def mod_required(interaction):
    if not is_mod(interaction):
        await deny(interaction)
        return False
    return True


def get_records(table, limit=10):
    allowed = {
        "news", "bounties", "yonkou", "marine",
        "government", "pirates", "companies",
        "islands", "events", "fruits", "logs"
    }
    if table not in allowed:
        return []
    return execute(
        f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT ?",
        (limit,)
    ).fetchall()


# ==========================================
# STARTUP
# ==========================================

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as error:
        print("Command sync error:", error)

    await bot.change_presence(
        activity=discord.Game(name="The World Economy")
    )
    print(f"🌍 WORLD ECONOMY ONLINE: {bot.user}")


# ==========================================
# 1. NEWSPAPER & NEWS
# ==========================================

news_group = app_commands.Group(
    name="news", description="World Economy Press"
)

@news_group.command(name="publish", description="Publish a news report")
@app_commands.describe(title="Headline", category="News category", content="Article content")
async def news_publish(interaction, title: str, category: str, content: str):
    if not await admin_required(interaction):
        return

    execute(
        """INSERT INTO news(title,content,category,author,status,created)
        VALUES(?,?,?,?,?,?)""",
        (title, content, category, str(interaction.user),
         "PUBLISHED", datetime.now().isoformat())
    )
    log_action("NEWS PUBLISHED", interaction.user, title)

    await interaction.response.send_message(
        embed=embed(f"BREAKING NEWS: {title}",
                    f"**Category:** {category}\n\n{content}\n\n"
                    f"*Reported by {interaction.user.display_name}*")
    )


@news_group.command(name="draft", description="Save an unpublished article")
async def news_draft(interaction, title: str, category: str, content: str):
    if not await admin_required(interaction):
        return

    execute(
        """INSERT INTO news(title,content,category,author,status,created)
        VALUES(?,?,?,?,?,?)""",
        (title, content, category, str(interaction.user),
         "DRAFT", datetime.now().isoformat())
    )
    await interaction.response.send_message(
        "📝 Article saved as a draft.", ephemeral=True
    )


@news_group.command(name="latest", description="Read the latest news")
async def news_latest(interaction):
    rows = execute(
        "SELECT * FROM news WHERE status='PUBLISHED' ORDER BY id DESC LIMIT 5"
    ).fetchall()

    if not rows:
        await interaction.response.send_message("No published news yet.")
        return

    description = ""
    for row in rows:
        description += (
            f"**{row['title']}** · {row['category']}\n"
            f"{row['content'][:500]}\n\n"
        )

    await interaction.response.send_message(
        embed=embed("LATEST WORLD NEWS", description)
    )


@news_group.command(name="archive", description="View the newspaper archive")
async def news_archive(interaction):
    rows = execute(
        "SELECT id,title,category,created FROM news "
        "WHERE status='PUBLISHED' ORDER BY id DESC LIMIT 15"
    ).fetchall()

    text = "\n".join(
        f"`#{r['id']}` **{r['title']}** · {r['category']}"
        for r in rows
    ) or "The archive is empty."

    await interaction.response.send_message(
        embed=embed("NEWSPAPER ARCHIVE", text), ephemeral=True
    )


@news_group.command(name="delete", description="Delete an article")
async def news_delete(interaction, article_id: int):
    if not await admin_required(interaction):
        return

    execute("DELETE FROM news WHERE id=?", (article_id,))
    log_action("NEWS DELETED", interaction.user, str(article_id))
    await interaction.response.send_message("🗑️ Article deleted.")


@news_group.command(name="newspaper", description="Generate a newspaper edition")
async def news_newspaper(interaction):
    rows = execute(
        "SELECT * FROM news WHERE status='PUBLISHED' ORDER BY id DESC LIMIT 8"
    ).fetchall()

    if not rows:
        await interaction.response.send_message("No articles available.")
        return

    description = "# THE WORLD ECONOMY\n"
    description += "### THE NEWS THAT SHAKES THE WORLD\n\n"

    for row in rows:
        description += (
            f"## {row['title']}\n"
            f"**{row['category']}**\n"
            f"{row['content'][:350]}\n\n"
        )

    await interaction.response.send_message(
        embed=embed("DAILY NEWSPAPER", description[:4000])
    )


# ==========================================
# 2. BOUNTY & WANTED SYSTEM
# ==========================================

bounty_group = app_commands.Group(
    name="bounty", description="Pirate bounty administration"
)

@bounty_group.command(name="set", description="Set a player's bounty")
async def bounty_set(interaction, player: str, amount: int, reason: str = "Official bounty"):
    if not await admin_required(interaction):
        return

    if amount < 0:
        await interaction.response.send_message("Invalid amount.", ephemeral=True)
        return

    execute(
        """INSERT INTO bounties(player,amount,reason,updated)
        VALUES(?,?,?,?)
        ON CONFLICT(player) DO UPDATE SET
        amount=excluded.amount,
        reason=excluded.reason,
        updated=excluded.updated""",
        (player, amount, reason, datetime.now().isoformat())
    )

    log_action("BOUNTY SET", interaction.user, player, str(amount))
    await interaction.response.send_message(
        embed=embed("💰 NEW WANTED POSTER",
                    f"**{player}**\n\n"
                    f"BOUNTY: **฿{amount:,}**\n"
                    f"Reason: {reason}\n"
                    f"ISSUED BY THE WORLD GOVERNMENT")
    )


@bounty_group.command(name="remove", description="Remove a bounty")
async def bounty_remove(interaction, player: str):
    if not await admin_required(interaction):
        return

    execute("DELETE FROM bounties WHERE player=?", (player,))
    log_action("BOUNTY REMOVED", interaction.user, player)
    await interaction.response.send_message(f"Removed bounty for {player}.")


@bounty_group.command(name="check", description="Check a bounty")
async def bounty_check(interaction, player: str):
    row = execute(
        "SELECT * FROM bounties WHERE player=?", (player,)
    ).fetchone()

    if not row:
        await interaction.response.send_message("No wanted record found.")
        return

    await interaction.response.send_message(
        embed=embed("WANTED DATABASE",
                    f"**{player}**\n฿{row['amount']:,}\n"
                    f"Reason: {row['reason']}")
    )


@bounty_group.command(name="top", description="Top 10 wanted pirates")
async def bounty_top(interaction):
    rows = execute(
        "SELECT * FROM bounties ORDER BY amount DESC LIMIT 10"
    ).fetchall()

    text = "\n".join(
        f"**{i+1}. {r['player']}** — ฿{r['amount']:,}"
        for i, r in enumerate(rows)
    ) or "No wanted pirates."

    await interaction.response.send_message(
        embed=embed("🏴‍☠️ MOST WANTED", text)
    )


# ==========================================
# 3. YONKOU & PIRATE ORGANIZATION
# ==========================================

pirate_group = app_commands.Group(
    name="pirate", description="Pirate administration"
)

@pirate_group.command(name="add", description="Register a pirate")
async def pirate_add(interaction, name: str, crew: str, role: str):
    if not await admin_required(interaction):
        return

    execute(
        "INSERT OR REPLACE INTO pirates(name,crew,role) VALUES(?,?,?)",
        (name, crew, role)
    )
    await interaction.response.send_message(
        embed=embed("PIRATE REGISTER",
                    f"**{name}**\nCrew: {crew}\nPosition: {role}")
    )


@pirate_group.command(name="crew", description="Create or update a pirate crew")
async def pirate_crew(interaction, captain: str, crew: str):
    if not await admin_required(interaction):
        return

    execute(
        "INSERT OR REPLACE INTO pirates(name,crew,role) VALUES(?,?,?)",
        (captain, crew, "Captain")
    )
    await interaction.response.send_message(
        embed=embed("PIRATE CREW CREATED",
                    f"Captain: {captain}\nCrew: {crew}")
    )


yonkou_group = app_commands.Group(
    name="yonkou", description="Four Emperors administration"
)

@yonkou_group.command(name="appoint", description="Appoint a Yonkou")
async def yonkou_appoint(interaction, name: str, crew: str, bounty: int):
    if not await admin_required(interaction):
        return

    execute(
        "INSERT OR REPLACE INTO yonkou(name,crew,bounty) VALUES(?,?,?)",
        (name, crew, bounty)
    )
    await interaction.response.send_message(
        embed=embed("👑 NEW YONKOU",
                    f"**{name}**\nCrew: {crew}\nBounty: ฿{bounty:,}")
    )


@yonkou_group.command(name="remove", description="Remove a Yonkou")
async def yonkou_remove(interaction, name: str):
    if not await admin_required(interaction):
        return

    execute("DELETE FROM yonkou WHERE name=?", (name,))
    await interaction.response.send_message(f"{name} removed from Yonkou registry.")


@yonkou_group.command(name="list", description="List all Yonkou")
async def yonkou_list(interaction):
    rows = execute("SELECT * FROM yonkou ORDER BY bounty DESC").fetchall()
    text = "\n".join(
        f"👑 **{r['name']}** · {r['crew']} · ฿{r['bounty']:,}"
        for r in rows
    ) or "No Yonkou registered."

    await interaction.response.send_message(
        embed=embed("THE FOUR EMPERORS", text)
    )


# ==========================================
# 4. MARINE
# ==========================================

marine_group = app_commands.Group(
    name="marine", description="Marine administration"
)

@marine_group.command(name="appoint", description="Appoint a Marine officer")
async def marine_appoint(interaction, name: str, rank: str, division: str = "General"):
    if not await admin_required(interaction):
        return

    execute(
        "INSERT OR REPLACE INTO marine(name,rank,division) VALUES(?,?,?)",
        (name, rank, division)
    )
    await interaction.response.send_message(
        embed=embed("⚓ MARINE APPOINTMENT",
                    f"Officer: **{name}**\nRank: {rank}\nDivision: {division}")
    )


@marine_group.command(name="promote", description="Promote a Marine officer")
async def marine_promote(interaction, name: str, new_rank: str):
    if not await admin_required(interaction):
        return

    row = execute(
        "SELECT * FROM marine WHERE name=?", (name,)
    ).fetchone()

    if not row:
        await interaction.response.send_message("Officer not found.")
        return

    execute(
        "UPDATE marine SET rank=? WHERE name=?",
        (new_rank, name)
    )
    log_action("MARINE PROMOTION", interaction.user, name, new_rank)
    await interaction.response.send_message(
        f"⚓ {name} has been promoted to {new_rank}."
    )


@marine_group.command(name="list", description="List Marine officers")
async def marine_list(interaction):
    rows = execute("SELECT * FROM marine ORDER BY rank").fetchall()
    text = "\n".join(
        f"⚓ **{r['name']}** · {r['rank']} · {r['division']}"
        for r in rows
    ) or "No Marine officers registered."

    await interaction.response.send_message(
        embed=embed("MARINE HEADQUARTERS", text)
    )


# ==========================================
# 5. WORLD GOVERNMENT
# ==========================================

government_group = app_commands.Group(
    name="government", description="World Government administration"
)

@government_group.command(name="appoint", description="Appoint a government official")
async def government_appoint(interaction, name: str, position: str):
    if not await admin_required(interaction):
        return

    execute(
        "INSERT OR REPLACE INTO government(name,position) VALUES(?,?)",
        (name, position)
    )
    await interaction.response.send_message(
        embed=embed("WORLD GOVERNMENT",
                    f"Official: **{name}**\nPosition: {position}")
    )


@government_group.command(name="remove", description="Remove a government official")
async def government_remove(interaction, name: str):
    if not await admin_required(interaction):
        return

    execute("DELETE FROM government WHERE name=?", (name,))
    await interaction.response.send_message("Official removed.")


@government_group.command(name="list", description="List government officials")
async def government_list(interaction):
    rows = execute("SELECT * FROM government").fetchall()
    text = "\n".join(
        f"👑 **{r['name']}** — {r['position']}" for r in rows
    ) or "No officials registered."

    await interaction.response.send_message(
        embed=embed("WORLD GOVERNMENT DATABASE", text)
    )


# ==========================================
# 6. WORLD ECONOMY BUSINESS
# ==========================================

company_group = app_commands.Group(
    name="company", description="Company management"
)

@company_group.command(name="create", description="Register a company")
async def company_create(interaction, name: str, owner: str, description: str):
    if not await admin_required(interaction):
        return

    execute(
        "INSERT OR REPLACE INTO companies(name,owner,description) VALUES(?,?,?)",
        (name, owner, description)
    )
    await interaction.response.send_message(
        embed=embed("🏢 COMPANY REGISTER",
                    f"**{name}**\nOwner: {owner}\n{description}")
    )


@company_group.command(name="list", description="List registered companies")
async def company_list(interaction):
    rows = execute("SELECT * FROM companies").fetchall()
    text = "\n".join(
        f"🏢 **{r['name']}** — {r['owner']}"
        for r in rows
    ) or "No companies registered."

    await interaction.response.send_message(
        embed=embed("WORLD BUSINESS DIRECTORY", text)
    )


# ==========================================
# 7. ISLANDS & KINGDOMS
# ==========================================

island_group = app_commands.Group(
    name="island", description="World island database"
)

@island_group.command(name="add", description="Register an island")
async def island_add(interaction, name: str, ruler: str, region: str):
    if not await admin_required(interaction):
        return

    execute(
        "INSERT OR REPLACE INTO islands(name,ruler,region) VALUES(?,?,?)",
        (name, ruler, region)
    )
    await interaction.response.send_message(
        embed=embed("🌍 ISLAND REGISTER",
                    f"Island: **{name}**\nRuler: {ruler}\nRegion: {region}")
    )


@island_group.command(name="list", description="List registered islands")
async def island_list(interaction):
    rows = execute("SELECT * FROM islands").fetchall()
    text = "\n".join(
        f"🏝️ **{r['name']}** — {r['region']} · Ruler: {r['ruler']}"
        for r in rows
    ) or "No islands registered."

    await interaction.response.send_message(
        embed=embed("WORLD MAP DATABASE", text)
    )


# ==========================================
# 8. EVENTS & WARS
# ==========================================

event_group = app_commands.Group(
    name="event", description="World events"
)

@event_group.command(name="create", description="Create a world event")
async def event_create(interaction, name: str, description: str):
    if not await admin_required(interaction):
        return

    execute(
        "INSERT INTO events(name,description,status,created) VALUES(?,?,?,?)",
        (name, description, "ACTIVE", datetime.now().isoformat())
    )
    await interaction.response.send_message(
        embed=embed(f"⚔️ WORLD EVENT: {name}", description)
    )


@event_group.command(name="list", description="List world events")
async def event_list(interaction):
    rows = execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT 15"
    ).fetchall()

    text = "\n".join(
        f"**#{r['id']} {r['name']}** · {r['status']}\n{r['description']}"
        for r in rows
    ) or "No events."

    await interaction.response.send_message(
        embed=embed("WORLD EVENTS", text)
    )


@event_group.command(name="end", description="End a world event")
async def event_end(interaction, event_id: int):
    if not await admin_required(interaction):
        return

    execute(
        "UPDATE events SET status='ENDED' WHERE id=?",
        (event_id,)
    )
    await interaction.response.send_message("Event ended.")


# ==========================================
# 9. DEVIL FRUITS
# ==========================================

fruit_group = app_commands.Group(
    name="fruit", description="Devil Fruit database"
)

@fruit_group.command(name="add", description="Register a Devil Fruit")
async def fruit_add(interaction, name: str, fruit_type: str, ability: str):
    if not await admin_required(interaction):
        return

    execute(
        "INSERT OR REPLACE INTO fruits(name,fruit_type,ability,owner) VALUES(?,?,?,?)",
        (name, fruit_type, ability, "Unclaimed")
    )
    await interaction.response.send_message(
        embed=embed("🍈 DEVIL FRUIT REGISTER",
                    f"**{name}**\nType: {fruit_type}\nAbility: {ability}")
    )


@fruit_group.command(name="give", description="Assign a Devil Fruit")
async def fruit_give(interaction, name: str, owner: str):
    if not await admin_required(interaction):
        return

    result = execute(
        "UPDATE fruits SET owner=? WHERE name=?",
        (owner, name)
    )
    if result.rowcount == 0:
        await interaction.response.send_message("Fruit not found.")
        return

    await interaction.response.send_message(
        f"🍈 {name} assigned to {owner}."
    )


@fruit_group.command(name="list", description="List Devil Fruits")
async def fruit_list(interaction):
    rows = execute("SELECT * FROM fruits").fetchall()
    text = "\n".join(
        f"🍈 **{r['name']}** · {r['fruit_type']} · Owner: {r['owner']}"
        for r in rows
    ) or "No fruits registered."

    await interaction.response.send_message(
        embed=embed("DEVIL FRUIT ENCYCLOPEDIA", text)
    )


# ==========================================
# 10. MODERATION
# ==========================================

mod_group = app_commands.Group(
    name="mod", description="Server moderation"
)

@mod_group.command(name="ban", description="Ban a member")
@app_commands.default_permissions(ban_members=True)
async def mod_ban(interaction, member: discord.Member, reason: str = "No reason provided"):
    if not await mod_required(interaction):
        return
    if member.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
        await interaction.response.send_message(
            "You cannot moderate a member with an equal or higher role.",
            ephemeral=True
        )
        return

    await member.ban(reason=reason)
    log_action("BAN", interaction.user, member, reason)
    await interaction.response.send_message(
        embed=embed("🔨 MEMBER BANNED", f"{member} — {reason}")
    )


@mod_group.command(name="kick", description="Kick a member")
@app_commands.default_permissions(kick_members=True)
async def mod_kick(interaction, member: discord.Member, reason: str = "No reason provided"):
    if not await mod_required(interaction):
        return
    if member.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
        await interaction.response.send_message(
            "You cannot moderate a member with an equal or higher role.",
            ephemeral=True
        )
        return

    await member.kick(reason=reason)
    log_action("KICK", interaction.user, member, reason)
    await interaction.response.send_message(
        embed=embed("MEMBER KICKED", f"{member} — {reason}")
    )


@mod_group.command(name="timeout", description="Timeout a member")
@app_commands.default_permissions(moderate_members=True)
async def mod_timeout(interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 40320], reason: str = "No reason provided"):
    if not await mod_required(interaction):
        return
    if member.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
        await interaction.response.send_message(
            "You cannot moderate a member with an equal or higher role.",
            ephemeral=True
        )
        return

    await member.timeout(timedelta(minutes=minutes), reason=reason)
    log_action("TIMEOUT", interaction.user, member, reason)
    await interaction.response.send_message(
        f"⏱️ {member.mention} timed out for {minutes} minutes."
    )


@mod_group.command(name="warn", description="Warn a member")
async def mod_warn(interaction, member: discord.Member, reason: str):
    if not await mod_required(interaction):
        return

    execute(
        "INSERT INTO warnings(user_id,moderator,reason,created) VALUES(?,?,?,?)",
        (member.id, str(interaction.user), reason, datetime.now().isoformat())
    )
    log_action("WARN", interaction.user, member, reason)
    await interaction.response.send_message(
        f"⚠️ {member.mention} has received a warning: {reason}"
    )


@mod_group.command(name="warnings", description="View a member's warnings")
async def mod_warnings(interaction, member: discord.Member):
    if not await mod_required(interaction):
        return

    rows = execute(
        "SELECT * FROM warnings WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (member.id,)
    ).fetchall()

    text = "\n".join(
        f"#{r['id']} · {r['reason']} · {r['moderator']}"
        for r in rows
    ) or "No warnings."

    await interaction.response.send_message(
        embed=embed(f"WARNINGS: {member}", text), ephemeral=True
    )


@mod_group.command(name="clear", description="Delete recent messages")
@app_commands.default_permissions(manage_messages=True)
async def mod_clear(interaction, amount: app_commands.Range[int, 1, 100]):
    if not await mod_required(interaction):
        return

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(
        f"🧹 Deleted {len(deleted)} messages.", ephemeral=True
    )


@mod_group.command(name="lock", description="Lock the current channel")
async def mod_lock(interaction):
    if not await mod_required(interaction):
        return

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        send_messages=False
    )
    await interaction.response.send_message("🔒 Channel locked.")


@mod_group.command(name="unlock", description="Unlock the current channel")
async def mod_unlock(interaction):
    if not await mod_required(interaction):
        return

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        send_messages=None
    )
    await interaction.response.send_message("🔓 Channel unlocked.")


# ==========================================
# 11. COMMUNITY ECONOMY
# ==========================================

economy_group = app_commands.Group(
    name="economy", description="Community Berry economy"
)

@economy_group.command(name="balance", description="Check your Berry balance")
async def economy_balance(interaction, member: discord.Member = None):
    member = member or interaction.user
    row = execute(
        "SELECT balance FROM economy WHERE user_id=?",
        (member.id,)
    ).fetchone()

    balance = row["balance"] if row else 0
    await interaction.response.send_message(
        embed=embed("💰 BERRY ACCOUNT",
                    f"{member.mention}\nBalance: **฿{balance:,}**")
    )


@economy_group.command(name="pay", description="Transfer Berries")
async def economy_pay(interaction, member: discord.Member, amount: app_commands.Range[int, 1, 1000000000]):
    if member.id == interaction.user.id or member.bot:
        await interaction.response.send_message("Invalid recipient.", ephemeral=True)
        return

    sender = execute(
        "SELECT balance FROM economy WHERE user_id=?",
        (interaction.user.id,)
    ).fetchone()

    if not sender or sender["balance"] < amount:
        await interaction.response.send_message(
            "Not enough Berries.", ephemeral=True
        )
        return

    execute(
        "UPDATE economy SET balance=balance-? WHERE user_id=?",
        (amount, interaction.user.id)
    )
    execute(
        """INSERT INTO economy(user_id,balance) VALUES(?,?)
        ON CONFLICT(user_id) DO UPDATE SET balance=balance+excluded.balance""",
        (member.id, amount)
    )
    await interaction.response.send_message(
        f"💰 {interaction.user.mention} paid ฿{amount:,} to {member.mention}."
    )


@economy_group.command(name="give", description="Give Berries to a member")
async def economy_give(interaction, member: discord.Member, amount: app_commands.Range[int, 1, 1000000000]):
    if not await admin_required(interaction):
        return

    execute(
        """INSERT INTO economy(user_id,balance) VALUES(?,?)
        ON CONFLICT(user_id) DO UPDATE SET balance=balance+excluded.balance""",
        (member.id, amount)
    )
    log_action("BERRIES GIVEN", interaction.user, member, str(amount))
    await interaction.response.send_message(
        f"💰 Added ฿{amount:,} to {member.mention}."
    )


# ==========================================
# 12. LEVEL SYSTEM
# ==========================================

level_group = app_commands.Group(
    name="level", description="Community levels"
)

@level_group.command(name="profile", description="View your level profile")
async def level_profile(interaction, member: discord.Member = None):
    member = member or interaction.user

    row = execute(
        "SELECT points FROM xp WHERE user_id=?",
        (member.id,)
    ).fetchone()

    points = row["points"] if row else 0
    level = points // 100

    await interaction.response.send_message(
        embed=embed("⭐ MEMBER PROFILE",
                    f"**{member.display_name}**\n"
                    f"XP: {points}\nLevel: {level}")
    )


# ==========================================
# 13. WORLD DATABASE
# ==========================================

world_group = app_commands.Group(
    name="world", description="World information"
)

@world_group.command(name="stats", description="World Economy database statistics")
async def world_stats(interaction):
    tables = [
        "news", "bounties", "yonkou", "marine",
        "government", "pirates", "companies",
        "islands", "events", "fruits"
    ]

    text = ""
    for table in tables:
        count = execute(
            f"SELECT COUNT(*) AS total FROM {table}"
        ).fetchone()["total"]
        text += f"**{table.upper()}:** {count}\n"

    await interaction.response.send_message(
        embed=embed("🌍 WORLD ECONOMY STATISTICS", text)
    )


# ==========================================
# 14. HELP & ADMIN
# ==========================================

@bot.tree.command(name="help", description="Show all WORLD ECONOMY systems")
async def help_command(interaction):
    description = """
📰 **NEWS:** `/news`
💰 **BOUNTY:** `/bounty`
👑 **YONKOU:** `/yonkou`
🏴‍☠️ **PIRATES:** `/pirate`
⚓ **MARINE:** `/marine`
🏛️ **GOVERNMENT:** `/government`
🏢 **COMPANY:** `/company`
🌍 **ISLANDS:** `/island`
⚔️ **EVENTS:** `/event`
🍈 **DEVIL FRUITS:** `/fruit`
🔨 **MODERATION:** `/mod`
💰 **ECONOMY:** `/economy`
⭐ **LEVELS:** `/level`
📊 **WORLD STATS:** `/world stats`
"""
    await interaction.response.send_message(
        embed=embed("WORLD ECONOMY COMMAND CENTER", description),
        ephemeral=True
    )


@bot.tree.command(name="setup", description="Check bot setup")
async def setup_command(interaction):
    if not await admin_required(interaction):
        return

    await interaction.response.send_message(
        embed=embed("SYSTEM STATUS",
                    f"Bot: ONLINE\n"
                    f"Database: CONNECTED\n"
                    f"Server: {interaction.guild.name}\n"
                    f"Commands: SYNCHRONIZED")
    )


@bot.tree.command(name="logs", description="View recent administration logs")
async def logs_command(interaction):
    if not await admin_required(interaction):
        return

    rows = execute(
        "SELECT * FROM logs ORDER BY id DESC LIMIT 10"
    ).fetchall()

    text = "\n".join(
        f"**{r['action']}** · {r['actor']} → {r['target']}\n{r['details']}"
        for r in rows
    ) or "No logs available."

    await interaction.response.send_message(
        embed=embed("📋 ADMINISTRATION LOGS", text),
        ephemeral=True
    )


# ==========================================
# REGISTER COMMAND GROUPS
# ==========================================

for group in [
    news_group,
    bounty_group,
    pirate_group,
    yonkou_group,
    marine_group,
    government_group,
    company_group,
    island_group,
    event_group,
    fruit_group,
    mod_group,
    economy_group,
    level_group,
    world_group
]:
    bot.tree.add_command(group)


# ==========================================
# ERROR HANDLING
# ==========================================

@bot.tree.error
async def on_app_command_error(interaction, error):
    print("Command error:", repr(error))

    message = "An error occurred while executing this command."

    if isinstance(error, app_commands.MissingPermissions):
        message = "⛔ You do not have the required Discord permissions."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


# ==========================================
# START BOT
# ==========================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN missing! Add your bot token to environment secrets."
    )

bot.run(TOKEN)
