from uuid import uuid4

from sqlalchemy import func, select

from infrastructure.database.models import MovimentacaoEstoque
from tests.integration.test_central_guards import purchase as purchase


async def test_patch_invalidates_approval_is_idempotent_and_does_not_receive_stock(purchase, db):
    post, proposal, decision, _, _, _, tenant = purchase
    response = await post("conversation-draft", proposal | {"action": "read"})
    assert response.status_code == 200, response.text
    source = response.json()
    ref = source["conversation_draft"]["itens"][0]["item_ref"]
    update = proposal | {
        "action": "patch",
        "expected_version": source["version"],
        "incoming_message_id": str(uuid4()),
        "edits": [{"op": "set_item", "item_ref": ref, "field": "quantidade", "value": "3"}],
    }
    response = await post("conversation-draft", update)
    assert response.status_code == 200, response.text
    changed = response.json()
    assert changed["version"] == source["version"] + 1
    assert changed["state"] == "review"
    assert changed["summary_hash"] is None
    assert not changed["ready_for_review"]
    assert changed["conversation_draft"]["itens"][0]["quantidade"] == "3"
    assert (await post("decision", decision)).status_code == 409
    assert (await post("conversation-draft", update)).json()["version"] == changed["version"]
    assert (
        await post(
            "conversation-draft", update | {"edits": [{"op": "remove_item", "item_ref": ref}]}
        )
    ).status_code == 409
    assert (
        await post("conversation-draft", update | {"incoming_message_id": str(uuid4())})
    ).status_code == 409
    assert (
        await post(
            "conversation-draft",
            proposal | {"action": "lookup", "incoming_message_id": update["incoming_message_id"]},
        )
    ).status_code == 200
    assert (
        await post(
            "conversation-draft",
            proposal | {"action": "lookup", "incoming_message_id": str(uuid4())},
        )
    ).status_code == 404
    assert (
        await db.scalar(
            select(func.count())
            .select_from(MovimentacaoEstoque)
            .where(MovimentacaoEstoque.tenant_id == tenant.id)
        )
        == 0
    )


async def test_patch_rejects_foreign_scope_and_catalog(purchase):
    post, proposal, *_ = purchase
    source = (await post("conversation-draft", proposal | {"action": "read"})).json()
    ref = source["conversation_draft"]["itens"][0]["item_ref"]
    update = proposal | {
        "action": "patch",
        "expected_version": source["version"],
        "incoming_message_id": str(uuid4()),
        "edits": [
            {"op": "set_item", "item_ref": ref, "field": "ingrediente_id", "value": str(uuid4())}
        ],
    }
    assert (await post("conversation-draft", update)).status_code == 422
    assert (
        await post(
            "conversation-draft",
            update | {"scope": {"tenant_id": str(uuid4()), "company_id": None}},
        )
    ).status_code == 403
    assert (await post("draft", proposal)).json()["version"] == source["version"]


async def test_expired_draft_edit_requires_explicit_renewal_and_new_approval(purchase, db):
    from datetime import UTC, datetime, timedelta

    from infrastructure.database.central_models import CentralCompra

    post, proposal, decision, operation, *_ = purchase
    row = await db.get(CentralCompra, proposal["proposal_id"])
    old_expiry = datetime.now(UTC) - timedelta(hours=1)
    row.expira_em = old_expiry
    await db.commit()
    source = (await post("conversation-draft", proposal | {"action": "read"})).json()
    assert source["expired"]
    ref = source["conversation_draft"]["itens"][0]["item_ref"]
    changed = (
        await post(
            "conversation-draft",
            proposal
            | {
                "action": "patch",
                "expected_version": source["version"],
                "incoming_message_id": str(uuid4()),
                "edits": [
                    {
                        "op": "set_item",
                        "item_ref": ref,
                        "field": "descricao_original",
                        "value": "Farinha",
                    }
                ],
            },
        )
    ).json()
    assert changed["expired"] and changed["ready_for_review"]
    await db.refresh(row)
    assert row.expira_em == old_expiry
    assert (await post("decision", decision)).status_code == 409
    assert (await post("execute", operation)).status_code == 409
    review = proposal | {"expected_version": changed["version"], "reviewed": changed["reviewed"]}
    assert (await post("review", review)).status_code == 409
    renewed = await post("review", review | {"renew_expired": True})
    assert renewed.status_code == 200, renewed.text
    await db.refresh(row)
    assert timedelta(hours=23) < row.expira_em - datetime.now(UTC) <= timedelta(hours=24)
    assert row.estado == "awaiting_approval" and row.aprovacao_ref is None
    assert (await post("decision", decision)).status_code == 409


