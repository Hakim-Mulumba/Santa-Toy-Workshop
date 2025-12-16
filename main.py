from fastapi import FastAPI, Request, Form, WebSocket
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json

from workshop import Workshop, Toy, Elf, Order

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

workshop = Workshop()

# Setup demo data
workshop.add_toy(Toy("Teddy Bear", "Soft", 30, 12))
workshop.add_toy(Toy("Robot", "Electronics", 50, 6))

workshop.add_elf(Elf("Buddy", {"Soft"}, 120))
workshop.add_elf(Elf("Jingle", {"Electronics"}, 100))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Serve the project's root index.html as a static file
    return FileResponse("index.html", media_type="text/html")


@app.get("/PROJECT_DOCUMENTATION.txt")
async def get_documentation():
    return FileResponse("PROJECT_DOCUMENTATION.txt", media_type="text/plain")


@app.post("/add_order", response_class=HTMLResponse)
async def add_order(
    request: Request,
    child: str = Form(...),
    toy: str = Form(...),
    priority: int = Form(...),
    address: str = Form(...)
):
    try:
        workshop.add_order(Order(child, toy, priority, address))
    except Exception as e:
        return HTMLResponse(str(e), status_code=400)
    return RedirectResponse(url='/', status_code=303)


# --- JSON API endpoints for frontend
@app.get("/api/state")
async def api_state():
    toys = [
        {"name": t.name, "category": t.category, "build_time": t.build_time, "stock": t.stock}
        for t in workshop.toys.values()
    ]
    orders = [
        {"child": o.child, "toy": o.toy, "priority": o.priority, "address": o.address, "message": o.message}
        for o in workshop.orders
    ]
    elves = [
        {"name": e.name, "skills": list(e.skills), "capacity": e.capacity, "assigned": [t.name for t in e.assigned_toys]}
        for e in workshop.elves
    ]
    return JSONResponse({"toys": toys, "orders": orders, "elves": elves})


@app.post("/api/add_toy")
async def api_add_toy(request: Request):
    data = await request.json()
    try:
        name = data["name"]
        category = data.get("category", "General")
        build_time = int(data.get("build_time", 10))
        stock = int(data.get("stock", 1))
        workshop.add_toy(Toy(name, category, build_time, stock))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse({"status": "ok"})


@app.post("/api/add_elf")
async def api_add_elf(request: Request):
    data = await request.json()
    try:
        name = data["name"]
        skills_raw = data.get("skills", "")
        skills = set([s.strip() for s in skills_raw.split(",") if s.strip()])
        capacity = int(data.get("capacity", 120))
        workshop.add_elf(Elf(name, skills, capacity))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse({"status": "ok"})


@app.post("/api/add_order")
async def api_add_order(request: Request):
    data = await request.json()
    try:
        child = data["child"]
        toy = data["toy"]
        priority = int(data.get("priority", 3))
        address = data.get("address", "")
        message = data.get("message", "")
        workshop.add_order(Order(child, toy, priority, address, message))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse({"status": "ok"})


@app.delete("/api/remove_toy/{toy_name}")
async def api_remove_toy(toy_name: str):
    try:
        workshop.remove_toy(toy_name)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse({"status": "ok"})


@app.delete("/api/cancel_order/{order_index}")
async def api_cancel_order(order_index: int):
    try:
        workshop.cancel_order(order_index)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse({"status": "ok"})


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()

    workshop.reserve_orders()
    workshop.assign_elves()

    await ws.send_text(json.dumps({
        "type": "status",
        "message": "Simulation started"
    }))

    async def run_elf(elf: Elf):
        for toy in elf.assigned_toys:
            await ws.send_text(json.dumps({
                "type": "log",
                "message": f"{elf.name} building {toy.name}"
            }))
            await asyncio.sleep(toy.build_time / 10)
            await ws.send_text(json.dumps({
                "type": "log",
                "message": f"{elf.name} finished {toy.name}"
            }))

    await asyncio.gather(*(run_elf(e) for e in workshop.elves))

    await ws.send_text(json.dumps({
        "type": "status",
        "message": "Simulation finished"
    }))
