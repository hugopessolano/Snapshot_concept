import time 
from fastapi import FastAPI, UploadFile 
from fastapi.exceptions import HTTPException 
from fastapi.responses import FileResponse 
import uvicorn 
import json 
import os 
from main import ExecutionManager
from auxiliary_functions import save_json_data

app = FastAPI() 
BASE_DIR = os.path.dirname(os.path.realpath(__file__)) 
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads") 
timestr = time.strftime("%Y%m%d-%H%M%S") 

@app.get("/") 
def read_root(): 
    return {"Hello": "FastAPI"} 

@app.post("/restore") 
def upload_file(file: UploadFile, store_id:str, access_token:str): 
    if file.content_type != "application/json": 
        raise HTTPException(400, detail="Invalid document type") 
    else: 
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        uploaded_file = os.path.join(UPLOAD_DIR, file.filename)
        data = json.loads(file.file.read())
        save_json_data(uploaded_file, data)
        
        execution_manager = ExecutionManager(store_id, access_token)
        execution_manager.build_fetched_products_json()
        execution_manager.load_json_file(uploaded_file)
        
        results = execution_manager.execute_snapshot_restore()
    
    #return {"content": data, "filename": file.filename} 

@app.post("/snapshot") 
def create_snapshot(store_id:str, access_token:str): 
    execution_manager = ExecutionManager(store_id, access_token)
    execution_manager.build_fetched_products_json()
    json_file = execution_manager.save_json()
    
    return FileResponse( path=json_file, media_type="application/json", filename=os.path.basename(json_file), ) 




if __name__ == "__main__": 
    uvicorn.run(app, host="127.0.0.1", port=8000)