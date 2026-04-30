def test_create_and_list_analysis(client, auth_headers, sample_pdf):
    with sample_pdf.open("rb") as f:
        r = client.post(
            "/api/analyses",
            headers=auth_headers,
            files={"file": ("tiny.pdf", f, "application/pdf")},
            data={"codigo_curso": "22A14"},
        )
    assert r.status_code == 202, r.text
    aid = r.json()["id"]

    r = client.get("/api/analyses", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == aid
    assert items[0]["status"] == "done"  # SYNC_MODE corre inline

    r = client.get(f"/api/analyses/{aid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["report"]["modelo"] == "qwen2.5:14b"


def test_reject_non_pdf(client, auth_headers, tmp_path):
    txt = tmp_path / "bad.txt"
    txt.write_text("not a pdf")
    with txt.open("rb") as f:
        r = client.post(
            "/api/analyses",
            headers=auth_headers,
            files={"file": ("bad.txt", f, "text/plain")},
        )
    assert r.status_code == 400


def test_user_isolation(client, sample_pdf):
    a = client.post("/api/auth/register", json={"email": "alice@t.com", "password": "password123"}).json()
    b = client.post("/api/auth/register", json={"email": "bob@t.com", "password": "password123"}).json()
    headers_a = {"Authorization": f"Bearer {a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {b['access_token']}"}

    with sample_pdf.open("rb") as f:
        r = client.post("/api/analyses", headers=headers_a, files={"file": ("x.pdf", f, "application/pdf")})
    aid = r.json()["id"]

    r = client.get(f"/api/analyses/{aid}", headers=headers_b)
    assert r.status_code == 404

    r = client.get("/api/analyses", headers=headers_b)
    assert r.json() == []


def test_delete_analysis(client, auth_headers, sample_pdf):
    with sample_pdf.open("rb") as f:
        aid = client.post(
            "/api/analyses",
            headers=auth_headers,
            files={"file": ("x.pdf", f, "application/pdf")},
        ).json()["id"]

    r = client.delete(f"/api/analyses/{aid}", headers=auth_headers)
    assert r.status_code in (204, 200)

    r = client.get(f"/api/analyses/{aid}", headers=auth_headers)
    assert r.status_code == 404


# --- Validacion sincrona "no es un PDA" ---


def test_reject_non_pda_with_chat_message(client, auth_headers, sample_pdf, monkeypatch):
    """Si el clasificador rechaza, el endpoint devuelve 422 con detail estructurado."""
    import pda_classifier

    monkeypatch.setattr(
        pda_classifier,
        "clasificar_documento",
        lambda secciones: (
            False,
            "NOT_A_PDA",
            "Este documento no parece ser un PDA. No reconocí ninguna sección canónica.",
        ),
    )

    with sample_pdf.open("rb") as f:
        r = client.post(
            "/api/analyses",
            headers=auth_headers,
            files={"file": ("manual.pdf", f, "application/pdf")},
        )

    assert r.status_code == 422, r.text
    body = r.json()
    assert isinstance(body["detail"], dict)
    assert body["detail"]["code"] == "NOT_A_PDA"
    assert "PDA" in body["detail"]["message"]


def test_reject_corrupt_pdf_with_parse_error(client, auth_headers, sample_pdf, monkeypatch):
    """Si Docling falla parseando, devuelve 422 PDF_PARSE_ERROR."""
    import pdf_parser
    from common.exceptions import PDFParseError

    def _raise(_):
        raise PDFParseError("Docling no pudo abrir el archivo")

    monkeypatch.setattr(pdf_parser, "parsear_pda", _raise)

    with sample_pdf.open("rb") as f:
        r = client.post(
            "/api/analyses",
            headers=auth_headers,
            files={"file": ("corrupto.pdf", f, "application/pdf")},
        )

    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "PDF_PARSE_ERROR"


def test_rejection_does_not_create_analysis_row(
    client, auth_headers, sample_pdf, monkeypatch
):
    """Un upload rechazado no debe dejar una fila huerfana en la DB."""
    import pda_classifier

    monkeypatch.setattr(
        pda_classifier,
        "clasificar_documento",
        lambda secciones: (False, "EMPTY_OR_SCANNED", "PDF vacio"),
    )

    with sample_pdf.open("rb") as f:
        client.post(
            "/api/analyses",
            headers=auth_headers,
            files={"file": ("x.pdf", f, "application/pdf")},
        )

    # La lista del usuario debe estar vacia: el rechazo no persiste.
    r = client.get("/api/analyses", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []
