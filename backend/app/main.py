from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="家庭财务小管家 API", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/transactions", response_model=list[schemas.TransactionOut])
def get_transactions(db: Session = Depends(get_db)):
    return crud.list_transactions(db)


@app.post("/transactions", response_model=schemas.TransactionOut)
def create_transaction(
    payload: schemas.TransactionCreate, db: Session = Depends(get_db)
):
    return crud.create_transaction(db, payload)


@app.delete("/transactions/{txn_id}")
def remove_transaction(txn_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_transaction(db, txn_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"message": "删除成功"}


@app.get("/stats/category/{txn_type}", response_model=list[schemas.CategorySummaryItem])
def get_category_summary(txn_type: str, db: Session = Depends(get_db)):
    if txn_type not in {"income", "expense"}:
        raise HTTPException(status_code=400, detail="txn_type 必须是 income 或 expense")
    return crud.summary_by_category(db, txn_type)


@app.get("/stats/monthly", response_model=list[schemas.MonthlySummaryItem])
def get_monthly_summary(db: Session = Depends(get_db)):
    return crud.summary_by_month(db)
