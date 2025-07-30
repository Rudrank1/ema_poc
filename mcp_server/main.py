from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from aws_tools import create_bucket_with_options, apply_policy

app = FastAPI()

class BucketRequest(BaseModel):
    bucket_name: str
    versioning: bool = False
    tags: Optional[Dict[str, str]] = None
    public_access_block: Optional[Dict[str, bool]] = None
    policy: Optional[str] = None

class PolicyRequest(BaseModel):
    bucket_name: str
    policy_json: str

@app.post("/create_bucket")
def create_bucket(req: BucketRequest):
    try:
        result = create_bucket_with_options(
            req.bucket_name,
            req.versioning,
            tags=req.tags,
            public_access_block=req.public_access_block,
            policy=req.policy
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/apply_policy")
def apply_policy_endpoint(req: PolicyRequest):
    try:
        result = apply_policy(req.bucket_name, req.policy_json)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))