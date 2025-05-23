from datetime import datetime

import discord
import ezcord
import uvicorn
from discord.ext.ipc import Client
from fastapi import Cookie, FastAPI, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from contextlib import asynccontextmanager
from backend import DiscordAuth, db, feature_db, welc

CLIENT_ID = 
CLIENT_SECRET = 
REDIRECT_URI = "http://localhost:1111/callback"
LOGIN_URL = 
INVITE_LINK

@asynccontextmanager
async def on_startup(app: FastAPI):
    await api.setup()
    await db.setup()
    await feature_db.setup()
    await welc.setup()
    yield

    await api.close()
    # Hier kann noch selbst eine Methode, die je nach Datenbank variiert, hinzugefügt werden, um die Datenbank zu "schließen"

app = FastAPI(lifespan=on_startup)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend")

ipc = Client(secret_key="keks")
api = DiscordAuth(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)


@app.get("/")
async def home(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id and await db.get_session(session_id):
        return RedirectResponse(url="/guilds")

    guild_count = await ipc.request("guild_count")
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "count": guild_count.response,
            "login_url": LOGIN_URL
        }
    )


@app.get("/callback")
async def callback(code: str):
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    result = await api.get_token_response(data)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid Auth Code")

    token, refresh_token, expires_in = result
    user = await api.get_user(token)
    user_id = user.get("id")

    session_id = await db.add_session(token, refresh_token, expires_in, user_id)

    response = RedirectResponse(url="/guilds")
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return response


@app.get("/guilds")
async def guilds(request: Request):
    session_id = request.cookies.get("session_id")
    session = await db.get_session(session_id)
    if not session_id or not session:
        raise HTTPException(status_code=401, detail="no auth")

    token, refresh_token, token_expires_at = session

    user = await api.get_user(token)
    if datetime.now() > token_expires_at or user.get("code") == 0:
        if await api.reload(session_id, refresh_token):
            RedirectResponse(url="/guilds")
        else:
            RedirectResponse(url="/logout")

    if "id" not in user:
        return RedirectResponse(url="/logout")

    user_guilds = await api.get_guilds(token)
    bot_guilds = await ipc.request("bot_guilds")
    perms = []

    for guild in user_guilds:
        if guild["id"] in bot_guilds.response["data"]:
            guild["url"] = "/server/" + str(guild["id"])
        else:
            guild["url"] = INVITE_LINK + f"&guild_id={guild['id']}"

        if guild["icon"]:
            guild["icon"] = "https://cdn.discordapp.com/icons/" + guild["id"] + "/" + guild["icon"]
        else:
            guild["icon"] = ezcord.random_avatar()

        is_admin = discord.Permissions(int(guild["permissions"])).administrator
        if is_admin or guild["owner"]:
            perms.append(guild)

    return templates.TemplateResponse(
        "guilds.html",
        {
            "request": request,
            "global_name": user["global_name"],
            "guilds": perms
        }
    )


@app.get("/server/{guild_id}")
async def server(request: Request, guild_id: int):
    session_id = request.cookies.get("session_id")
    if not session_id or not await db.get_session(session_id):
        raise HTTPException(status_code=401, detail="no auth")

    stats = await ipc.request("guild_stats", guild_id=guild_id)
    setting = await feature_db.get_setting(guild_id, "example_feature")
    if setting:
        feature_txt = "Das Feature ist aktiviert"
    else:
        feature_txt = "Das Feature ist deaktiviert"

    return templates.TemplateResponse(
        "server.html",
        {
            "request": request,
            "name": stats.response["name"],
            "count": stats.response["member_count"],
            "id": guild_id,
            "feature": feature_txt,
        },
    )


@app.get("/server/{guild_id}/settings/welcome")
async def change_settings(request: Request,guild_id: int, session_id: str = Cookie(None)):
    user_id = await db.get_user_id(session_id)
    if not session_id or not user_id:
        raise HTTPException(status_code=401, detail="no auth")

    perms = await ipc.request("check_perms", guild_id=guild_id, user_id=user_id)

    if perms.response["perms"]:
        guild_items = await ipc.request("get_guild_items",guild_id=guild_id)
        channels = guild_items.response["channels"]
        welc_channel = await welc.get_welc(guild_id)
        welc_channel = await ipc.request("get_channel_name",guild_id=guild_id,channel_id=welc_channel)
        welc_message = await welc.get_welc_message(guild_id)


        return templates.TemplateResponse(
            "welcome.html",
            {
                "request": request,
                "channels": channels,
                "welc_channel": welc_channel.response,
                "guild_id":  guild_id,
                "welc_message": welc_message,
            }
        )
        
        
    else:
        return {"error": "Du hast keinen Zugriff auf diesen Server"}


@app.post("/server/{guild_id}/settings/welcome/channel")
async def channel(request:Request,guild_id:int,session_id: str = Cookie(None), channel: str = Form(...)):
    user_id = await db.get_user_id(session_id)
    if not session_id or not user_id:
        raise HTTPException(status_code=401,detail="no auth")
    
    perms = await ipc.request("check_perms", guild_id=guild_id, user_id=user_id)
    if perms.response["perms"]:
        await welc.set_welc(guild_id,channel)
        return templates.TemplateResponse(
            "back.html",
            {
                "request": request,
                "guild_id": guild_id,
            }
        )
    
@app.post("/server/{guild_id}/settings/welcome/msg")
#die methode für das setzen der verschiedenen settings aus dem formular
#parameter ausm formular und den cookies
async def join_message(request:Request,guild_id:int,session_id: str = Cookie(None), msg: str = Form(...)):
    #user id von der session getten
    user_id = await db.get_user_id(session_id)
    if not session_id or not user_id:
        raise HTTPException(status_code=401, detail="no auth")

    perms = await ipc.request("check_perms", guild_id=guild_id, user_id=user_id)
    
    if perms.response["perms"]:
        #halt die msg setzen mit dem aus dem formular
        await welc.set_welc_message(guild_id,msg)
        return templates.TemplateResponse(
            "back.html",
            {
                "request": request,
                "guild_id": guild_id,
            }
        )


@app.get("/logout")
async def logout(session_id: str = Cookie(None)):
    session = await db.get_session(session_id)
    if not session_id or not session:
        raise HTTPException(status_code=401, detail="no auth")

    token, _, _ = session

    response = RedirectResponse("/")
    response.delete_cookie(key="session_id", httponly=True)

    await db.delete_session(session_id)
    await api.revoke_token(token)

    return response


@app.exception_handler(404)
async def error_redirect(_, __):
    return RedirectResponse("/")


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=1111, reload=True)
