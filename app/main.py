import os
import csv
import io
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer, BadSignature

from app.db import init_db, get_conn
from app.models import ReviewCreate

app = FastAPI(title="QR Feedback MVP")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
SECRET = os.environ.get("SESSION_SECRET", "dev-secret-change-this")
serializer = URLSafeSerializer(SECRET, salt="admin-session")


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse("/r/demo")


@app.get("/favicon.ico")
def favicon():
    # optional; avoid log noise
    return RedirectResponse("/static/favicon.ico")


def require_admin(request: Request):
    token = request.cookies.get("admin_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        data = serializer.loads(token)
        if data.get("admin") is True:
            return True
    except BadSignature:
        pass
    raise HTTPException(status_code=401, detail="Not authenticated")


def get_business_by_slug(slug: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM businesses WHERE slug = ?;", (slug,))
    row = cur.fetchone()
    conn.close()
    return row


def get_or_create_business(slug: str):
    row = get_business_by_slug(slug)
    if row:
        return row

    conn = get_conn()
    cur = conn.cursor()
    name = slug.replace("-", " ").title()
    cur.execute("INSERT INTO businesses (slug, name) VALUES (?, ?);", (slug, name))
    conn.commit()
    cur.execute("SELECT * FROM businesses WHERE slug = ?;", (slug,))
    row = cur.fetchone()
    conn.close()
    return row


# -----------------------
# Public review form
# -----------------------
@app.get("/r/{slug}", response_class=HTMLResponse)
def review_form(request: Request, slug: str):
    biz = get_or_create_business(slug)
    return templates.TemplateResponse("review_form.html", {
        "request": request,
        "business": dict(biz),
        "success": request.query_params.get("success") == "1",
    })


@app.post("/r/{slug}")
def submit_review_form(
    slug: str,
    rating: int = Form(...),
    comment: str = Form(""),
    contact_email: str = Form(""),
):
    payload = ReviewCreate(
        business_slug=slug,
        rating=int(rating),
        comment=comment.strip() or None,
        contact_email=contact_email.strip() or None,
    )
    create_review(payload)
    return RedirectResponse(url=f"/r/{slug}?success=1", status_code=303)


# -----------------------
# API
# -----------------------
@app.post("/api/reviews")
def create_review(payload: ReviewCreate):
    biz = get_or_create_business(payload.business_slug)
    flagged = 1 if payload.rating <= 2 else 0

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reviews (business_id, rating, comment, contact_email, flagged)
        VALUES (?, ?, ?, ?, ?);
    """, (biz["id"], payload.rating, payload.comment, payload.contact_email, flagged))
    conn.commit()
    conn.close()

    return {"ok": True, "flagged": bool(flagged)}


# -----------------------
# Admin auth
# -----------------------
@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": None})


@app.post("/admin/login", response_class=HTMLResponse)
def admin_login(request: Request, password: str = Form(...)):
    if not ADMIN_PASSWORD:
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "error": "Server missing ADMIN_PASSWORD env var"
        })

    if password != ADMIN_PASSWORD:
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "error": "Wrong password"
        })

    token = serializer.dumps({"admin": True})
    resp = RedirectResponse(url="/admin", status_code=303)
    resp.set_cookie("admin_session", token, httponly=True, samesite="lax")
    return resp


@app.get("/admin/logout")
def admin_logout():
    resp = RedirectResponse(url="/admin/login", status_code=303)
    resp.delete_cookie("admin_session")
    return resp


# -----------------------
# Admin dashboard
# -----------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    min_rating: int = 1,
    business: str = "",
    _: bool = Depends(require_admin),
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT slug, name FROM businesses ORDER BY name;")
    businesses = [dict(r) for r in cur.fetchall()]

    query = """
    SELECT r.*, b.slug AS business_slug, b.name AS business_name
    FROM reviews r
    JOIN businesses b ON b.id = r.business_id
    WHERE r.rating >= ?
    """
    params = [min_rating]

    if business:
        query += " AND b.slug = ?"
        params.append(business)

    query += " ORDER BY r.created_at DESC LIMIT 200;"
    cur.execute(query, tuple(params))
    reviews = [dict(r) for r in cur.fetchall()]

    conn.close()

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "reviews": reviews,
        "businesses": businesses,
        "min_rating": min_rating,
        "business": business,
    })


@app.post("/admin/reviews/{review_id}/seen")
def mark_seen(review_id: int, _: bool = Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE reviews SET seen = 1 WHERE id = ?;", (review_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=303)


@app.get("/admin/export.csv")
def export_csv(_: bool = Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    SELECT b.slug AS business_slug, b.name AS business_name,
           r.rating, r.comment, r.contact_email, r.created_at, r.seen, r.flagged
    FROM reviews r
    JOIN businesses b ON b.id = r.business_id
    ORDER BY r.created_at DESC;
    """)
    rows = cur.fetchall()
    conn.close()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["business_slug", "business_name", "rating", "comment", "contact_email", "created_at", "seen", "flagged"])
    for r in rows:
        w.writerow([
            r["business_slug"], r["business_name"], r["rating"], r["comment"],
            r["contact_email"], r["created_at"], r["seen"], r["flagged"]
        ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reviews.csv"}
    )
