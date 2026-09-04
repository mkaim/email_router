import os
from email.message import EmailMessage

import pytest

from router import route_issue

# Deliberately unambiguous messages so a small local model routes them reliably.
CASES = [
    {
        "id": "vpn-issue",
        "email": "jane.doe@example.com",
        "message": (
            "My work laptop will not connect to the company VPN since this "
            "morning and I cannot reach any internal systems or my email."
        ),
        "department": "it@example.com",
    },
    {
        "id": "password-reset",
        "email": "peter.pan@example.com",
        "message": (
            "I forgot my account password and cannot log into my workstation "
            "or my email."
        ),
        "department": "it@example.com",
    },
    {
        "id": "phishing-report",
        "email": "laura@example.com",
        "message": (
            "I received an email asking me to confirm my credentials. I think "
            "it is a phishing attempt."
        ),
        "department": "it@example.com",
    },
    {
        "id": "phone-broken",
        "email": "dave@example.com",
        "message": "My company phone fell on the floor and the screen is now black.",
        "department": "it@example.com",
    },
    {
        "id": "payslip-polish",
        "email": "jan.kowalski@example.com",
        "message": (
            "Nie otrzymałem paska wynagrodzeń za poprzedni miesiąc i moje "
            "wynagrodzenie nie wpłynęło na konto."
        ),
        "department": "kadry@example.com",
    },
    {
        "id": "leave-request-polish",
        "email": "katarzyna@example.com",
        "message": "Chciałabym złożyć wniosek o urlop wypoczynkowy w lipcu.",
        "department": "kadry@example.com",
    },
    {
        "id": "sick-leave",
        "email": "maria@example.com",
        "message": (
            "I was ill last week and need to submit my sick leave certificate."
        ),
        "department": "kadry@example.com",
    },
    {
        "id": "employment-contract-copy",
        "email": "tom@example.com",
        "message": "I would like to request a copy of my employment contract.",
        "department": "kadry@example.com",
    },
    {
        "id": "work-certificate",
        "email": "ewa@example.com",
        "message": "I need a work certificate for a bank loan application.",
        "department": "kadry@example.com",
    },
    {
        "id": "onboarding",
        "email": "anna.nowak@example.com",
        "message": (
            "I am starting next Monday and I have not received my onboarding "
            "documents or laptop setup instructions."
        ),
        "department": "human-resources@example.com",
    },
    {
        "id": "performance-review",
        "email": "greg@example.com",
        "message": (
            "I would like to schedule my annual performance review with my manager."
        ),
        "department": "human-resources@example.com",
    },
    {
        "id": "harassment-report",
        "email": "ola@example.com",
        "message": "I want to report ongoing harassment from a coworker.",
        "department": "human-resources@example.com",
    },
    {
        "id": "training-course",
        "email": "mark@example.com",
        "message": "How do I sign up for the mandatory compliance training?",
        "department": "human-resources@example.com",
    },
    {
        "id": "access-card",
        "email": "bob@example.com",
        "message": "My office access card stopped working and I cannot park in the garage.",
        "department": "help-desk@example.com",
    },
    {
        "id": "kitchen-coffee-machine",
        "email": "sara@example.com",
        "message": "The coffee machine in the third floor kitchen is broken.",
        "department": "help-desk@example.com",
    },
    {
        "id": "parking-badge",
        "email": "kuba@example.com",
        "message": "I lost my parking badge and need a replacement.",
        "department": "help-desk@example.com",
    },
    {
        "id": "ergonomic-chair",
        "email": "igor@example.com",
        "message": (
            "I need an ergonomic chair because my back hurts from the current one."
        ),
        "department": "help-desk@example.com",
    },
    {
        "id": "legal-contact",
        "email": "nina@example.com",
        "message": "Where can I find the contact details of the legal department?",
        "department": "other@example.com",
    },
    {
        "id": "german-vpn",
        "email": "hans@example.com",
        "message": (
            "Mein Laptop kann sich seit heute Morgen nicht mehr mit dem VPN verbinden."
        ),
        "department": "it@example.com",
    },
    {
        "id": "spanish-payslip",
        "email": "lucia@example.com",
        "message": (
            "No he recibido mi nómina del mes pasado y el pago no ha llegado "
            "a mi cuenta."
        ),
        "department": "kadry@example.com",
    },
]

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LLM_TESTS") != "1",
    reason="set RUN_LLM_TESTS=1 with a reachable OPENAI_BASE_URL to exercise the real model",
)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_llm_routes_to_expected_department(case):
    sent: list[EmailMessage] = []

    # RoutingResult is populated from the send_mail tool's arguments, so these
    # assertions verify the model called the tool with the right destination
    # and a non-empty subject.
    result = route_issue(
        case["email"],
        case["message"],
        send_email=sent.append,
        app_email="app@noreply.com",
    )

    assert result.department == case["department"]
    assert result.subject.strip()
    assert len(sent) == 1
