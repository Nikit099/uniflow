import sys

import httpx


def login(client: httpx.Client, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/demo/login", json={"username": username, "password": password}
    )
    response.raise_for_status()
    return str(response.json()["csrf_token"])


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    student = httpx.Client(base_url=base_url)
    staff = httpx.Client(base_url=base_url)
    student_csrf = login(student, "student", "student123")
    staff_csrf = login(staff, "staff", "staff123")
    student_headers = {"X-CSRF-Token": student_csrf}
    staff_headers = {"X-CSRF-Token": staff_csrf}

    cases = student.get("/api/v1/cases").json()
    case_id = cases[0]["id"]
    case = student.get(f"/api/v1/cases/{case_id}").json()
    if case["status"] != "IN_PROGRESS":
        raise RuntimeError("Run make demo-reset before E2E")
    for item in case["requirements"]:
        response = student.post(
            f"/api/v1/cases/{case_id}/documents",
            headers=student_headers,
            data={
                "case_requirement_id": item["id"],
                "document_type": item["requirement"]["code"],
            },
            files={
                "file": (
                    f"{item['id']}.pdf",
                    b"%PDF-1.4\n% synthetic demo\n",
                    "application/pdf",
                )
            },
        )
        response.raise_for_status()
    student.post(
        f"/api/v1/cases/{case_id}/submit", headers=student_headers
    ).raise_for_status()

    review = staff.get(f"/api/v1/staff/cases/{case_id}").json()
    for item in review["requirements"][:2]:
        staff.post(
            f"/api/v1/staff/requirements/{item['id']}/accept",
            headers=staff_headers,
            json={"version": item["version"]},
        ).raise_for_status()
    problem = review["requirements"][2]
    staff.post(
        f"/api/v1/staff/requirements/{problem['id']}/request-changes",
        headers=staff_headers,
        json={
            "version": problem["version"],
            "reason": "Missing reverse side in the demo file",
            "reason_code": "missing_page",
        },
    ).raise_for_status()

    corrected_case = student.get(f"/api/v1/cases/{case_id}").json()
    corrected = next(
        item
        for item in corrected_case["requirements"]
        if item["status"] == "CHANGES_REQUESTED"
    )
    student.post(
        f"/api/v1/cases/{case_id}/documents",
        headers=student_headers,
        data={
            "case_requirement_id": corrected["id"],
            "document_type": corrected["requirement"]["code"],
        },
        files={
            "file": (
                "corrected.pdf",
                b"%PDF-1.4\n% corrected synthetic demo\n",
                "application/pdf",
            )
        },
    ).raise_for_status()
    student.post(
        f"/api/v1/cases/{case_id}/submit", headers=student_headers
    ).raise_for_status()

    final_review = staff.get(f"/api/v1/staff/cases/{case_id}").json()
    final_item = next(
        item for item in final_review["requirements"] if item["id"] == corrected["id"]
    )
    staff.post(
        f"/api/v1/staff/requirements/{final_item['id']}/accept",
        headers=staff_headers,
        json={"version": final_item["version"]},
    ).raise_for_status()
    verified = staff.post(
        f"/api/v1/staff/cases/{case_id}/verify", headers=staff_headers
    )
    verified.raise_for_status()
    assert verified.json()["status"] == "VERIFIED_BY_UNIVERSITY"
    print(f"Primary E2E passed for case {case_id}")


if __name__ == "__main__":
    main()