async def test_lookup_returns_current_snapshot_and_manual_review_keeps_dialogue_current(purchase):
    post, proposal, *_ = purchase
    source = (await post("conversation-draft", proposal | {"action": "read"})).json()
    ref = source["conversation_draft"]["itens"][0]["item_ref"]
    message = str(uuid4())
    changed = (
        await post(
            "conversation-draft",
            proposal
            | {
                "action": "patch",
                "expected_version": source["version"],
                "incoming_message_id": message,
                "edits": [
                    {
                        "op": "set_item",
                        "item_ref": ref,
                        "field": "descricao_original",
                        "value": "Farinha revisada",
                    }
                ],
            },
        )
    ).json()
    response = await post(
        "review",
        proposal | {"expected_version": changed["version"], "reviewed": changed["reviewed"]},
    )
    assert response.status_code == 200, response.text
    current = (
        await post(
            "conversation-draft", proposal | {"action": "lookup", "incoming_message_id": message}
        )
    ).json()
    assert current["version"] == response.json()["version"]
    assert current["conversation_draft"]["itens"][0]["item_ref"] == ref
    assert current["summary_hash"]


async def test_incomplete_draft_has_issues_and_no_approvable_hash(purchase):
    post, proposal, *_ = purchase
    source = (await post("conversation-draft", proposal | {"action": "read"})).json()
    ref = source["conversation_draft"]["itens"][0]["item_ref"]
    response = await post(
        "conversation-draft",
        proposal
        | {
            "action": "patch",
            "expected_version": source["version"],
            "incoming_message_id": str(uuid4()),
            "edits": [{"op": "set_item", "item_ref": ref, "field": "quantidade", "value": None}],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["issues"] and not response.json()["ready_for_review"]
    assert response.json()["summary_hash"] is None


async def test_confirmed_purchase_cannot_be_reopened_and_reconcile_still_works(purchase):
    post, proposal, decision, operation, *_ = purchase
    assert (await post("decision", decision)).status_code == 200
    executed = await post("execute", operation)
    assert executed.status_code == 200, executed.text
    terminal = await post("conversation-draft", proposal | {"action": "read"})
    assert terminal.status_code == 200
    assert not terminal.json()["ready_for_review"]
    assert (
        await post(
            "conversation-draft",
            proposal
            | {
                "action": "patch",
                "expected_version": terminal.json()["version"],
                "incoming_message_id": str(uuid4()),
                "edits": [
                    {
                        "op": "remove_item",
                        "item_ref": terminal.json()["conversation_draft"]["itens"][0]["item_ref"],
                    }
                ],
            },
        )
    ).status_code == 409
    reference = {
        k: operation[k]
        for k in (
            "operation_id",
            "business_id",
            "capability_code",
            "principal_ref",
            "scope",
            "idempotency_key",
        )
    }
    assert (await post("reconcile", reference)).json()["status"] == "confirmed"


async def test_litre_to_kg_requires_conversion_and_invalid_patch_is_atomic(purchase):
    post, proposal, *_ = purchase
    source = (await post("conversation-draft", proposal | {"action": "read"})).json()
    ref = source["conversation_draft"]["itens"][0]["item_ref"]
    base = proposal | {
        "action": "patch",
        "expected_version": source["version"],
        "incoming_message_id": str(uuid4()),
    }
    invalid = await post(
        "conversation-draft",
        base
        | {
            "edits": [
                {"op": "set_item", "item_ref": ref, "field": "quantidade", "value": "4"},
                {"op": "set_item", "item_ref": ref, "field": "produto_id", "value": str(uuid4())},
            ]
        },
    )
    assert invalid.status_code == 422
    assert (await post("draft", proposal)).json()["version"] == source["version"]
    changed = await post(
        "conversation-draft",
        base | {"edits": [{"op": "set_item", "item_ref": ref, "field": "unidade", "value": "l"}]},
    )
    assert changed.status_code == 200, changed.text
    assert not changed.json()["ready_for_review"]
    assert any(i["code"] == "fiscal_conversion_required" for i in changed.json()["issues"])


async def test_every_dialogue_action_revalidates_current_user(purchase, db):
    post, proposal, _, _, user, *_ = purchase
    source = (await post("conversation-draft", proposal | {"action": "read"})).json()
    user.ativo = False
    await db.commit()
    for action in [
        {"action": "read"},
        {"action": "lookup", "incoming_message_id": str(uuid4())},
        {
            "action": "patch",
            "expected_version": source["version"],
            "incoming_message_id": str(uuid4()),
            "edits": [
                {
                    "op": "remove_item",
                    "item_ref": source["conversation_draft"]["itens"][0]["item_ref"],
                }
            ],
        },
    ]:
        assert (await post("conversation-draft", proposal | action)).status_code == 403


async def test_started_operation_rejects_edits(purchase, db):
    from infrastructure.database.central_models import CentralCompra

    post, proposal, *_ = purchase
    source = (await post("conversation-draft", proposal | {"action": "read"})).json()
    row = await db.get(CentralCompra, proposal["proposal_id"])
    row.operation_id = uuid4()
    await db.commit()
    response = await post(
        "conversation-draft",
        proposal
        | {
            "action": "patch",
            "expected_version": source["version"],
            "incoming_message_id": str(uuid4()),
            "edits": [
                {
                    "op": "remove_item",
                    "item_ref": source["conversation_draft"]["itens"][0]["item_ref"],
                }
            ],
        },
    )
    assert response.status_code == 409
