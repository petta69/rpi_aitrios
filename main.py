from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import matplotlib.pyplot as plt
import aiofiles
import os
import asyncio
from logger.logger import Logger
import numpy as np
import json

app = FastAPI()

logger = Logger(level=5).get_logger()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

ThisHostIP = "172.17.2.110"
ThisHostPort = 5000
DATA_FILE = "data.json"
clients = []

async def read_data():
    data_numbers = []
    data_labels = []
    async with aiofiles.open(DATA_FILE, mode='r') as file:
        #data = await file.readlines()
        data = json.loads(await file.read())
        for key, value in data.items():
            data_labels.append(key)
            data_numbers.append(value)
    return data_labels, data_numbers

def create_plot(xData1, yData1):
    fontDict1 = {
        "family" : "Verdana",
        "weight" : "bold",
        "size" : 16
        }
    plt.rc("font", **fontDict1)
    # make the bar chart
    rlen1 = 1
    clen1 = 1
    width1 = 1024
    height1 = 360
    dpi1 = 72
    figsize1 = (width1/dpi1,height1/dpi1)
    fig1,ax1 = plt.subplots(rlen1,clen1,figsize=figsize1,dpi=dpi1)
    y_pos1 = np.arange(len(xData1))
    plt.bar(y_pos1, yData1)
    plt.xticks(y_pos1, xData1)
    plt.ylabel("Count")
    plt.xlabel("Type")
    plt.title("Count by Type")
    plot_path = 'static/plot.png'
    plt.savefig(plot_path)
    plt.close()
    return plot_path

async def notify_clients():
    data_label, data = await read_data()
    plot_path = create_plot(data_label, data)
    logger.debug(f"Sending updated plot: {plot_path}")
    for client in clients:
        await client.send_text(plot_path)

async def watch_file():
    last_mtime = os.path.getmtime(DATA_FILE)
    while True:
        await asyncio.sleep(1)
        current_mtime = os.path.getmtime(DATA_FILE)
        if current_mtime != last_mtime:
            last_mtime = current_mtime
            logger.debug("Data file updated, notifying clients...")
            await notify_clients()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(watch_file())

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        clients.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
