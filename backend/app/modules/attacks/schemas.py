"""Pydantic schemas for the attack engine endpoints."""

import uuid
from pydantic import BaseModel


class AttackPreviewRequest(BaseModel):
    target_membership_id: uuid.UUID


class AttackExecuteRequest(BaseModel):
    target_membership_id: uuid.UUID
    guessed_account_id: uuid.UUID
